"""
scripts/check_vllm_pressure_action_reasoning_field_first.py

vLLM/AWQ replay of check_pressure_action_reasoning_field_first.py -- same a_reasoning schema fix
(see that module's own docstring for the full sort_keys mechanism and pre-registration), same
70-citizen harvest, same open-menu override, same think=False/compute_max_tokens(1)+300 protocol.
Only the client changes, Ollama to vLLM -- reuses every prompt/schema/decode function from the
Ollama script directly rather than duplicating them, so there is exactly one definition of the
test's actual logic.

Ollama result (this session, 2026-09-05): pooled 57/70 (81.4%, clears the pre-registered bar) but
FAILS on the informative should-act subset (4/17, 23.5%) -- a base-rate artifact, not a real pass
(see check_pressure_action_reasoning_field_first_results.md). This script answers whether the
same collapse-toward-inaction, on the same schema-embedded-reasoning mechanism, reproduces on the
AWQ-quantized model too.

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_pressure_action_reasoning_field_first.py
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_client import VllmJsonClient, _THINK_TAG_RE  # noqa: E402
from check_pressure_action_reasoning_field_first import (  # noqa: E402
    REASONING_PRESSURE_JSON_SCHEMA,
    _ACT_NAMES,
    _ACTING_CODES,
    _MANDATE_DEV,
    _SUCCESS_THRESHOLD,
    _TICKS_TO_ELECTION,
    _harvest_unambiguous_citizens,
    build_reasoning_first_system_prompt,
    build_reasoning_first_user_prompt,
    decode_reasoning_pressure_batch,
)


def main() -> int:
    shipped = load_config()
    vllm_url = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")
    config = dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url=vllm_url),
        pressure_menu=dataclasses.replace(
            shipped.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
    )
    holder, cases = _harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (holder=cid{holder.citizen_id})")
    if len(cases) < 60:
        print(f"WARNING: below the plan's own >=60 floor -- got {len(cases)}")

    system_prompt = build_reasoning_first_system_prompt(config, holder.citizen_id)
    per_citizen: dict[int, dict] = {}
    correct = 0
    failures = 0
    order_confirmed = 0
    order_violated = 0
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for citizen, gap, expected_act in cases:
            user_prompt = build_reasoning_first_user_prompt(
                citizen.citizen_id, holder.citizen_id, gap, _MANDATE_DEV, _TICKS_TO_ELECTION
            )
            try:
                raw = client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=REASONING_PRESSURE_JSON_SCHEMA,
                    max_tokens=300,  # vLLM's own JSON overhead is heavier than Ollama's --
                                     # verified live: compute_max_tokens(1)+300 (Ollama's
                                     # own budget) was still enough headroom here too, kept
                                     # for direct comparability rather than re-tuned
                    think=False,
                )
                stripped = _THINK_TAG_RE.sub("", raw).strip()
                reasoning_pos = stripped.find('"a_reasoning"')
                act_pos = stripped.find('"act"')
                if reasoning_pos == -1 or act_pos == -1 or reasoning_pos < act_pos:
                    order_confirmed += 1
                else:
                    order_violated += 1
                    print(f"  cid={citizen.citizen_id} ORDER VIOLATION: 'act' appeared before 'a_reasoning'")
                decision = decode_reasoning_pressure_batch(raw, [citizen.citizen_id])[0]
                actual_act = decision.act in _ACTING_CODES
                agree = actual_act == expected_act
                correct += agree
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "act": decision.act, "agree": agree,
                    "reasoning": decision.a_reasoning,
                }
                print(f"  cid={citizen.citizen_id} expected={expected_act} act={decision.act} ({_ACT_NAMES[decision.act]}) {'AGREE' if agree else 'DISAGREE'}")
                print(f"    reasoning: {decision.a_reasoning!r}")
            except Exception as exc:  # noqa: BLE001 -- count failures, keep testing the rest
                failures += 1
                print(f"  cid={citizen.citizen_id} FAILED: {exc}")
                continue

    out_path = Path(__file__).with_name("check_vllm_pressure_action_reasoning_field_first_results.json")
    out_path.write_text(json.dumps(per_citizen, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nper-citizen results written to {out_path}")

    checked = len(cases) - failures
    rate = correct / checked if checked else float("nan")
    print("\n--- result ---")
    print(f"checked: {checked}/{len(cases)} ({failures} decode failures)")
    print(f"agreement with deterministic proxy (act-vs-no-act): {correct}/{checked} ({rate:.1%})  <- Ollama: 81.4% pooled")
    print(f"raw-response order check (a_reasoning before act): {order_confirmed} confirmed, {order_violated} violated")

    distinct_reasonings = {v["reasoning"] for v in per_citizen.values()}
    print(f"distinct reasoning strings across {len(per_citizen)} decoded cases: {len(distinct_reasonings)}")

    should_act_cases = [v for v in per_citizen.values() if v["expected_act"]]
    should_not_cases = [v for v in per_citizen.values() if not v["expected_act"]]
    should_act_rate = sum(v["agree"] for v in should_act_cases) / len(should_act_cases) if should_act_cases else float("nan")
    should_not_rate = sum(v["agree"] for v in should_not_cases) / len(should_not_cases) if should_not_cases else float("nan")
    print("\nclass breakdown (the informative subset is 'should act', not the pooled rate):")
    print(f"  should-act (ratio>1.5):     {sum(v['agree'] for v in should_act_cases)}/{len(should_act_cases)} ({should_act_rate:.1%})  <- Ollama: 4/17 (23.5%)")
    print(f"  should-not-act (ratio<0.5): {sum(v['agree'] for v in should_not_cases)}/{len(should_not_cases)} ({should_not_rate:.1%})  <- Ollama: 53/53 (100%)")

    print("\n--- verdict ---")
    if order_violated > 0:
        print(f"{order_violated} case(s) generated 'act' before 'a_reasoning' -- mechanism not fully exercised.")
    elif checked == 0:
        print("No usable results -- cannot conclude.")
    elif len(distinct_reasonings) <= max(1, len(per_citizen) // 10):
        print(f"Only {len(distinct_reasonings)} distinct reasoning string(s) -- content-blind on vLLM/AWQ too.")
    elif should_act_rate < _SUCCESS_THRESHOLD:
        print(
            f"FAILS on the informative subset: {should_act_rate:.1%} should-act agreement "
            f"(vs {should_not_rate:.1%} should-not-act, {rate:.1%} pooled) -- same base-rate-masked "
            "collapse-toward-inaction pattern as Ollama, not resolved by switching backends."
        )
    else:
        print(
            f"PASSES on the informative subset ({should_act_rate:.1%}) -- unlike Ollama, the "
            "collapse-toward-inaction does NOT reproduce under vLLM/AWQ on this mechanism."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
