"""
scripts/check_chamber_prefix_cache_fix.py

Live verification of the 2026-09-10 build_chamber_system_prompt/
build_chamber_user_prompt restructuring (plan-llm-protocol-and-theory-
program.md §3.B.7), the same fix already shipped for vote_cast
(check_vote_cast_prefix_cache_fix.py) and now applied to chamber_
deliberation: the per-chunk cid list moved out of the system prompt
(where it broke prefix-cache continuity across chunks) into build_
chamber_user_prompt's own `expected_cids` field.

Chamber has no `candidates`-style shared user-prompt section the way
vote_cast does, so the win here is expected to be narrower -- only the
system prompt itself becoming a stable, cacheable prefix across chunks,
not also unlocking shared user-prompt content. This script measures
whatever is actually observed rather than assuming vote_cast's magnitude
transfers.

This checks TWO things against the real server:
1. Decision correctness/reliability is unaffected -- fallback rate and
   sincere-motif sanity, same rigor as every other change this session
   (the prompt semantics did not change, only where the cid data lives).
2. The real, isolated prefix-cache hit rate during a burst of consecutive
   chunks -- read directly from vLLM's own periodic log line.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_chamber_prefix_cache_fix.py
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import ChamberContext, decide_chamber_deliberation  # noqa: E402
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _chamber_member(cid: int) -> Citizen:
    c = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.023 + d * 0.011) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions  # seated state: pinned to sincere anchor
    return c


def main() -> int:
    config = _vllm_config()
    members = [_chamber_member(3000 + i) for i in range(30)]  # 6 chunks of 5, the shipped chamber chunk size
    contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}

    print(f"chamber: {len(members)} members -> 6 chunks of 5")
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        start = time.perf_counter()
        outcome = decide_chamber_deliberation(members, contexts, config, client)
        elapsed = time.perf_counter() - start

    n_fallback = sum(outcome.llm_fallback.values())
    n_retried = sum(outcome.retry_sampling_varied.values())
    sincere = sum(1 for d in outcome.decisions if d.motif == 701)
    print(f"\nelapsed={elapsed:.1f}s decisions={len(outcome.decisions)} "
          f"sincere={sincere}/{len(members)} llm_fallback={n_fallback} retried={n_retried}")

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
