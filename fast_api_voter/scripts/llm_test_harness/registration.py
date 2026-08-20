"""
fast_api_voter/scripts/llm_test_harness/registration.py

Pre-registration: writing the hypothesis, decision criterion, and planned
sample size down BEFORE any trial runs, and never touching that record
again regardless of what the results turn out to say -- the discipline
this project applied manually throughout its own GPU investigation
(committed corrections, never silent rewrites -- see
llm_batching_determinism_results_gpu.md's own "Correction" sections),
now enforced structurally: there is no function in this module or
storage.py that updates an experiment row after insert.
"""
from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from . import sample_size, storage


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    hypothesis: str
    decision_criterion: str
    planned_n: int
    budget_description: str
    registered_at: str
    git_commit: str
    threshold: float | None = None
    comparison: Literal["gt", "lt", "ge", "le"] | None = None
    metric: Literal["failure_rate", "success_rate"] | None = None


def _current_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5.0, check=False,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def register(
    hypothesis: str,
    decision_criterion: str,
    planned_n: int,
    budget_description: str,
    *,
    expected_effect_rate: float | None = None,
    confidence: float = 0.95,
    decision_threshold_for_sizing: float | None = None,
    threshold: float | None = None,
    comparison: Literal["gt", "lt", "ge", "le"] | None = None,
    metric: Literal["failure_rate", "success_rate"] | None = None,
    db_path: Path | None = None,
    warn: bool = True,
) -> Experiment:
    """Writes an immutable experiment record. If both expected_effect_rate
    and decision_threshold_for_sizing are given, computes the sample size
    the stated decision criterion would actually need
    (sample_size.required_sample_size) and PRINTS a warning -- never a
    hard block, per the design brief -- if planned_n falls short.

    `threshold`/`comparison`/`metric` are the OPTIONAL structured form of
    the decision criterion: when all three are given, report.py evaluates
    PASS/FAIL mechanically from the stored trials; `decision_criterion`
    itself always stays free text (for human readability) regardless.

    Returns the stored Experiment either way -- a sizing warning is never
    a rejection."""
    if planned_n < 1:
        raise ValueError(f"planned_n must be at least 1, got {planned_n!r}")

    if expected_effect_rate is not None and decision_threshold_for_sizing is not None:
        required = sample_size.required_sample_size(
            expected_effect_rate, confidence=confidence, decision_threshold=decision_threshold_for_sizing,
        )
        if planned_n < required and warn:
            print(
                f"WARNING: planned_n={planned_n} is below the {required} trials this "
                f"decision criterion would need at {confidence:.0%} confidence "
                f"(expected_effect_rate={expected_effect_rate}, "
                f"decision_threshold={decision_threshold_for_sizing}). Proceeding anyway -- "
                "this is a warning, not a block."
            )

    experiment = Experiment(
        experiment_id=f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}",
        hypothesis=hypothesis,
        decision_criterion=decision_criterion,
        planned_n=planned_n,
        budget_description=budget_description,
        registered_at=datetime.now(timezone.utc).isoformat(),
        git_commit=_current_git_commit(),
        threshold=threshold,
        comparison=comparison,
        metric=metric,
    )

    conn = storage.connect(db_path)
    try:
        storage.insert_experiment(
            conn,
            {
                "experiment_id": experiment.experiment_id,
                "hypothesis": experiment.hypothesis,
                "decision_criterion": experiment.decision_criterion,
                "threshold": experiment.threshold,
                "comparison": experiment.comparison,
                "metric": experiment.metric,
                "planned_n": experiment.planned_n,
                "budget_description": experiment.budget_description,
                "registered_at": experiment.registered_at,
                "git_commit": experiment.git_commit,
            },
        )
    finally:
        conn.close()

    return experiment
