"""
scripts/check_vllm_prefix_cache_priming.py

plan-vllm-switch-readiness.md §3, axis (a)'s explicitly-named gap: none of the 8 tests in
test_polity_vllm_live.py reproduce the protocol that found Ollama's cross-request prompt-cache
corruption bug (llm_batching_determinism_results_gpu.md, "A third mechanism, found live:
cross-request prompt-cache reuse"). That mechanism is specific to llama.cpp's `cache_prompt: true`
fuzzy similarity-based cache (Ollama's own hardcoded setting, no per-request override exists) --
vLLM's engine reports `enable_prefix_caching=True` by default (confirmed live in this container's
own startup log), but its mechanism is architecturally different: PagedAttention does an EXACT
block-level prefix match, not a fuzzy "closest previous prompt" heuristic (llama.cpp's `f_keep`).
The absence of the SAME bug is expected by construction; the absence of ANY vLLM-specific
cache-interaction truncation mechanism is what this script actually tests, empirically.

Mirrors the causality-test protocol from llm_batching_determinism_results_gpu.md rather than
inventing a new one, for direct comparability: N independent trials, each priming the engine's
cache with a distinct, real, long think=True prompt (campaign_positioning's system+user prompt,
the same shape that triggered Ollama's bug), then immediately sending a cheap, previously-unseen,
think=False, single-citizen vote_cast call (compute_max_tokens(1) -- the production-sized budget
for that shape, not the original Ollama test's flat 50, which under-provisioned vLLM's own JSON
overhead and produced a false finish_reason='length' on every trial, both arms equally, before
this was caught and fixed) -- half sharing the prime's system-prompt text as a genuine prefix
(production's real shape: successive calls share large common system-prompt boilerplate), half an
unrelated control. Ollama's own version of this test found no difference between the two arms
(all 6/6 clean) yet the bug still fired on think=True/long-reasoning calls elsewhere -- so a clean
result here is evidence of absence for the CHEAP variant only, not proof no vLLM-specific mechanism
exists under think=True/long-reasoning load. Reported as such, not oversold.

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_prefix_cache_priming.py
"""
from __future__ import annotations

import dataclasses
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA, VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy  # noqa: E402

_N_TRIALS = 3  # matching the Ollama causality test's own 3+3 shape
_PRIME_POPULATION_SIZE = 300
_PRIME_THINK_TOKEN_ALLOWANCE = 8000


def _priming_prompts(seed_offset: int) -> tuple[str, str]:
    """A distinct, real, long think=True prompt each call -- campaign_positioning's own shape,
    the one that triggered Ollama's bug, varied per trial via a different candidate/electorate
    draw so no two primes are literally identical."""
    config = load_config()
    population = list(generate_population(config.citizens, _PRIME_POPULATION_SIZE, config.run.seed + seed_offset))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed + seed_offset)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    nominee = population[seed_offset % len(population)]
    issue_count = len(population[0].issue_positions)
    sums = [0.0] * issue_count
    for c in population:
        for i, v in enumerate(c.issue_positions):
            sums[i] += v
    mean = tuple(s / len(population) for s in sums)
    return (
        build_positioning_system_prompt([nominee], config),
        build_positioning_user_prompt([nominee], parties_by_id, mean),
    )


