"""
scripts/check_pressure_action_temperature_diagnostic.py

Step 0.1 of plan-pressure-action-remediation.md -- a cheap diagnostic run BEFORE committing to any
of the three redesign paths (§3), to see whether they're even the right thing to prioritize.

Hypothesis: the total avoidance of acting codes could be, wholly or partly, a GREEDY-DECODING
artifact (one dominant token trajectory at temperature=0) rather than a learned content bias --
direct precedent in this project: temperature=0.3 on retry broke a degenerate deterministic loop
for cast_votes's own schema-incoherence bug (cache_recycle_chunk_size_tension_findings.md).

Protocol (fixed before running, per the plan): replay the same 4 extreme "should act" cases plus
the 1 control already used throughout this investigation, real UNMODIFIED production prompt,
size=1 (isolates batching, already-eliminated), think=False (production path), but temperature=0.3
instead of the shipped 0.0 -- the ONE variable changed.

Pre-registered criterion:
- If credible, ground-truth-consistent acting codes appear on the should-act cases -> decoding
  has a real component, temperature variation becomes a serious light-weight remediation
  candidate to test at scale BEFORE any prompt/schema redesign.
- If no change -> greedy decoding is ruled out as a factor; priority goes to the three redesign
  paths (§3), not a decoding tweak.

Usage:
    python fast_api_voter/scripts/check_pressure_action_temperature_diagnostic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}
_DIAGNOSTIC_TEMPERATURE = 0.3

# Same 5 cases as the ablation test, with size=1/think=False/temperature=0.0 baselines already measured.
_CASES: list[dict[str, int | float | str]] = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "baseline_act": 0, "role": "should-ACT (extreme)"},
    {"cid": 152, "self_gap": 0.3458, "blank_threshold": 0.1064, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 146, "self_gap": 0.4161, "blank_threshold": 0.1736, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 158, "self_gap": 0.086, "blank_threshold": 0.487, "baseline_act": 0, "role": "should-NOT-act (control)"},
]


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    results: dict[int, tuple[int, int]] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for case in _CASES:
            cid = int(case["cid"])
            citizen = citizens_by_id[cid]
            ctx = PressureContext(
                cid=cid, target=_TARGET, self_gap=float(case["self_gap"]), mandate_dev=_MANDATE_DEV,
                ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            raw = client.complete_json(
                system_prompt=build_pressure_system_prompt([citizen], config),
                user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
                temperature=_DIAGNOSTIC_TEMPERATURE,
            )
            decision = decode_pressure_batch(raw, [cid])[0]
            results[cid] = (decision.act, decision.motif)

    print(f"--- temperature={_DIAGNOSTIC_TEMPERATURE} results vs. baseline (real prompt, size=1, think=False, temperature=0.0) ---")
    for case in _CASES:
        cid = int(case["cid"])
        role = str(case["role"])
        baseline_act = int(case["baseline_act"])
        ratio = float(case["self_gap"]) / float(case["blank_threshold"])
        new_act, new_motif = results[cid]
        flip = "FLIPPED to acting" if (new_act in _ACTING_CODES and baseline_act not in _ACTING_CODES) else (
            "FLIPPED to non-acting" if (new_act not in _ACTING_CODES and baseline_act in _ACTING_CODES) else "unchanged"
        )
        print(
            f"cid={cid:>4} [{role}] ratio={ratio:.3f} "
            f"baseline={_ACT_NAMES[baseline_act]} -> t=0.3={_ACT_NAMES[new_act]} "
            f"(motif={new_motif}) [{flip}]"
        )

    should_act_flips = sum(
        1 for case in _CASES
        if str(case["role"]).startswith("should-ACT")
        and results[int(case["cid"])][0] in _ACTING_CODES
    )
    should_act_total = sum(1 for case in _CASES if str(case["role"]).startswith("should-ACT"))
    control_case = next(case for case in _CASES if "control" in str(case["role"]))
    control_flipped_to_acting = results[int(control_case["cid"])][0] in _ACTING_CODES

    print(f"\nshould-act cases now choosing an acting code: {should_act_flips}/{should_act_total}")
    print(f"control case flipped to acting: {control_flipped_to_acting}")

    print("\n--- verdict, per the pre-registered criterion ---")
    if should_act_flips > 0:
        print(
            "Acting codes appeared -> decoding has at least a partial component. Temperature "
            "variation becomes a serious light-weight candidate to test at scale (>=60 unambiguous "
            "citizens) BEFORE committing to any of the three prompt/schema redesigns."
        )
    else:
        print(
            "Zero flips -> greedy decoding at temperature=0 is ruled out as a (sole) factor. "
            "Priority goes to the three redesign paths (binary-then-lever, primary-language + "
            "algorithmic translation, few-shot), not a decoding tweak."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
