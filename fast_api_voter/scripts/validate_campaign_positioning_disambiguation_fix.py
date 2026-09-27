"""
scripts/validate_campaign_positioning_disambiguation_fix.py

Live validation of the 2026-08-31 disambiguation fix to build_positioning_system_prompt (see that
function's own docstring and plan-adversarial-framing-collapse.md's campaign_positioning section):
a sentence was inserted between CAMPAIGN_MOTIF_PROMPT_TABLE and the "la liste decisions doit
contenir EXACTEMENT" self-check, targeting the exact misreading found by reading the full raw
reasoning traces of 3 reproduced Mode A truncations (cid 167, 209, 158) -- the model believed the
cid-list constraint and the motif code menu (601-604) were in conflict, and looped instead of
concluding, despite having already worked out a substantively complete answer.

Re-runs the SAME 6 cids already characterized in check_campaign_positioning_truncation_reasoning.py
(184, 167, 126, 79, 209, 158 -- population_size=300, same seed, same think=True/size=1/8000-token
protocol), 3x each, to get a non-determinism-adjusted read. cid=79's truncation has a DIFFERENT,
NOT-addressed root cause (a data-transcription artifact, not a prompt ambiguity, see the docstring)
-- tracked separately, not expected to improve. cid=184/126 (0/2 truncations pre-fix) are a
no-regression check. Pre-registered: experiment 20260901T003657Z-0a0e4d59.

Usage:
    python fast_api_voter/scripts/validate_campaign_positioning_disambiguation_fix.py
"""
from __future__ import annotations

import math
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
from api.domain.polity.llm_client import OllamaJsonClient, decode_positioning_batch  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation  # noqa: E402
from llm_test_harness import trial  # noqa: E402

_POPULATION_SIZE = 300
_THINK_TOKEN_ALLOWANCE = 8000
_REPS = 3
_TARGET_CIDS = [184, 167, 126, 79, 209, 158]
_FIX_TARGETS = {167, 209, 158}  # the 3 cases whose root cause this fix addresses
_KNOWN_DIFFERENT_CAUSE = {79}  # NOT addressed by this fix, tracked separately
_NO_REGRESSION_CHECK = {184, 126}  # 0/2 truncations pre-fix


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
    experiment_id = "20260901T003657Z-0a0e4d59"

    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    mean = _electorate_mean(population)
    by_cid = {c.citizen_id: c for c in population}

    results: dict[int, list[str]] = {cid: [] for cid in _TARGET_CIDS}
    trial_index = 0

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in _TARGET_CIDS:
            nominee = by_cid[cid]
            dist = math.dist(nominee.issue_positions, mean)
            print(f"\n########## cid={cid} (dist_to_mean={dist:.4f}) ##########")
            for rep in range(1, _REPS + 1):
                trial_index += 1

                def run_call(nominee: Citizen = nominee, cid: int = cid, rep: int = rep) -> trial.TrialResult:
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
                        return trial.TrialResult(ok=True, finish_reason="stop", truncated=False, decoded_tokens=None, detail=f'{{"cid": {cid}, "rep": {rep}, "outcome": "ok"}}')
                    except Exception as exc:  # noqa: BLE001 -- a failure IS the measurement here
                        mode = _classify_failure(str(exc))
                        print(f"  rep{rep}: FAILED ({mode}): {exc}")
                        results[cid].append(mode)
                        return trial.TrialResult(
                            ok=False, finish_reason=("length" if mode == "truncation" else "error"),
                            truncated=(mode == "truncation"), decoded_tokens=None,
                            detail=f'{{"cid": {cid}, "rep": {rep}, "outcome": "{mode}"}}',
                        )

                trial.record_trial(experiment_id, trial_index, container_name="ollama-polity", run_call=run_call)

    print("\n--- result ---")
    for cid in _TARGET_CIDS:
        outcomes = results[cid]
        truncations = outcomes.count("truncation")
        label = "FIX TARGET" if cid in _FIX_TARGETS else ("DIFFERENT CAUSE (not addressed)" if cid in _KNOWN_DIFFERENT_CAUSE else "no-regression check")
        print(f"  cid={cid} [{label}]: {outcomes} -- {truncations}/{_REPS} truncated")

    fix_target_outcomes = [o for cid in _FIX_TARGETS for o in results[cid]]
    fix_target_truncations = fix_target_outcomes.count("truncation")
    print(f"\nFix targets (167/209/158) combined: {fix_target_truncations}/{len(fix_target_outcomes)} truncated (pre-fix: 6/6)")
    print("PASSES" if fix_target_truncations <= 1 else "FAILS", "the pre-registered bar (<=1/9 truncations on the targeted cases)")

    different_cause_outcomes = results[79]
    different_cause_truncations = different_cause_outcomes.count("truncation")
    print(f"cid=79 (different, unaddressed cause): {different_cause_truncations}/{_REPS} truncated (pre-fix: 2/2) -- not expected to improve")

    no_regression_outcomes = [o for cid in _NO_REGRESSION_CHECK for o in results[cid]]
    no_regression_truncations = no_regression_outcomes.count("truncation")
    print(f"No-regression check (184/126): {no_regression_truncations}/{len(no_regression_outcomes)} truncated (pre-fix: 0/2 each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