def _control_short_call(seed_offset: int) -> tuple[str, str]:
    """A cheap, unrelated vote_cast prompt -- never sharing text with the prime. Single citizen,
    not a batch: the point is a minimal call, and compute_max_tokens(1) below is sized for
    exactly one decision -- a bigger batch here would need proportionally more budget too, which
    is a real production concern (chunking) but not what this script tests."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [
        Citizen(
            citizen_id=9000 + seed_offset * 10 + i,
            issue_positions=tuple((i * 0.023 + seed_offset * 0.31 + d * 0.011) % 1.0 for d in range(dims)),
            issue_priorities=tuple(1.0 / dims for _ in range(dims)),
            blank_threshold=0.5,
            ambition_score=0.5,
        )
        for i in range(1)
    ]
    candidate = Citizen(
        citizen_id=9500 + seed_offset,
        issue_positions=tuple((seed_offset * 0.17 + d * 0.019) % 1.0 for d in range(dims)),
        issue_priorities=tuple(1.0 / dims for _ in range(dims)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    declare_candidacy(candidate)
    return build_system_prompt(citizens, [candidate]), build_user_prompt(citizens, [candidate])


def _shared_prefix_short_call(prime_system_prompt: str, seed_offset: int) -> tuple[str, str]:
    """Shares the prime's system-prompt text as a genuine prefix (production's real shape:
    successive calls share large common system-prompt boilerplate), but a distinct, never-before-
    seen user prompt so this is not literally the same request replayed."""
    _, control_user = _control_short_call(seed_offset)
    return prime_system_prompt, control_user


def main() -> int:
    shipped = load_config()
    vllm_url = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")
    config = dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url=vllm_url))
    results: list[dict[str, object]] = []

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for arm in ("shared_prefix", "control"):
            for trial in range(1, _N_TRIALS + 1):
                seed_offset = trial * 7 + (0 if arm == "shared_prefix" else 100)
                prime_sys, prime_user = _priming_prompts(seed_offset)
                print(f"\n[{arm} trial {trial}] priming with a long think=True positioning prompt...")
                t0 = time.monotonic()
                try:
                    client.complete_json(
                        system_prompt=prime_sys,
                        user_prompt=prime_user,
                        json_schema=POSITIONING_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1) + _PRIME_THINK_TOKEN_ALLOWANCE,
                        think=True,
                    )
                    prime_ok = True
                except Exception as exc:  # noqa: BLE001 -- report, keep going
                    prime_ok = False
                    print(f"  prime FAILED: {exc}")
                prime_elapsed = time.monotonic() - t0

                if arm == "shared_prefix":
                    short_sys, short_user = _shared_prefix_short_call(prime_sys, seed_offset)
                else:
                    short_sys, short_user = _control_short_call(seed_offset)

                t0 = time.monotonic()
                try:
                    client.complete_json(
                        system_prompt=short_sys,
                        user_prompt=short_user,
                        json_schema=VOTE_CAST_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1),
                        think=False,
                    )
                    short_ok, short_reason = True, "stop"
                except Exception as exc:  # noqa: BLE001 -- this IS the measurement
                    short_ok, short_reason = False, str(exc)
                short_elapsed = time.monotonic() - t0

                print(f"  prime: {'ok' if prime_ok else 'FAILED'} ({prime_elapsed:.1f}s)")
                print(f"  short call: {'ok' if short_ok else 'FAILED'} ({short_elapsed:.2f}s) {'' if short_ok else short_reason}")
                results.append({
                    "arm": arm, "trial": trial, "prime_ok": prime_ok,
                    "short_ok": short_ok, "short_elapsed": short_elapsed, "short_reason": short_reason,
                })

    print("\n--- result ---")
    for arm in ("shared_prefix", "control"):
        arm_results = [r for r in results if r["arm"] == arm]
        ok_count = sum(1 for r in arm_results if r["short_ok"])
        print(f"{arm}: {ok_count}/{len(arm_results)} short calls clean")

    all_ok = all(r["short_ok"] for r in results)
    print("\n--- verdict ---")
    if all_ok:
        print(
            f"All {len(results)} short calls (both arms) completed cleanly after priming with a "
            "distinct long think=True prompt each time. No cache-interaction corruption found on "
            "the cheap think=False variant this protocol can test -- consistent with, but not proof "
            "against, the architectural argument (exact block-level prefix match vs. llama.cpp's "
            "fuzzy similarity heuristic). Does not rule out a mechanism specific to think=True/"
            "long-reasoning generations, which this cheap protocol does not exercise (same caveat "
            "the original Ollama causality test carried)."
        )
    else:
        failed = [r for r in results if not r["short_ok"]]
        print(f"{len(failed)}/{len(results)} short calls FAILED after priming -- a real vLLM-specific "
              "cache-interaction mechanism may exist. Do not conclude axis (a) clean; investigate "
              "before proceeding.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
