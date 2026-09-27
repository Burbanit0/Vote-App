"""Statistics for multi-seed sweeps (S0.7): intervals instead of bare means, and
the pre-registered red flags evaluated mechanically, so a sweep's results doc is
generated rather than argued.

The p100 sweep reported mean and stdev only, and its first write-up read 10 seeds
as settling representativeness; intervals were then computed by hand to correct
it (S0.1). These functions make them the default output. They reproduce that
correction's prediction and Clopper-Pearson figures exactly; its BCa lower bound
(0.894) was Monte Carlo noise from 10,000 resamples on rounded values, hence the
100,000 default here (0.888 on the exact values).

Repeated runs of one seed measure inference noise at a fixed seed, not
seed-to-seed variation, so every across-seed statistic uses each seed's first
completed run only.
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

OCCUPANCY_BAR = 0.70
FALLBACK_ALERT_RATE = 0.10

# run_metadata.json fields (S0.4) that must agree across a batch for its runs to
# be one experiment: same code, same prompts, same server and weights.
PROVENANCE_FIELDS = (
    "git_sha", "git_dirty_paths", "prompt_source_sha256",
    "vllm_version", "vllm_image_id", "served_model_repo", "served_model_revision",
)


def sweep_run_plan(seeds: Sequence[int]) -> list[tuple[int, int]]:
    """(seed, repeat) per requested run, repeat counting from 1 in order of
    appearance -- `1,2,42,1` runs seed 1 twice, the second as repeat 2."""
    seen: Counter[int] = Counter()
    plan = []
    for seed in seeds:
        seen[seed] += 1
        plan.append((seed, seen[seed]))
    return plan


def mean_bca_interval(
    values: Sequence[float], *, confidence: float = 0.95, n_resamples: int = 100_000, random_seed: int = 0,
) -> tuple[float, float] | None:
    """Bias-corrected and accelerated bootstrap interval for the mean. None below
    three values or when every value is equal (the bootstrap distribution is a
    point). With few values it is wide and unstable; it is reported, not trusted."""
    if len(values) < 3 or len(set(values)) == 1:
        return None
    result = stats.bootstrap(
        (np.asarray(values, dtype=float),), np.mean, confidence_level=confidence,
        n_resamples=n_resamples, method="BCa", random_state=random_seed,
    )
    low, high = float(result.confidence_interval.low), float(result.confidence_interval.high)
    return None if math.isnan(low) or math.isnan(high) else (low, high)


def prediction_interval(values: Sequence[float], *, confidence: float = 0.95) -> tuple[float, float] | None:
    """Where one new seed's value is expected to fall: mean ± t · s · √(1 + 1/n).
    It can extend past a metric's natural bounds, and that is information."""
    n = len(values)
    if n < 2:
        return None
    mean = float(np.mean(values))
    half_width = float(stats.t.ppf((1 + confidence) / 2, n - 1)) * float(np.std(values, ddof=1)) * math.sqrt(1 + 1 / n)
    return (mean - half_width, mean + half_width)


def clopper_pearson(successes: int, trials: int, *, confidence: float = 0.95) -> tuple[float, float] | None:
    """Exact binomial interval for a rate; None for zero trials."""
    if trials == 0:
        return None
    interval = stats.binomtest(successes, trials).proportion_ci(confidence_level=confidence, method="exact")
    return (float(interval.low), float(interval.high))


@dataclass(frozen=True)
class SweepRun:
    seed: int
    repeat: int
    run_id: str
    outcome: str
    office_occupancy: float | None = None
    decisions_by_type: dict[str, int] = field(default_factory=dict)
    fallback_by_type: dict[str, int] = field(default_factory=dict)
    run_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def completed(self) -> bool:
        return self.outcome == "completed"

    def fallback_rates(self) -> dict[str, float]:
        return {t: self.fallback_by_type.get(t, 0) / n for t, n in sorted(self.decisions_by_type.items()) if n}


def first_completed_runs(runs: Sequence[SweepRun]) -> list[SweepRun]:
    """Each seed's first completed run: the independent sample across seeds."""
    chosen: dict[int, SweepRun] = {}
    for run in sorted(runs, key=lambda r: (r.seed, r.repeat)):
        if run.completed and run.seed not in chosen:
            chosen[run.seed] = run
    return list(chosen.values())


