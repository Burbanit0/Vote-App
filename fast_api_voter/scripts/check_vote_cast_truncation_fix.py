"""
scripts/check_vote_cast_truncation_fix.py

Live verification of the 2026-09-10 build_system_prompt fix
(plan-flagship-30y-run.md Phase 7 Stage 3): reproduces the EXACT failure
shape found in the scale-probe run (candidate_count > 6, e.g. an election
with several rupture candidates on top of the 5 party nominees) and checks
that the fallback storm it caused is gone.

Before the fix: build_system_prompt told the model, unconditionally, to
rank EVERY acceptable candidate -- directly contradicting validate_decision's
own truncate_at=5 rejection once candidate_count > 6. Two real election
ticks in the scale-probe fell back 494/500 and 476/500 votes to this exact
mechanism (replays.log: "ranks N candidates, exceeding the truncation limit
of 5", N observed up to 15).

Note: `_deterministic_vote_fallback` (the fallback path itself) reuses
simple_rules.build_ranking, which does NOT truncate -- that's correct and
expected, since §3.6.1's truncation rule is an LLM-response-size protocol
constraint, not a deeper simulation rule, so this script only checks
ranking length among the NON-fallback (real LLM) decisions.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vote_cast_truncation_fix.py
"""
from __future__ import annotations

import dataclasses
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_system_prompt,
    cast_votes,
    truncation_limit,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy  # noqa: E402

_N_VOTERS = 24
_N_CANDIDATES = 12  # matches the scale-probe's own observed range (11-15)


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def main() -> int:
    config = _vllm_config()
    citizens = generate_population(config.citizens, 80, config.run.seed)
    parties = initialize_parties(citizens, _N_CANDIDATES, config.run.seed)
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
    voters = [c for c in citizens if c not in nominees][:_N_VOTERS]

    truncate_at = truncation_limit(len(nominees))
    print(f"candidates={len(nominees)} truncate_at={truncate_at} (expect not None -- the bug's trigger condition)")
    assert truncate_at is not None, "this probe needs >6 candidates to exercise the fixed branch at all"

    prompt_sample = build_system_prompt(voters[:1], nominees)
    assert "JUSQU'A" in prompt_sample
    assert "OBLIGATOIREMENT contenir CHAQUE candidat" not in prompt_sample
    print("prompt wording check: OK (truncated branch present, unconditional branch absent)")

    # A decision exceeding truncate_at can never appear in outcome.decisions
    # itself -- cast_votes's own except-LlmResponseError handler catches
    # validate_decision's rejection and falls the whole chunk back before
    # it's ever added there. The only place the truncation-limit failure
    # mode is still observable is the WARNING _complete_and_decode_with_
    # replay logs on the way to that fallback -- capture those directly
    # instead of inspecting outcome.decisions post hoc.
    captured_logs: list[str] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured_logs.append(record.getMessage())

    engine_logger = logging.getLogger("api.domain.polity.llm_behavior_engine")
    handler = _CaptureHandler()
    engine_logger.addHandler(handler)
    engine_logger.setLevel(logging.WARNING)
    try:
        with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
            start = time.perf_counter()
            outcome = cast_votes(voters, nominees, config, client)
            elapsed = time.perf_counter() - start
    finally:
        engine_logger.removeHandler(handler)

    n_fallback = sum(outcome.llm_fallback.values())
    n_retried = sum(outcome.retry_sampling_varied.values())
    print(f"\nelapsed={elapsed:.1f}s voters={len(voters)} llm_fallback={n_fallback} retried={n_retried}")

    truncation_failures = [line for line in captured_logs if "exceeding the truncation limit" in line]
    other_failures = [line for line in captured_logs if "exceeding the truncation limit" not in line
                       and ("rejected on attempt" in line or "exhausted every recovery attempt" in line)]
    print(f"truncation-limit failures: {len(truncation_failures)} (must be 0 -- this is the actual bug fixed)")
    print(f"other failures (pre-existing, unrelated quirks -- e.g. blank+non-empty-ranking §3.6.1): "
          f"{len(other_failures)}")

    fallback_rate = n_fallback / len(voters)
    print(f"llm_fallback rate: {100 * fallback_rate:.1f}% "
          f"-- compare to the scale-probe's own ~95-99% at this candidate count before the fix")

    ok = not truncation_failures
    print("\nFIX VERIFIED LIVE (zero truncation-limit violations)" if ok
          else "\nFIX DID NOT RESOLVE THE ISSUE -- truncation-limit violations still present")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
