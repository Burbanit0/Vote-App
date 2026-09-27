"""
scripts/check_shipped_chunk_size_smoke.py

A live smoke test of the SHIPPED production code path (cast_votes /
decide_chamber_deliberation, imported directly from llm_behavior_engine.py --
not the standalone measurement harness in check_vllm_chunk_size_throughput.py)
against the real vLLM server, after raising _VOTE_CAST_MAX_CHUNK_SIZE_VLLM=3 /
_CHAMBER_MAX_CHUNK_SIZE_VLLM=5 and switching both call sites to the dynamic
max_tokens probe. Unit tests cover this against fakes; this is the one check
that exercises the real HTTP round trips (including the new count_prompt_
tokens probe call) end to end before committing.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_shipped_chunk_size_smoke.py
"""
from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    _chamber_chunk_size,
    _vote_cast_chunk_size,
    cast_votes,
    decide_chamber_deliberation,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import BLANK_LABEL, assign_party_affiliation, build_ranking, declare_candidacy  # noqa: E402
from api.domain.polity.citizen import Citizen  # noqa: E402


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
    assert config.llm.provider == "vllm"
    print(f"_vote_cast_chunk_size = {_vote_cast_chunk_size(config)} (expect 3)")
    print(f"_chamber_chunk_size = {_chamber_chunk_size(config)} (expect 5)")

    citizens = generate_population(config.citizens, 20, config.run.seed)
    parties = initialize_parties(citizens, 5, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)
    nominees = []
    for party in parties:
        members = [c for c in citizens if c.party_affiliation == party.party_id]
        if members:
            nominees.append(max(members, key=lambda c: (c.ambition_score, -c.citizen_id)))
    for nominee in nominees:
        declare_candidacy(nominee)
    nominees = sorted(nominees, key=lambda c: c.citizen_id)
    voters = [c for c in citizens if c not in nominees][:10]

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        print("\n== cast_votes (12 voters, real code path, chunk_size=3) ==")
        start = time.perf_counter()
        outcome = cast_votes(voters, nominees, config, client)
        elapsed = time.perf_counter() - start
        print(f"elapsed={elapsed:.1f}s ballots={len(outcome.ballots)} "
              f"llm_fallback={sum(outcome.llm_fallback.values())} "
              f"retry_sampling_varied={sum(outcome.retry_sampling_varied.values())}")
        # ballot_from_decision's own contract deliberately diverges from
        # build_ranking's: it stops at Blank (acceptable candidates ranked,
        # then Blank), never appending build_ranking's own beyond-tolerance
        # tail -- so the correct comparison is against build_ranking's
        # PRE-blank prefix only, matching how cast_votes actually decodes
        # a decision (see resolve_ranking_cids/ballot_from_decision).
        correct = 0
        for voter, ballot in zip(voters, outcome.ballots):
            full = build_ranking(voter, nominees)
            blank_index = full.index(BLANK_LABEL)
            expected = full[:blank_index] + [BLANK_LABEL] if blank_index > 0 else [BLANK_LABEL]
            if ballot == expected:
                correct += 1
            else:
                print(f"  MISMATCH cid={voter.citizen_id}: got {ballot} expected {expected}")
        print(f"ground-truth correct: {correct}/{len(voters)}")

        print("\n== decide_chamber_deliberation (12 members, real code path, chunk_size=5) ==")
        members = [_chamber_member(500 + i) for i in range(12)]
        contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}
        start = time.perf_counter()
        chamber_outcome = decide_chamber_deliberation(members, contexts, config, client)
        elapsed = time.perf_counter() - start
        sincere = sum(1 for d in chamber_outcome.decisions if d.motif == 701)
        print(f"elapsed={elapsed:.1f}s decisions={len(chamber_outcome.decisions)} sincere={sincere}/12")

    print("\nSMOKE TEST PASSED" if correct == len(voters) else "\nSMOKE TEST HAD MISMATCHES")
    return 0 if correct == len(voters) else 1


if __name__ == "__main__":
    raise SystemExit(main())
