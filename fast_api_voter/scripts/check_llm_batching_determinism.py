"""
scripts/check_llm_batching_determinism.py

DEMARRAGE-polity-v0.md §5 / polity-simulation-design-v2.md §15bis.5
verification protocol: does temperature=0 + a pinned model actually
guarantee byte-identical output regardless of concurrent batch size, and
across a container restart? The whole v2+ reproducibility strategy (§4)
assumes yes; this has never been checked empirically.

Setup:
    docker run -d -p 11434:11434 --name ollama -e OLLAMA_NUM_PARALLEL=8 ollama/ollama
    docker exec ollama ollama pull qwen2.5:0.5b

Usage:
    python fast_api_voter/scripts/check_llm_batching_determinism.py --save before.json
    docker restart ollama   # wait for it to come back up
    python fast_api_voter/scripts/check_llm_batching_determinism.py --compare before.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:0.5b"
PROMPT = (
    "A citizen must decide whether to vote for candidate A or candidate B "
    "in a local election. List three factors that would influence this "
    "decision, one sentence each."
)
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 64}
BATCH_SIZES = (1, 5, 25, 50)
SEQUENTIAL_RUNS = 10


async def _generate(client: httpx.AsyncClient) -> str:
    response = await client.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": PROMPT, "options": OPTIONS, "stream": False},
        timeout=120.0,
    )
    response.raise_for_status()
    return str(response.json()["response"])


async def _run_batch(size: int) -> list[str]:
    async with httpx.AsyncClient() as client:
        return list(await asyncio.gather(*(_generate(client) for _ in range(size))))


async def _run_sequential(count: int) -> list[str]:
    results = []
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            results.append(await _generate(client))
    return results


def _all_identical(outputs: list[str]) -> bool:
    return len(set(outputs)) <= 1


async def collect() -> dict[str, Any]:
    batches = {str(size): await _run_batch(size) for size in BATCH_SIZES}
    sequential = await _run_sequential(SEQUENTIAL_RUNS)
    return {"batches": batches, "sequential": sequential}


def analyse(data: dict[str, Any], log: Any) -> bool:
    ok = True
    reference = data["batches"][str(BATCH_SIZES[0])][0]
    for size in BATCH_SIZES:
        outputs = data["batches"][str(size)]
        within = _all_identical(outputs)
        matches_reference = outputs[0] == reference
        ok = ok and within and matches_reference
        log(
            f"- batch_size={size}: identical within batch = {within}, "
            f"first response matches batch_size={BATCH_SIZES[0]} reference = {matches_reference}"
        )

    sequential_ok = _all_identical(data["sequential"])
    ok = ok and sequential_ok
    log(f"- {SEQUENTIAL_RUNS} consecutive runs (batch_size=1) identical = {sequential_ok}")
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", type=Path, help="write raw results to this JSON file")
    parser.add_argument(
        "--compare", type=Path, help="compare fresh results against a previously --save'd JSON file"
    )
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    log(f"# LLM batching determinism protocol -- model={MODEL}, options={OPTIONS}\n")
    log("## Within this run\n")
    data = await collect()
    within_run_ok = analyse(data, log)

    across_restart_ok: bool | None = None
    if args.compare:
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        log("\n## Against the pre-restart baseline\n")
        baseline_ref = baseline["batches"][str(BATCH_SIZES[0])][0]
        fresh_ref = data["batches"][str(BATCH_SIZES[0])][0]
        across_restart_ok = baseline_ref == fresh_ref
        log(f"- batch_size={BATCH_SIZES[0]} output identical to pre-restart baseline = {across_restart_ok}")

    overall = within_run_ok and (across_restart_ok is not False)
    log(f"\n## Summary\n\n- Within-run (batching + sequential): {'PASS' if within_run_ok else 'FAIL'}")
    if across_restart_ok is not None:
        log(f"- Across restart: {'PASS' if across_restart_ok else 'FAIL'}")
    log(f"\n**Overall: {'PASS' if overall else 'FAIL'}**")

    if args.save:
        args.save.write_text(json.dumps(data), encoding="utf-8")
        log(f"\n(raw results saved to {args.save})")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
