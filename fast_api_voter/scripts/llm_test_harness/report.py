"""
fast_api_voter/scripts/llm_test_harness/report.py

Renders a markdown report FROM the stored experiment+trials rows --
generated, never hand-written, so a report can never silently drift from
what was actually measured (the design brief's own stated goal). Mirrors
the pre-registration discipline: this module evaluates the pre-registered
criterion mechanically when threshold/comparison/metric were given at
registration time, and otherwise prints the free-text criterion next to
the raw numbers for a human to close the loop -- see registration.py's
own Experiment fields for why both paths exist.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import storage

_COMPARISON_LABELS: dict[str, str] = {"gt": ">", "lt": "<", "ge": ">=", "le": "<="}


def _compare(comparison: str, value: float, threshold: float) -> bool:
    if comparison == "gt":
        return value > threshold
    if comparison == "lt":
        return value < threshold
    if comparison == "ge":
        return value >= threshold
    if comparison == "le":
        return value <= threshold
    raise ValueError(f"unknown comparison {comparison!r}")


def _rate(trials: list[sqlite3.Row], *, ok_value: int) -> float | None:
    if not trials:
        return None
    matching = sum(1 for t in trials if t["ok"] == ok_value)
    return matching / len(trials)


def generate_report(experiment_id: str, *, db_path: Path | None = None) -> str:
    """Raises ValueError if experiment_id is unknown -- a report about a
    non-existent experiment is a caller error worth surfacing loudly, not
    an empty document."""
    conn = storage.connect(db_path)
    try:
        experiment = storage.get_experiment(conn, experiment_id)
        if experiment is None:
            raise ValueError(f"no experiment registered under id {experiment_id!r}")
        trials = storage.get_trials(conn, experiment_id)
    finally:
        conn.close()

    lines: list[str] = []
    lines.append(f"# Experiment `{experiment_id}`\n")
    lines.append(f"- **Hypothesis**: {experiment['hypothesis']}")
    lines.append(f"- **Decision criterion**: {experiment['decision_criterion']}")
    lines.append(f"- **Planned n**: {experiment['planned_n']} -- **actual n**: {len(trials)}")
    lines.append(f"- **Budget**: {experiment['budget_description']}")
    lines.append(
        f"- **Registered at**: {experiment['registered_at']} (git `{experiment['git_commit'][:12]}`)\n"
    )

    success_rate = _rate(trials, ok_value=1)
    failure_rate = _rate(trials, ok_value=0)
    lines.append("## Results\n")
    if not trials:
        lines.append("No trials recorded yet.\n")
    else:
        n_ok = sum(1 for t in trials if t["ok"])
        lines.append(f"- {len(trials)} trials -- {n_ok} ok, {len(trials) - n_ok} failed")
        assert success_rate is not None and failure_rate is not None
        lines.append(f"- success_rate = {success_rate:.3f}, failure_rate = {failure_rate:.3f}\n")
        lines.append("| # | ok | finish_reason | latency(s) | detail |")
        lines.append("|---|---|---|---|---|")
        for t in trials:
            lines.append(
                f"| {t['trial_number']} | {bool(t['ok'])} | {t['finish_reason'] or '-'} | "
                f"{t['latency_seconds']:.1f} | {t['detail'] or '-'} |"
            )
        lines.append("")

    lines.append("## Decision\n")
    metric = experiment["metric"]
    threshold = experiment["threshold"]
    comparison = experiment["comparison"]
    if trials and metric and threshold is not None and comparison:
        value = failure_rate if metric == "failure_rate" else success_rate
        assert value is not None
        verdict = _compare(comparison, value, threshold)
        symbol = _COMPARISON_LABELS[comparison]
        lines.append(
            f"**Mechanically evaluated**: {metric} = {value:.3f} {symbol} {threshold} "
            f"-> **{'PASS' if verdict else 'FAIL'}** against the pre-registered criterion."
        )
    else:
        lines.append(
            "No structured threshold/comparison/metric was registered -- evaluate the "
            f"criterion above ({experiment['decision_criterion']!r}) against the raw "
            "numbers by hand."
        )

    return "\n".join(lines) + "\n"
