"""
scripts/check_dynamic_budget_latency_regression.py

Phase 7's smoke run (plan-flagship-30y-run.md) came back 1.88x SLOWER than the
pre-chunk-size baseline (4257.6s vs 2266.8s, same 2y/pop100/vllm config) --
the opposite of what check_vllm_chunk_size_throughput_results.md predicted.
That investigation only ever compared chunk sizes AGAINST EACH OTHER under
the new dynamic-max-tokens budget strategy; it never compared the dynamic
strategy against the ORIGINAL flat-allowance strategy at the SAME chunk size,
so a regression from the budget strategy itself (independent of chunk size)
would have been invisible to it. This isolates that one variable directly,
at chunk_size=1 held fixed, on real chamber_deliberation prompts.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_dynamic_budget_latency_regression.py
"""
from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    _CHAMBER_THINK_TOKEN_ALLOWANCE,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_chamber_batch  # noqa: E402
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA  # noqa: E402

_REPS = 5


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _chamber_member(cid: int) -> Citizen:
    c = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.031 + d * 0.017) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions
    return c


def main() -> int:
    config = _vllm_config()
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        print("| rep | budget_strategy | max_tokens | elapsed(s) |")
        print("|---|---|---|---|")
        for rep in range(_REPS):
            member = _chamber_member(700 + rep)
            sp = build_chamber_system_prompt([member], config)
            up = build_chamber_user_prompt([member], {member.citizen_id: ChamberContext(cid=member.citizen_id, ticks_left=12)})

            flat_budget = compute_max_tokens(1) + _CHAMBER_THINK_TOKEN_ALLOWANCE
            start = time.perf_counter()
            raw = client.complete_json(system_prompt=sp, user_prompt=up, json_schema=CHAMBER_JSON_SCHEMA, max_tokens=flat_budget, think=True)
            elapsed_flat = time.perf_counter() - start
            decode_chamber_batch(raw, [member.citizen_id])
            print(f"| {rep} | FLAT (shipped-before-2026-09-08) | {flat_budget} | {elapsed_flat:.1f} |")

            prompt_tokens = client.count_prompt_tokens(system_prompt=sp, user_prompt=up, think=True)
            dyn_budget = max(compute_max_tokens(1), 16384 - prompt_tokens - 300)
            start = time.perf_counter()
            raw2 = client.complete_json(system_prompt=sp, user_prompt=up, json_schema=CHAMBER_JSON_SCHEMA, max_tokens=dyn_budget, think=True)
            elapsed_dyn = time.perf_counter() - start
            decode_chamber_batch(raw2, [member.citizen_id])
            print(f"| {rep} | DYNAMIC (shipped now) | {dyn_budget} (prompt_tokens={prompt_tokens}) | {elapsed_dyn:.1f} |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
