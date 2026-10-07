"""
scripts/resolution_2_1_temperature_0_7.py

plan-pressure-action-resolution.md §2.1 -- temperature=0.7 extension. temperature=0.3 was already
tested (plan-pressure-action-remediation.md §2.1, 0/4 flip, negative) -- this is NOT a fresh
hypothesis, low prior expectation, run anyway because near-zero cost. Registered experiment:
run `python -c "from llm_test_harness import storage; ..."` or see
plan-pressure-action-resolution.md for the experiment_id printed at registration time.

Same 5 cases as the original 0.3 test (4 extreme "should act" + 1 control), same production
5-way menu/prompt, size=1, think=False, temperature=0.7 (the one changed variable). Uses
pressure_action_harness.raw_pressure_call for full request/response capture.

Usage:
    python fast_api_voter/scripts/resolution_2_1_temperature_0_7.py <experiment_id>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from llm_test_harness import trial  # noqa: E402
from pressure_action_harness import ACT_NAMES, ACTING_CODES, raw_pressure_call, to_trial_result  # noqa: E402

_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_TEMPERATURE = 0.7

# Same 5 cases as plan-pressure-action-remediation.md §2.1's original temperature=0.3 test.
_CASES = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "expected_act": True},
    {"cid": 152, "self_gap": 0.3458, "blank_threshold": 0.1064, "expected_act": True},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "expected_act": True},
    {"cid": 146, "self_gap": 0.4161, "blank_threshold": 0.1736, "expected_act": True},
    {"cid": 158, "self_gap": 0.086, "blank_threshold": 0.487, "expected_act": False},
]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: resolution_2_1_temperature_0_7.py <experiment_id>")
        return 1
    experiment_id = sys.argv[1]

    config = load_config()
    outcomes: list[bool | None] = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i, case in enumerate(_CASES, start=1):
            cid = int(case["cid"])
            gap = float(case["self_gap"])
            expected_act = bool(case["expected_act"])
            ctx = PressureContext(
                cid=cid, target=_TARGET, self_gap=gap, mandate_dev=_MANDATE_DEV,
                ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            citizen_stub = type("C", (), {"citizen_id": cid})()
            system_prompt = build_pressure_system_prompt([citizen_stub], config)
            user_prompt = build_pressure_user_prompt([citizen_stub], {cid: ctx})
            case_outcome: dict[str, bool | None] = {"agree": None}

            def run_call(
                gap: float = gap, cid: int = cid, expected_act: bool = expected_act,
                system_prompt: str = system_prompt, user_prompt: str = user_prompt,
                case_outcome: dict[str, bool | None] = case_outcome,
            ) -> trial.TrialResult:
                raw = raw_pressure_call(
                    client, system_prompt, user_prompt, PRESSURE_JSON_SCHEMA,
                    compute_max_tokens(1), temperature=_TEMPERATURE,
                )
                actual_act = None
                agree = None
                if raw.content:
                    try:
                        parsed = json.loads(raw.content)
                        act = parsed["decisions"][0]["act"]
                        actual_act = act in ACTING_CODES
                        agree = actual_act == expected_act
                        print(f"  cid={cid} expected={expected_act} act={act} ({ACT_NAMES.get(act, '?')}) [{'AGREE' if agree else 'DISAGREE'}]")
                    except Exception as exc:  # noqa: BLE001
                        print(f"  cid={cid} decode failed: {exc}")
                case_outcome["agree"] = agree
                return to_trial_result(raw, {
                    "cid": cid, "self_gap": gap, "expected_act": expected_act,
                    "actual_act": actual_act, "agree": agree, "temperature": _TEMPERATURE,
                    "variant": "2.1_temperature_0.7",
                })

            trial.record_trial(experiment_id, i, container_name="ollama-polity", run_call=run_call)
            outcomes.append(case_outcome["agree"])

    checked = [o for o in outcomes if o is not None]
    correct = sum(1 for o in checked if o)
    print(f"\n--- result ---")  # noqa: F541
    print(f"checked: {len(checked)}/{len(_CASES)}")
    if checked:
        print(f"agreement: {correct}/{len(checked)} ({correct/len(checked):.1%})")
    print(f"All {len(_CASES)} trials recorded under experiment {experiment_id}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