def provenance_differences(runs: Sequence[SweepRun]) -> dict[str, dict[str, str]]:
    """PROVENANCE_FIELDS whose values differ among completed runs, as field ->
    {run (or run@resume n): value}. A resume records its own provenance, so a run
    resumed under other code counts as differing from itself. Empty when the batch
    is one experiment -- or when no run recorded provenance (all values null)."""
    differences: dict[str, dict[str, str]] = {}
    for provenance_field in PROVENANCE_FIELDS:
        values: dict[str, str] = {}
        for run in (r for r in runs if r.completed):
            records = [run.run_metadata, *run.run_metadata.get("resumes", [])]
            for index, record in enumerate(records):
                label = run.run_id if index == 0 else f"{run.run_id}@resume{index}"
                values[label] = str(record.get(provenance_field))
        if len(set(values.values())) > 1:
            differences[provenance_field] = values
    return differences


@dataclass(frozen=True)
class RedFlag:
    name: str
    status: str  # "raised", "clear" or "not evaluable"
    detail: str


_OCCUPANCY_FLAG = "office_occupancy below the bar"
_FALLBACK_FLAG = "decision type above the fallback alert"
_DIVERGENCE_FLAG = "same-seed divergence beyond the across-seed spread"


def _occupancy_by_run(runs: Sequence[SweepRun]) -> dict[str, float]:
    return {r.run_id: r.office_occupancy for r in runs if r.completed and r.office_occupancy is not None}


def _occupancy_flag(runs: Sequence[SweepRun]) -> RedFlag:
    measured = _occupancy_by_run(runs)
    if not measured:
        return RedFlag(_OCCUPANCY_FLAG, "not evaluable", "no completed run reports office_occupancy")
    low = [f"{run_id} {value:.4f}" for run_id, value in measured.items() if value < OCCUPANCY_BAR]
    if low:
        return RedFlag(_OCCUPANCY_FLAG, "raised", f"bar {OCCUPANCY_BAR}; below it: {', '.join(low)}")
    return RedFlag(_OCCUPANCY_FLAG, "clear", f"all {len(measured)} completed runs at or above {OCCUPANCY_BAR}")


def _fallback_flag(runs: Sequence[SweepRun]) -> RedFlag:
    completed = [r for r in runs if r.completed]
    if not completed:
        return RedFlag(_FALLBACK_FLAG, "not evaluable", "no completed run")
    over = [
        f"{r.run_id} {decision_type} {rate:.1%}"
        for r in completed for decision_type, rate in r.fallback_rates().items() if rate > FALLBACK_ALERT_RATE
    ]
    if over:
        return RedFlag(_FALLBACK_FLAG, "raised", f"alert {FALLBACK_ALERT_RATE:.0%}: {'; '.join(over)}")
    return RedFlag(_FALLBACK_FLAG, "clear", f"no type above {FALLBACK_ALERT_RATE:.0%} in {len(completed)} completed runs")


def _repeat_divergences(runs: Sequence[SweepRun], first_by_seed: dict[int, float]) -> dict[str, float]:
    repeats = [r for r in runs if r.repeat > 1 and r.seed in first_by_seed]
    return {
        f"seed {r.seed} repeat {r.repeat}": abs(occupancy - first_by_seed[r.seed])
        for r in repeats
        if (occupancy := _occupancy_by_run([r]).get(r.run_id)) is not None
    }


def _repeat_divergence_flag(runs: Sequence[SweepRun]) -> RedFlag:
    """|office_occupancy of a repeat - its seed's first run| against the range of
    first-run office_occupancy across distinct seeds."""
    first_by_seed = {r.seed: r.office_occupancy for r in first_completed_runs(runs) if r.office_occupancy is not None}
    divergences = _repeat_divergences(runs, first_by_seed)
    if len(first_by_seed) < 2 or not divergences:
        return RedFlag(
            _DIVERGENCE_FLAG, "not evaluable",
            f"needs two completed seeds and a completed repeat of one (have {len(first_by_seed)} seeds, "
            f"{len(divergences)} comparable repeats)",
        )
    spread = max(first_by_seed.values()) - min(first_by_seed.values())
    listed = "; ".join(f"{label}: |Δ| {value:.4f}" for label, value in divergences.items())
    status = "raised" if any(value > spread for value in divergences.values()) else "clear"
    return RedFlag(_DIVERGENCE_FLAG, status, f"office_occupancy spread across seeds {spread:.4f}; {listed}")


def red_flags(runs: Sequence[SweepRun]) -> list[RedFlag]:
    """The three red flags S0.7 pre-registered for the p500 batch, in its order."""
    return [_occupancy_flag(runs), _fallback_flag(runs), _repeat_divergence_flag(runs)]
