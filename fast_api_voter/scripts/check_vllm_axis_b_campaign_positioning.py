"""
scripts/check_vllm_axis_b_campaign_positioning.py

plan-vllm-switch-readiness.md's axis (b), point 1: does vLLM's AWQ-quantized Qwen3-8B-AWQ reason
comparably to Ollama's un-quantized qwen3:8b on campaign_positioning's own already-characterized
hard cases? Reuses the EXACT same 6 cids, population_size, seed, and think=True/8000-token
protocol as validate_campaign_positioning_disambiguation_fix.py (the live validation of the
2026-08-31 disambiguation fix) for direct comparability -- only the client changes, Ollama to
vLLM. That script's own pre-fix/post-fix Ollama baseline:
  - fix targets (167/209/158): 6/6 truncated pre-fix, <=1/9 post-fix (validated live)
  - cid=79: a DIFFERENT, unaddressed root cause (model-internal array-transcription artifact,
    not a prompt ambiguity) -- 2/2 truncated pre-fix, not expected to improve on ANY backend
  - no-regression check (184/126): 0/2 truncated pre-fix and post-fix

This is axis (b), not axis (a): the question is whether the AWQ-quantized model's own reasoning
behavior on these prompts differs from the un-quantized model's, not whether vLLM-as-a-server
works (already confirmed separately, scripts/vllm_determinism_results.md).

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_axis_b_campaign_positioning.py
"""
from __future__ import annotations

import dataclasses
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_positioning_batch  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation  # noqa: E402

_POPULATION_SIZE = 300
_THINK_TOKEN_ALLOWANCE = 8000
_REPS = 3
_TARGET_CIDS = [184, 167, 126, 79, 209, 158]
_FIX_TARGETS = {167, 209, 158}
_KNOWN_DIFFERENT_CAUSE = {79}
_NO_REGRESSION_CHECK = {184, 126}


def _electorate_mean(population: list[Citizen]) -> tuple[float, ...]:
    issue_count = len(population[0].issue_positions)
    sums = [0.0] * issue_count
    for c in population:
        for i, v in enumerate(c.issue_positions):
            sums[i] += v
    return tuple(s / len(population) for s in sums)


def _classify_failure(message: str) -> str:
    if "finish_reason='length'" in message:
        return "truncation"
    if "batch misaligned" in message:
        return "cid_motif_leak_or_misalignment"
    return "other"


def main() -> int:
    shipped = load_config()
    vllm_url = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")
    config = dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url=vllm_url))

    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    mean = _electorate_mean(population)
    by_cid = {c.citizen_id: c for c in population}

    results: dict[int, list[str]] = {cid: [] for cid in _TARGET_CIDS}

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in _TARGET_CIDS:
            nominee = by_cid[cid]
            dist = math.dist(nominee.issue_positions, mean)
            print(f"\n########## cid={cid} (dist_to_mean={dist:.4f}) ##########")
            for rep in range(1, _REPS + 1):
                try:
                    raw = client.complete_json(
                        system_prompt=build_positioning_system_prompt([nominee], config),
                        user_prompt=build_positioning_user_prompt([nominee], parties_by_id, mean),
                        json_schema=POSITIONING_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE,
                        think=True,
                    )
                    decision = decode_positioning_batch(raw, [nominee.citizen_id])[0]
                    print(f"  rep{rep}: OK shifts={len(decision.shifts)} motif={decision.motif}")
                    results[cid].append("ok")
                except Exception as exc:  # noqa: BLE001 -- a failure IS the measurement here
                    mode = _classify_failure(str(exc))
                    print(f"  rep{rep}: FAILED ({mode}): {exc}")
                    results[cid].append(mode)

    print("\n--- result ---")
    for cid in _TARGET_CIDS:
        outcomes = results[cid]
        truncations = outcomes.count("truncation")
        label = (
            "FIX TARGET" if cid in _FIX_TARGETS
            else "DIFFERENT CAUSE (not addressed)" if cid in _KNOWN_DIFFERENT_CAUSE
            else "no-regression check"
        )
        print(f"  cid={cid} [{label}]: {outcomes} -- {truncations}/{_REPS} truncated")

    fix_target_outcomes = [o for cid in _FIX_TARGETS for o in results[cid]]
    fix_target_truncations = fix_target_outcomes.count("truncation")
    print(f"\nFix targets (167/209/158) combined: {fix_target_truncations}/{len(fix_target_outcomes)} truncated")
    print(
        "PASSES" if fix_target_truncations <= 1 else "FAILS",
        "the Ollama-established bar (<=1/9 truncations on the targeted cases) under vLLM/AWQ",
    )

    different_cause_outcomes = results[79]
    different_cause_truncations = different_cause_outcomes.count("truncation")
    print(f"cid=79 (different, unaddressed cause): {different_cause_truncations}/{_REPS} truncated (Ollama: 2/2)")

    no_regression_outcomes = [o for cid in _NO_REGRESSION_CHECK for o in results[cid]]
    no_regression_truncations = no_regression_outcomes.count("truncation")
    print(f"No-regression check (184/126): {no_regression_truncations}/{len(no_regression_outcomes)} truncated (Ollama: 0/2 each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
