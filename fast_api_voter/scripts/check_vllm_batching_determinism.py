"""
scripts/check_vllm_batching_determinism.py

polity-simulation-design-v2.md §15bis.5 verification protocol, run against
vLLM instead of Ollama (v4 vLLM switch, §15bis.6). NEVER RUN in this
project: no vLLM server/GPU has been available in this environment. Written
so the question is ready to answer the moment one exists.

§15bis.4c's own threat model for vLLM is NOT the same failure mode
check_llm_batching_determinism.py already confirmed for Ollama
(non-deterministic floating-point reduction order in multi-threaded CPU
inference, llama.cpp) -- it is specifically about vLLM's continuous-batching
SCHEDULER causing a different kernel reduction path depending on what else
is in-flight in the same server-side batch. That risk only exists on the
REAL structured-output code path (response_format + guided decoding), so
unlike the Ollama script -- which used a standalone free-text /api/generate
probe -- this one sends the actual production request shape: real
VOTE_CAST_JSON_SCHEMA (dereferenced via _inline_refs, exactly as
VllmJsonClient does), real prompt builders, real system/user prompts.

QUARANTINE WARNING (repeated from llm_client.py's own module docstring,
verbatim in spirit): this script is deliberately async and deliberately
concurrent -- that is the whole point, a server-side continuous batch
cannot form otherwise. This pattern exists ONLY to prove or disprove
divergence under concurrency. It must never leak into production code,
which keeps exactly one request in flight at a time (llm_client.py).

Setup (once a GPU host exists):
    docker compose -f docker-compose.llm.yml up -d

Usage:
    python fast_api_voter/scripts/check_vllm_batching_determinism.py \
        --save before.json
    docker compose -f docker-compose.llm.yml restart vllm   # wait for it to come back up
    python fast_api_voter/scripts/check_vllm_batching_determinism.py \
        --compare before.json

No results doc is committed alongside this script -- per this project's
convention (llm_batching_determinism_results.md,
ollama_structured_output_results.md, lot6_batch_reliability_results.md), a
results doc ships with real measured numbers, never as an empty stub. See
scripts/vllm_determinism_results.md once this has actually been run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import _inline_refs  # noqa: E402
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

DEFAULT_BASE_URL = "http://localhost:8000/v1"
MODEL = "qwen3:8b"  # must match --served-model-name at server launch (docker-compose.llm.yml)
BATCH_SIZES = (1, 5, 25, 50)
SEQUENTIAL_RUNS = 10
_DIMS = 20  # matches the shipped citizens.issue_count


def _citizen(cid: int) -> Citizen:
    positions = tuple((cid * 0.037 + i * 0.017) % 1.0 for i in range(_DIMS))
    priorities = tuple(1.0 / _DIMS for _ in range(_DIMS))
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=0.5,
                    ambition_score=0.5)


def _candidate(cid: int) -> Citizen:
    c = _citizen(1000 + cid)
    declare_candidacy(c)
    return c


def _request_body(max_tokens: int) -> dict[str, Any]:
    """The exact request VllmJsonClient.complete_json(think=False) would
    send for a real 20-citizen vote_cast batch -- same schema, same
    prompts, same options. Built once (the prompts are a pure function of
    the fixed citizen/candidate lists below); every concurrent/sequential
    call in this script sends this SAME body, per §15bis.5's own protocol
    ("même prompt exact")."""
    citizens = [_citizen(i) for i in range(20)]
    candidates = [_candidate(i) for i in range(5)]
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": build_system_prompt(citizens, candidates)},
            {"role": "user", "content": build_user_prompt(citizens, candidates)},
        ],
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polity_decision_batch", "strict": True, "schema": _inline_refs(VOTE_CAST_JSON_SCHEMA),
            },
        },
    }


async def _generate(client: httpx.AsyncClient, base_url: str, body: dict[str, Any]) -> str:
    response = await client.post(f"{base_url}/chat/completions", json=body, timeout=180.0)
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"])


async def _run_batch(base_url: str, body: dict[str, Any], size: int) -> list[str]:
    """Deliberately concurrent (asyncio.gather) -- see module docstring's
    quarantine warning. This is what forces vLLM's server-side continuous
    batching to actually engage with `size` in-flight requests at once."""
    async with httpx.AsyncClient() as client:
        return list(await asyncio.gather(*(_generate(client, base_url, body) for _ in range(size))))


async def _run_sequential(base_url: str, body: dict[str, Any], count: int) -> list[str]:
    results = []
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            results.append(await _generate(client, base_url, body))
    return results


def _all_identical(outputs: list[str]) -> bool:
    return len(set(outputs)) <= 1


async def collect(base_url: str) -> dict[str, Any]:
    config = load_config()
    body = _request_body(compute_max_tokens(20))
    batches = {str(size): await _run_batch(base_url, body, size) for size in BATCH_SIZES}
    sequential = await _run_sequential(base_url, body, SEQUENTIAL_RUNS)
    return {"batches": batches, "sequential": sequential, "codebook_version": config.llm.codebook_version}


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
    log(f"- {SEQUENTIAL_RUNS} consecutive sequential calls (batch_size=1) identical = {sequential_ok}")
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="vLLM's OpenAI-compatible base URL")
    parser.add_argument("--save", type=Path, help="write raw results to this JSON file")
    parser.add_argument(
        "--compare", type=Path, help="compare fresh results against a previously --save'd JSON file"
    )
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    log(f"# vLLM batching determinism protocol (§15bis.5) -- model={MODEL}, base_url={args.base_url}\n")
    log("## Within this run\n")
    data = await collect(args.base_url)
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
