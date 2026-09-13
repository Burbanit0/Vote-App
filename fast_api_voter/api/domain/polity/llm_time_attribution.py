"""Where a run's LLM time went (S0.5), from its llm_calls.jsonl.

Every call is put in exactly one category:

- `warm_up`, `budget_probe`: infrastructure calls, not decisions.
- `truncation`: generation stopped at the token budget (finish_reason "length").
- `failed`: the client raised without a model answer (transport).
- `rejected`: answered, then replaced by the next attempt of the same batch --
  the engine could not decode or validate it.
- `retry`: an accepted answer from a replay (attempt >= 1).
- `first_attempt`: an accepted answer on the first try.

"Accepted" is inferred from the log alone: a batch's last attempt counts as
accepted even when the engine then fell back to its deterministic baseline, so
read `rejected` together with progress.json's fallback counts.

Coverage is the union of call intervals over the run's wall-clock, not the sum of
latencies: with intra-run workers, calls overlap and the sum can exceed it.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

CATEGORIES = ("first_attempt", "retry", "rejected", "truncation", "failed", "budget_probe", "warm_up")
TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "reasoning_tokens", "cached_tokens")


def read_calls(path: Path) -> list[dict[str, Any]]:
    calls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            calls.append(json.loads(line))
    return calls


def _batch_key(call: dict[str, Any]) -> tuple[Any, ...]:
    return (call.get("tick"), call.get("decision_type"), tuple(call.get("unit_ids") or ()))


def superseded_call_indexes(calls: Sequence[dict[str, Any]]) -> set[int]:
    """Indexes of decision calls followed, within the same batch (tick, decision
    type, units), by that batch's next attempt. Two separate batches over the same
    units in one tick (a reaction to two events) both start at attempt 0, so
    neither supersedes the other."""
    by_batch: dict[tuple[Any, ...], list[int]] = {}
    for index, call in enumerate(calls):
        if call.get("kind") == "decision":
            by_batch.setdefault(_batch_key(call), []).append(index)
    superseded: set[int] = set()
    for indexes in by_batch.values():
        ordered = sorted(indexes, key=lambda i: calls[i].get("started_at") or 0.0)
        for current, following in zip(ordered, ordered[1:]):
            if (calls[following].get("attempt") or 0) == (calls[current].get("attempt") or 0) + 1:
                superseded.add(current)
    return superseded


def call_category(call: dict[str, Any], superseded: bool) -> str:
    kind = call.get("kind")
    if kind in ("warm_up", "budget_probe"):
        return str(kind)
    if call.get("finish_reason") == "length":
        return "truncation"
    if call.get("error") and call.get("content") is None:
        return "failed"
    if superseded:
        return "rejected"
    return "retry" if (call.get("attempt") or 0) > 0 else "first_attempt"


def covered_seconds(calls: Iterable[dict[str, Any]]) -> float:
    intervals = sorted(
        (float(c["started_at"]), float(c["started_at"]) + float(c.get("latency_ms") or 0.0) / 1000)
        for c in calls
        if c.get("started_at") is not None
    )
    total, reach = 0.0, float("-inf")
    for start, end in intervals:  # sorted by start: count only what extends past the reach so far
        if end > reach:
            total += end - max(start, reach)
            reach = end
    return total


def _empty_bucket() -> dict[str, float]:
    return {"calls": 0, "seconds": 0.0, **dict.fromkeys(TOKEN_FIELDS, 0)}


def _add(bucket: dict[str, float], call: dict[str, Any]) -> None:
    bucket["calls"] += 1
    bucket["seconds"] += float(call.get("latency_ms") or 0.0) / 1000
    for token_field in TOKEN_FIELDS:
        bucket[token_field] += int(call.get(token_field) or 0)


def attribute(calls: Sequence[dict[str, Any]], wall_clock_seconds: float | None) -> dict[str, Any]:
    superseded = superseded_call_indexes(calls)
    by_type: dict[str, dict[str, dict[str, float]]] = {}
    by_category = {category: _empty_bucket() for category in CATEGORIES}
    for index, call in enumerate(calls):
        category = call_category(call, index in superseded)
        decision_type = call.get("decision_type") or call.get("kind") or "unknown"
        _add(by_type.setdefault(str(decision_type), {}).setdefault(category, _empty_bucket()), call)
        _add(by_category[category], call)
    covered = covered_seconds(calls)
    return {
        "calls": len(calls),
        "latency_seconds_sum": sum(bucket["seconds"] for bucket in by_category.values()),
        "covered_seconds": covered,
        "wall_clock_seconds": wall_clock_seconds,
        "coverage": covered / wall_clock_seconds if wall_clock_seconds else None,
        "by_category": by_category,
        "by_decision_type": dict(sorted(by_type.items())),
    }


def attribute_run(run_dir: Path) -> dict[str, Any]:
    """Attribution for a run directory: its llm_calls.jsonl over progress.json's
    wall-clock (null when the run never wrote progress)."""
    progress_path = run_dir / "progress.json"
    wall_clock = None
    if progress_path.exists():
        wall_clock = json.loads(progress_path.read_text(encoding="utf-8")).get("wall_clock_elapsed_seconds")
    return attribute(read_calls(run_dir / "llm_calls.jsonl"), wall_clock)
