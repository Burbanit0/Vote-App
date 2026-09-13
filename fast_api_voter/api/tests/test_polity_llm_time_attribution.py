"""LLM time attribution (S0.5). See api/domain/polity/llm_time_attribution.py."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.llm_time_attribution import attribute, attribute_run, call_category, covered_seconds


def _call(kind: str = "decision", *, tick: int = 4, decision_type: str | None = "vote_cast", units: tuple[int, ...] = (1, 2, 3),
          attempt: int | None = 0, start: float = 0.0, ms: float = 1000.0, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "tick": tick, "decision_type": decision_type, "unit_ids": list(units), "attempt": attempt,
            "started_at": start, "latency_ms": ms, **extra}


def test_every_call_lands_in_exactly_one_category() -> None:
    calls = [
        _call("warm_up", decision_type=None, units=(), attempt=None, start=0, ms=500),
        _call("budget_probe", attempt=None, start=1, ms=10),
        _call(start=2, content="bad", completion_tokens=40),             # rejected: attempt 1 follows
        _call(attempt=1, start=4, content="ok", temperature=0.7),        # the recovering retry
        _call(units=(4, 5, 6), start=6, finish_reason="length"),         # truncated
        _call(units=(4, 5, 6), attempt=1, start=9, content="ok"),        # retry after the truncation
        _call(units=(7,), start=11, content="ok", prompt_tokens=900),    # clean first attempt
        _call(units=(8,), start=13, error="LlmTransportError: refused"),  # no answer at all
    ]
    report = attribute(calls, wall_clock_seconds=20.0)
    counts = {category: int(bucket["calls"]) for category, bucket in report["by_category"].items()}
    assert counts == {
        "first_attempt": 1, "retry": 2, "rejected": 1, "truncation": 1, "failed": 1, "budget_probe": 1, "warm_up": 1,
    }
    assert report["by_category"]["rejected"]["completion_tokens"] == 40
    assert report["by_decision_type"]["vote_cast"]["first_attempt"]["prompt_tokens"] == 900
    assert report["by_decision_type"]["warm_up"]["warm_up"]["calls"] == 1
    assert report["latency_seconds_sum"] == pytest.approx(0.5 + 0.01 + 6 * 1.0)
    assert report["coverage"] == pytest.approx(report["covered_seconds"] / 20.0)


def test_two_batches_over_the_same_units_in_one_tick_do_not_supersede_each_other() -> None:
    # A reaction to a scandal and to a shock in the same tick: both batches start at attempt 0.
    first, second, second_retry = _call(start=0), _call(start=2), _call(attempt=1, start=4)
    assert call_category(first, superseded=False) == "first_attempt"
    categories = attribute([first, second, second_retry], None)["by_category"]
    assert (categories["first_attempt"]["calls"], categories["rejected"]["calls"], categories["retry"]["calls"]) == (1, 1, 1)


def test_covered_seconds_merges_overlapping_calls() -> None:
    calls = [_call(start=0, ms=4000), _call(start=1, ms=1000), _call(start=3, ms=3000), _call(start=10, ms=1000),
             {"kind": "decision", "started_at": None}]
    assert covered_seconds(calls) == pytest.approx(6.0 + 1.0)
    assert attribute([], None)["coverage"] is None


def test_attribute_run_reads_the_run_directory(tmp_path: Path) -> None:
    (tmp_path / "llm_calls.jsonl").write_text(json.dumps(_call(ms=2000)) + "\n\n", encoding="utf-8")
    assert attribute_run(tmp_path)["wall_clock_seconds"] is None
    (tmp_path / "progress.json").write_text(json.dumps({"wall_clock_elapsed_seconds": 4.0}), encoding="utf-8")
    assert attribute_run(tmp_path)["coverage"] == pytest.approx(0.5)
