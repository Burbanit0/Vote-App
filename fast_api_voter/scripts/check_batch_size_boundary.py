"""
scripts/check_batch_size_boundary.py

Follow-up to the Lot 0 spike (check_ollama_structured_output.py /
ollama_structured_output_results.md), triggered by an open question left in
polity_v2_consolidation_handoff.md: a live consolidation run twice saw the
model corrupt the *same* citizens (index 0, 4, 8, 12, 16 of a 20-citizen
batch) with a self-contradictory blank=0/empty-ranking decision, exactly at
MIN_SAFE_BATCH_SIZE (llm_behavior_engine.py). That constant was chosen as "a
safety margin above 12-15" (the Lot 0 zero-output boundary) -- a different
failure mode, never itself swept.

This script sweeps citizen counts across and above that boundary using the
REAL production code path (build_system_prompt/build_user_prompt/
compute_max_tokens from llm_behavior_engine.py, OllamaJsonClient/
decode_vote_batch from llm_client.py) rather than the Lot 0 script's
standalone toy prompt builder, with multiple repeats per size to get a
failure rate (Finding D: identical calls are not guaranteed byte-identical,
so a single pass/fail per size is not conclusive).

2 candidates, not 5: the corruption was confirmed to happen with both 2 and
5 candidates (ruling out candidate count as *the* cause), and the live
consolidation notes 2 candidates measurably increased how often it
happened -- using 2 here maximizes signal per call given each call costs
~3.5-4 minutes on CPU.

Setup: same as check_ollama_structured_output.py (Ollama container running,
qwen3:8b pulled).

Usage:
    python fast_api_voter/scripts/check_batch_size_boundary.py \
        --sizes 20 21 22 23 24 25 --repeats 2 \
        --results scripts/batch_size_boundary_results.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import LlmResponseError, OllamaJsonClient, decode_vote_batch  # noqa: E402
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _citizen(cid: int, dims: int) -> Citizen:
    positions = tuple((cid * 0.037 + i * 0.017) % 1.0 for i in range(dims))
    priorities = tuple(1.0 / dims for _ in range(dims))
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=0.5,
                    ambition_score=0.5)


def _candidate(cid: int, dims: int) -> Citizen:
    c = _citizen(1000 + cid, dims)
    declare_candidacy(c)
    return c


def _diagnose_corruption(raw: str, expected_cids: list[int]) -> str:
    """On a decode failure, try to identify *which* cids look like the
    blank=0/empty-ranking self-contradiction the handoff doc describes,
    rather than just recording pass/fail -- reproduces the "index 0, 4, 8,
    12, 16" level of detail from the original observation, best-effort
    (falls back to a generic message if the payload doesn't even parse)."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return f"not valid JSON after stripping <think>: {exc}"
    decisions = parsed.get("decisions") if isinstance(parsed, dict) else None
    if not isinstance(decisions, list):
        return f"unexpected shape, no 'decisions' list: {str(parsed)[:300]!r}"
    bad: list[tuple[int, int]] = []  # (index, cid)
    for i, d in enumerate(decisions):
        if isinstance(d, dict) and d.get("blank") == 0 and not d.get("ranking"):
            bad.append((i, d.get("cid", -1)))
    got_cids = [d.get("cid") if isinstance(d, dict) else None for d in decisions]
    count_note = f"count={len(decisions)} (expected {len(expected_cids)})"
    order_note = "cids match expected order" if got_cids == expected_cids else f"cid mismatch: got {got_cids}"
    if bad:
        return f"blank=0/empty-ranking self-contradiction at {bad} ({count_note}, {order_note})"
    return f"{count_note}, {order_note}"


def run_one(client: OllamaJsonClient, dims: int, size: int) -> tuple[bool, str, float]:
    citizens = [_citizen(i, dims) for i in range(size)]
    candidates = [_candidate(i, dims) for i in range(2)]
    expected_cids = [c.citizen_id for c in citizens]
    start = time.monotonic()
    try:
        raw = client.complete_json(
            system_prompt=build_system_prompt(citizens, candidates),
            user_prompt=build_user_prompt(citizens, candidates),
            json_schema=VOTE_CAST_JSON_SCHEMA,
            max_tokens=compute_max_tokens(size),
        )
    except Exception as exc:  # noqa: BLE001 -- spike script: report any failure shape, transport included
        elapsed = time.monotonic() - start
        return False, f"transport/request error: {exc}", elapsed
    elapsed = time.monotonic() - start
    try:
        decode_vote_batch(raw, expected_cids)
        return True, "ok", elapsed
    except LlmResponseError as exc:
        detail = _diagnose_corruption(raw, expected_cids)
        return False, f"{exc} || diagnosis: {detail}", elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[20, 21, 22, 23, 24, 25])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    config = load_config()
    dims = config.citizens.issue_count
    log(f"# Batch-size boundary sweep -- model={config.llm.model}, dims={dims}, "
        f"candidates=2, sizes={args.sizes}, repeats={args.repeats}\n")

    summary: dict[int, list[bool]] = {size: [] for size in args.sizes}

    with OllamaJsonClient.from_config(config.llm, seed=42) as client:
        for size in args.sizes:
            for rep in range(args.repeats):
                ok, detail, elapsed = run_one(client, dims, size)
                summary[size].append(ok)
                status = "PASS" if ok else "FAIL"
                log(f"size={size} rep={rep + 1}/{args.repeats}: {status} elapsed={elapsed:.1f}s -- {detail}")

    log("\n## Summary\n")
    log("| size | passes | failures | failure rate |")
    log("|------|--------|----------|--------------|")
    for size in args.sizes:
        results = summary[size]
        fails = results.count(False)
        log(f"| {size} | {results.count(True)} | {fails} | {fails}/{len(results)} |")

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
