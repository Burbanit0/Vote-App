"""
scripts/check_vote_cast_prefix_cache_fix.py

Live verification of the 2026-09-10 build_system_prompt/build_user_prompt
restructuring (plan-llm-protocol-and-theory-program.md §3.B.7): the
per-chunk cid list moved out of the system prompt (where it broke prefix-
cache continuity for every chunk of the same election, measured directly:
two chunks' own system prompts used to diverge 84% through) into
build_user_prompt's own `expected_cids` field instead.

This checks TWO things against the real server:
1. Decision correctness is unaffected -- ground truth via
   simple_rules.build_ranking, same rigor as every other change this
   session (the prompt semantics did not change, only where the cid data
   lives, but this is not assumed safe without a live check).
2. The real, isolated prefix-cache hit rate during a burst of consecutive
   chunks from the SAME election (fixed candidates, six different voter
   chunks) -- read directly from vLLM's own periodic log line, not
   estimated.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vote_cast_prefix_cache_fix.py
"""
from __future__ import annotations

import dataclasses
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import cast_votes  # noqa: E402
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import BLANK_LABEL, assign_party_affiliation, build_ranking, declare_candidacy  # noqa: E402


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def main() -> int:
    config = _vllm_config()
    citizens = generate_population(config.citizens, 60, config.run.seed)
    parties = initialize_parties(citizens, 5, config.run.seed)
    for c in citizens:
        c.party_affiliation = assign_party_affiliation(c, parties)
    nominees = []
    for p in parties:
        members = [c for c in citizens if c.party_affiliation == p.party_id]
        if members:
            nominees.append(max(members, key=lambda c: (c.ambition_score, -c.citizen_id)))
    for n in nominees:
        declare_candidacy(n)
    nominees = sorted(nominees, key=lambda c: c.citizen_id)
    voters = [c for c in citizens if c not in nominees][:18]  # 6 chunks of 3, the shipped chunk size

    print(f"election: {len(nominees)} candidates, {len(voters)} voters -> 6 chunks of 3")
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        start = time.perf_counter()
        outcome = cast_votes(voters, nominees, config, client)
        elapsed = time.perf_counter() - start

    n_fallback = sum(outcome.llm_fallback.values())
    print(f"\nelapsed={elapsed:.1f}s voters={len(voters)} llm_fallback={n_fallback} "
          f"retried={sum(outcome.retry_sampling_varied.values())}")

    correct = 0
    for voter, ballot in zip(voters, outcome.ballots):
        full = build_ranking(voter, nominees)
        blank_index = full.index(BLANK_LABEL)
        expected = full[:blank_index] + [BLANK_LABEL] if blank_index > 0 else [BLANK_LABEL]
        if ballot == expected:
            correct += 1
    print(f"ground-truth correct (of non-fallback expectations): {correct}/{len(voters)}")

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
