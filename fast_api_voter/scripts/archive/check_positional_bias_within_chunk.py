"""
scripts/check_positional_bias_within_chunk.py

§5.D of `plan-llm-protocol-and-theory-program.md`: "lost in the middle" (Liu et
al., 2023) says models attend unevenly across a context. This project batches
several citizens into one call (`_VOTE_CAST_MAX_CHUNK_SIZE_VLLM=3`,
`_CHAMBER_MAX_CHUNK_SIZE_VLLM=5`), so if that effect is real here, a citizen's
decision would depend partly on WHERE they sat in the chunk -- a confound that
sits underneath every batched decision the project has ever journaled.

**Why this is worth running before anything else in that plan**: it needs no
GPU, no server, no code change, and no new run. It reads journals that already
exist. `chunk_voters` is a pure, deterministic function of (ordered citizen
list, max_batch_size), so the exact chunk composition of every historical call
is reconstructable after the fact -- position within chunk was never journaled,
but it never needed to be.

**What this does and does not test.** The project already tested chunk
REORDERING against the `pressure_action` collapse and found the collapse
reproduced (`check_pressure_action_chunk_reorder.py`) -- that answered "is the
collapse an artifact of position", and the answer was no. This asks a different,
finer question that reordering could not: across a whole real run, does the
DISTRIBUTION of decisions differ by position within the chunk? A collapse is not
required for a positional gradient to exist, and a positional gradient is a
confound even when every individual decision is defensible.

Decisions marked `llm_fallback=1` are excluded from the behavioural tallies:
they are `_deterministic_*_fallback` output, not model decisions, and counting
them would dilute exactly the signal being looked for. They are reported
separately, since a positional gradient in FAILURE rate would itself be a
finding.

Usage:
    python fast_api_voter/scripts/check_positional_bias_within_chunk.py \\
        --run-dir fast_api_voter/scripts/flagship_runs/parity-8y-p100-chunked-v1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.llm_behavior_engine import MIN_SAFE_BATCH_SIZE  # noqa: E402,F401

# Mirrors llm_behavior_engine.chunk_voters exactly (near-equal chunks, the first
# `remainder` chunks taking one extra). Re-implemented rather than imported
# because the real one takes Citizen objects and this only needs the shape --
# any drift between the two would be caught by the assertion in _positions().
def _chunk_sizes(n: int, max_batch_size: int) -> list[int]:
    if n == 0:
        return []
    num_chunks = -(-n // max_batch_size)
    base_size, remainder = divmod(n, num_chunks)
    return [base_size + (1 if i < remainder else 0) for i in range(num_chunks)]


def _positions(ordered_ids: list[int], max_batch_size: int) -> dict[int, tuple[int, int]]:
    """cid -> (position_within_chunk, chunk_size)."""
    sizes = _chunk_sizes(len(ordered_ids), max_batch_size)
    assert sum(sizes) == len(ordered_ids), "chunk reconstruction lost citizens"
    out: dict[int, tuple[int, int]] = {}
    start = 0
    for size in sizes:
        for offset, cid in enumerate(ordered_ids[start:start + size]):
            out[cid] = (offset, size)
        start += size
    return out


def _load(run_dir: Path) -> list[dict]:
    candidates = list(run_dir.glob("**/events.jsonl"))
    if not candidates:
        raise SystemExit(f"no events.jsonl under {run_dir}")
    with candidates[0].open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _analyse(events: list[dict], event_type: str, chunk_size: int, sort_by_cid: bool) -> None:
    by_tick: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("event_type") == event_type:
            by_tick[event["tick"]].append(event)
    if not by_tick:
        print(f"\n== {event_type}: no events ==")
        return

    stats: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for tick, tick_events in by_tick.items():
        # chamber sorts by citizen_id before chunking; cast_votes preserves the
        # caller's population order, which is citizen_id order at construction.
        ordered = sorted(tick_events, key=lambda e: e["citizen_id"]) if sort_by_cid else tick_events
        ordered_ids = [e["citizen_id"] for e in ordered]
        pos_map = _positions(ordered_ids, chunk_size)
        for event in ordered:
            offset, size = pos_map[event["citizen_id"]]
            payload = event.get("payload", {})
            bucket = stats[offset]
            bucket["n"] += 1
            if payload.get("llm_fallback"):
                bucket["fallback"] += 1
                continue
            bucket["n_model"] += 1
            if payload.get("retry_sampling_varied"):
                bucket["retried"] += 1
            if event_type == "chamber_deliberation":
                if str(event.get("motif")) == "702":
                    bucket["shifted"] += 1
                bucket["n_shifts"] += len(payload.get("shifts") or [])
            elif event_type == "vote_cast":
                if payload.get("blank"):
                    bucket["blank"] += 1
                bucket["ranking_len"] += len(payload.get("ranking") or [])

    print(f"\n== {event_type} (chunk_size={chunk_size}) ==")
    if event_type == "chamber_deliberation":
        print("| pos | n | fallback% | retried% | motif702% (of model) | mean shifts |")
        print("|---|---|---|---|---|---|")
    else:
        print("| pos | n | fallback% | retried% | blank% (of model) | mean ranking len |")
        print("|---|---|---|---|---|---|")
    for offset in sorted(stats):
        b = stats[offset]
        n, nm = b["n"], b["n_model"]
        if event_type == "chamber_deliberation":
            print(f"| {offset} | {int(n)} | {100 * b['fallback'] / n:.1f} | "
                  f"{100 * b['retried'] / n:.1f} | "
                  f"{(100 * b['shifted'] / nm) if nm else float('nan'):.1f} | "
                  f"{(b['n_shifts'] / nm) if nm else float('nan'):.2f} |")
        else:
            print(f"| {offset} | {int(n)} | {100 * b['fallback'] / n:.1f} | "
                  f"{100 * b['retried'] / n:.1f} | "
                  f"{(100 * b['blank'] / nm) if nm else float('nan'):.1f} | "
                  f"{(b['ranking_len'] / nm) if nm else float('nan'):.2f} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--vote-chunk", type=int, default=3, help="_VOTE_CAST_MAX_CHUNK_SIZE_VLLM at run time")
    parser.add_argument("--chamber-chunk", type=int, default=5, help="_CHAMBER_MAX_CHUNK_SIZE_VLLM at run time")
    args = parser.parse_args(argv)

    events = _load(args.run_dir)
    print(f"loaded {len(events)} events from {args.run_dir}")
    _analyse(events, "chamber_deliberation", args.chamber_chunk, sort_by_cid=True)
    _analyse(events, "vote_cast", args.vote_chunk, sort_by_cid=False)
    print("\nNOTE: a flat column here is evidence AGAINST a positional effect at these "
          "chunk sizes; a monotone or U-shaped gradient is evidence FOR one and would "
          "make position a confound in every batched decision journaled so far.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
