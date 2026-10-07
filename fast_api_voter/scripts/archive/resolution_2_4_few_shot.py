"""
scripts/resolution_2_4_few_shot.py

plan-pressure-action-resolution.md §2.4 -- adds 2 worked examples (one "should act", one "should
not act") to production's own system prompt, built on real values from the 70-citizen dataset
already harvested for §3.1/§3.2/§2.3 (pressure_action_harness.harvest_unambiguous_citizens), not
invented. Selection rule fixed BEFORE any call, mechanically (most extreme ratio per pole among
the 70) -- see plan-pressure-action-resolution.md §2.4's own methodological warning against
picking examples after seeing results.

Example act/motif choice: the harvested dataset only encodes a binary ground truth (should act /
should not); it says nothing about WHICH of act=1/2/3 is "correct" for the should-act pole. Since
every case here uses petition_open=False (same ctx convention as every prior script this
investigation), SIGN_PETITION(1) would contradict its own precondition (nothing to sign) -- the
mechanically consistent choice is LAUNCH_PETITION(2) with motif=301 (MANDATE_DEVIATION_HIGH).
The should-not-act pole uses NOTHING(0) with motif=304 (RESIGNATION_NO_LEVERAGE), the standard
grounding for that pole throughout this investigation's prior scripts.

Critically, per the §2.3 finding (a raw agreement rate on an imbalanced test set can pass a
threshold purely because the null/always-NOTHING policy already clears it): this script reports
the should-act-only subset explicitly, and does not treat the combined 80% bar alone as sufficient
-- see plan-pressure-action-resolution.md §2.4's corrected criterion.

Usage:
    python fast_api_voter/scripts/resolution_2_4_few_shot.py <experiment_id>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import Any  # noqa: E402

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from llm_test_harness import trial  # noqa: E402
from pressure_action_harness import (  # noqa: E402
    ACT_NAMES,
    ACTING_CODES,
    MANDATE_DEV,
    TICKS_TO_ELECTION,
    harvest_unambiguous_citizens,
    raw_pressure_call,
    to_trial_result,
)

_SCHEMA_INSTRUCTION = "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
_SHOULD_ACT_MOTIF = 301  # MANDATE_DEVIATION_HIGH
_SHOULD_ACT_ACT = 2  # LAUNCH_PETITION -- petition_open=False, so SIGN_PETITION would be incoherent
_SHOULD_NOT_ACT_MOTIF = 304  # RESIGNATION_NO_LEVERAGE
_SHOULD_NOT_ACT_ACT = 0  # NOTHING


def _example_ctx_payload(cid: int, target: int, gap: float) -> dict[str, object]:
    return {
        "cid": cid, "target": target,
        "ctx": {
            "self_gap": round(gap, 4), "mandate_dev": MANDATE_DEV,
            "neighbors_acting": None, "ticks_to_election": TICKS_TO_ELECTION,
        },
        "available": [0, 1, 2, 3, 4],
        "petition": {"open": False, "expires_at_tick": None, "already_signed": False},
    }


def build_few_shot_examples_block(
    should_act_cid: int, should_act_gap: float, should_not_act_cid: int, should_not_act_gap: float, target: int,
) -> str:
    example_1_input = json.dumps(
        {"consulted": [_example_ctx_payload(should_act_cid, target, should_act_gap)]},
        sort_keys=True, separators=(",", ":"),
    )
    example_1_output = json.dumps(
        {"decisions": [{"cid": should_act_cid, "act": _SHOULD_ACT_ACT, "motif": _SHOULD_ACT_MOTIF, "target": target}]},
        sort_keys=True, separators=(",", ":"),
    )
    example_2_input = json.dumps(
        {"consulted": [_example_ctx_payload(should_not_act_cid, target, should_not_act_gap)]},
        sort_keys=True, separators=(",", ":"),
    )
    example_2_output = json.dumps(
        {"decisions": [{"cid": should_not_act_cid, "act": _SHOULD_NOT_ACT_ACT, "motif": _SHOULD_NOT_ACT_MOTIF, "target": target}]},
        sort_keys=True, separators=(",", ":"),
    )
    return (
        "EXEMPLES (deux precedents concrets, valeurs reelles, pour ancrer "
        "la regle abstraite ci-dessus) :\n"
        f"Exemple 1 -- ecart largement au-dessus du seuil, aucune "
        f"petition en cours : entree {example_1_input} -> reponse "
        f"correcte {example_1_output}\n"
        f"Exemple 2 -- ecart largement en-dessous du seuil, aucune "
        f"petition en cours : entree {example_2_input} -> reponse "
        f"correcte {example_2_output}\n"
    )


def build_few_shot_system_prompt(citizen_stub: Any, config: PolityConfig, examples_block: str) -> str:
    """Production's own build_pressure_system_prompt, with the 2 worked examples inserted
    immediately before the trailing schema-conformance instruction -- see module docstring.
    Fails loudly if production's exact wording ever changes, so this test can't silently drift
    into testing a stale prompt shape."""
    base = build_pressure_system_prompt([citizen_stub], config)
    if _SCHEMA_INSTRUCTION not in base:
        raise RuntimeError(
            "build_pressure_system_prompt's trailing instruction line has changed -- "
            "update _SCHEMA_INSTRUCTION in resolution_2_4 to match before rerunning."
        )
    return base.replace(_SCHEMA_INSTRUCTION, examples_block + _SCHEMA_INSTRUCTION)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: resolution_2_4_few_shot.py <experiment_id>")
        return 1
    experiment_id = sys.argv[1]

    config = load_config()
    holder, all_cases = harvest_unambiguous_citizens(config)
    print(f"harvested {len(all_cases)} unambiguous citizens (holder=cid{holder.citizen_id})")

    should_act_cases = [c for c in all_cases if c[2]]
    should_not_act_cases = [c for c in all_cases if not c[2]]
    example_should_act = max(should_act_cases, key=lambda c: c[1] / c[0].blank_threshold)
    example_should_not_act = min(should_not_act_cases, key=lambda c: c[1] / c[0].blank_threshold)
    print(
        f"selected examples (mechanical, most-extreme-ratio-per-pole): "
        f"should_act=cid{example_should_act[0].citizen_id} "
        f"(ratio={example_should_act[1] / example_should_act[0].blank_threshold:.2f}), "
        f"should_not_act=cid{example_should_not_act[0].citizen_id} "
        f"(ratio={example_should_not_act[1] / example_should_not_act[0].blank_threshold:.2f})"
    )

    excluded_cids = {example_should_act[0].citizen_id, example_should_not_act[0].citizen_id}
    cases = [c for c in all_cases if c[0].citizen_id not in excluded_cids]
    print(f"test set: {len(cases)} cases (2 examples excluded)")

    examples_block = build_few_shot_examples_block(
        example_should_act[0].citizen_id, example_should_act[1],
        example_should_not_act[0].citizen_id, example_should_not_act[1],
        holder.citizen_id,
    )

    outcomes: list[bool | None] = []
    acting_codes_seen: set[int] = set()
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i, (citizen, gap, expected_act) in enumerate(cases, start=1):
            cid = citizen.citizen_id
            ctx = PressureContext(
                cid=cid, target=holder.citizen_id, self_gap=gap, mandate_dev=MANDATE_DEV,
                ticks_to_election=TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            citizen_stub = type("C", (), {"citizen_id": cid})()
            system_prompt = build_few_shot_system_prompt(citizen_stub, config, examples_block)
            user_prompt = build_pressure_user_prompt([citizen_stub], {cid: ctx})
            case_outcome: dict[str, bool | None] = {"agree": None}

            def run_call(
                gap: float = gap, cid: int = cid, expected_act: bool = expected_act,
                system_prompt: str = system_prompt, user_prompt: str = user_prompt,
                case_outcome: dict[str, bool | None] = case_outcome,
            ) -> trial.TrialResult:
                raw = raw_pressure_call(client, system_prompt, user_prompt, PRESSURE_JSON_SCHEMA, compute_max_tokens(1))
                actual_act = None
                agree = None
                act = None
                if raw.content:
                    try:
                        parsed = json.loads(raw.content)
                        act = parsed["decisions"][0]["act"]
                        actual_act = act in ACTING_CODES
                        agree = actual_act == expected_act
                        if actual_act:
                            acting_codes_seen.add(act)
                        print(f"  cid={cid} expected={expected_act} act={act} ({ACT_NAMES.get(act, '?')}) [{'AGREE' if agree else 'DISAGREE'}]")
                    except Exception as exc:  # noqa: BLE001
                        print(f"  cid={cid} decode failed: {exc}")
                case_outcome["agree"] = agree
                return to_trial_result(raw, {
                    "cid": cid, "self_gap": gap, "expected_act": expected_act,
                    "actual_act": actual_act, "agree": agree, "variant": "2.4_few_shot",
                })

            trial.record_trial(experiment_id, i, container_name="ollama-polity", run_call=run_call)
            outcomes.append(case_outcome["agree"])

    checked = [o for o in outcomes if o is not None]
    correct = sum(1 for o in checked if o)
    should_act_outcomes = [o for o, (_, _, expected) in zip(outcomes, cases) if expected]
    should_act_checked = [o for o in should_act_outcomes if o is not None]
    should_act_correct = sum(1 for o in should_act_checked if o)

    print("\n--- result ---")
    print(f"checked: {len(checked)}/{len(cases)}")
    if checked:
        rate = correct / len(checked)
        print(f"raw agreement (both poles): {correct}/{len(checked)} ({rate:.1%})")
        print("pre-registered threshold: >= 80%")
    if should_act_checked:
        sa_rate = should_act_correct / len(should_act_checked)
        print(f"should-act subset only: {should_act_correct}/{len(should_act_checked)} ({sa_rate:.1%}) -- the informative number")
    print(f"acting codes ever emitted: {sorted(acting_codes_seen) or 'NONE'}")
    print(f"All {len(cases)} trials recorded under experiment {experiment_id}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
