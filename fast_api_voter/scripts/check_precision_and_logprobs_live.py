"""
scripts/check_precision_and_logprobs_live.py

Live verification of the two remaining offline-only changes from
plan-llm-protocol-and-theory-program.md §5.B/§5.C, now that the shared
server is free (Phase 7's scale-probe run completed):

1. chamber_deliberation's 2-decimal position precision (_PROMPT_VECTOR_
   PRECISION) -- exercised live for the first time here; vote_cast's own
   version was already exercised live via check_vote_cast_truncation_fix.py
   and the earlier flagship smoke run.
2. VllmJsonClient.complete_with_logprobs itself, against the real server --
   only mocked-transport tests have exercised it so far.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_precision_and_logprobs_live.py
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
    decide_chamber_deliberation,
)
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
    c.chamber_position = c.issue_positions
    return c


def main() -> int:
    config = _vllm_config()

    print("== 1. chamber_deliberation with 2-decimal position precision (live, first time) ==")
    members = [_chamber_member(2000 + i) for i in range(10)]
    contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        start = time.perf_counter()
        outcome = decide_chamber_deliberation(members, contexts, config, client)
        elapsed = time.perf_counter() - start
    n_fallback = sum(outcome.llm_fallback.values())
    sincere = sum(1 for d in outcome.decisions if d.motif == 701)
    print(f"elapsed={elapsed:.1f}s decisions={len(outcome.decisions)} sincere={sincere}/10 fallback={n_fallback}")

    print("\n== 2. VllmJsonClient.complete_with_logprobs against the real server ==")
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        content, tokens = client.complete_with_logprobs(
            system_prompt="Tu reponds uniquement par 'oui' ou 'non', rien d'autre.",
            user_prompt="Est-ce que 2+2 fait 4 ?",
            max_tokens=1,
            top_logprobs=5,
        )
    print(f"content={content!r}")
    for t in tokens:
        print(f"  token={t.token!r} logprob={t.logprob:.4f} alternatives={t.alternatives}")

    ok = n_fallback == 0 and len(tokens) >= 1 and content.strip() != ""
    print("\nBOTH LIVE-VERIFIED" if ok else "\nSOMETHING DID NOT WORK AS EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
