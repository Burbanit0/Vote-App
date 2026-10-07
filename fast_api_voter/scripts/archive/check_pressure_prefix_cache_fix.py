"""
scripts/check_pressure_prefix_cache_fix.py

Live verification of the 2026-09-10 build_pressure_system_prompt/build_
pressure_user_prompt restructuring (plan-llm-protocol-and-theory-
program.md §3.B.7, the same fix already shipped for vote_cast and
chamber_deliberation): the per-chunk cid list moved out of the system
prompt (where it broke prefix-cache continuity for every chunk) into
build_pressure_user_prompt's own `expected_cids` field.

pressure_action's own version of this fix is the most complete of the
three: build_pressure_system_prompt no longer reads its `consulted`
parameter AT ALL (confirmed structurally by
test_pressure_system_prompt_is_identical_across_different_chunks), so its
output is a pure function of `config` -- a constant for the whole run at
a fixed config, not merely stable within one chunk or one tick.

This checks TWO things against the real server:
1. Decision correctness is unaffected -- the closed shipped menu's own
   deterministic proxy (simple_rules.deterministic_pressure_action) gives
   a real, if weak, reference direction; decode success and menu-legality
   are also checked directly.
2. The real, isolated prefix-cache hit rate during a burst of consecutive
   pressure_action chunks -- read directly from vLLM's own periodic log
   line, not estimated.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_prefix_cache_fix.py
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import deterministic_pressure_action  # noqa: E402

_TARGET_CID = 999
_TICKS_TO_ELECTION = 10
_MANDATE_DEV = 0.1
_CHUNK_SIZE = 5
_N_CHUNKS = 6  # 30 citizens across 6 chunks -- the same burst size vote_cast/chamber used


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid, target=_TARGET_CID, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
    )
    return citizen, context


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)

    n_correct = 0
    n_total = 0
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for chunk_i in range(_N_CHUNKS):
            # self_gap spans clearly-satisfied to clearly-discontented across
            # chunks, so this burst exercises real content, not one constant.
            citizens, contexts = [], {}
            for j in range(_CHUNK_SIZE):
                gap = 0.05 + (chunk_i * _CHUNK_SIZE + j) * (2.2 / (_N_CHUNKS * _CHUNK_SIZE))
                cid = 7000 + chunk_i * _CHUNK_SIZE + j
                citizen, context = _probe_citizen(cid, gap)
                citizens.append(citizen)
                contexts[cid] = context
            expected_cids = [c.citizen_id for c in citizens]

            system_prompt = build_pressure_system_prompt(citizens, config)
            user_prompt = build_pressure_user_prompt(citizens, contexts)
            content = client.complete_json(
                system_prompt=system_prompt, user_prompt=user_prompt,
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(len(citizens)), think=False,
            )
            decisions = decode_pressure_batch(content, expected_cids)
            for decision in decisions:
                citizen = next(c for c in citizens if c.citizen_id == decision.cid)
                gap = contexts[decision.cid].self_gap
                proxy = int(deterministic_pressure_action(citizen, gap, config.pressure_menu))
                n_total += 1
                n_correct += int(decision.act == proxy)
            print(f"chunk {chunk_i}: {len(decisions)}/{len(citizens)} decoded, "
                  f"acts={[d.act for d in decisions]}")

    print(f"\ndecoded cleanly: {n_total}/{_N_CHUNKS * _CHUNK_SIZE}")
    print(f"agreement with deterministic proxy (reference direction, not ground truth): "
          f"{n_correct}/{n_total}")

    print("\n== vLLM's own prefix-cache hit-rate log lines during this burst ==")
    logs = subprocess.run(
        ["docker", "logs", "vllm-polity", "--since", "2m"], capture_output=True, text=True, check=False,
    ).stdout
    for line in logs.splitlines():
        if "Prefix cache hit rate" in line:
            print(line.split("loggers.py:310]")[-1].strip())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
