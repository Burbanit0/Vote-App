"""
scripts/check_vllm_pressure_action_open_menu_baseline.py

vLLM/AWQ replay of check_pressure_action_open_menu_baseline.py -- THE decisive open-menu
measurement for pressure_action's real decision-quality problem (project_polity_pressure_action_
collapse_investigation.md: not a rigid collapse, a quality gap -- 60.0% overall / should-act pole
at 9/17 (52.9%) on Ollama's un-quantized qwen3:8b). Same 70 harvested citizens, same open-menu
override (electoral_only=False, petition_enabled=True, mobilization_enabled=True), same
production schema/prompt shape, think=False -- only the client changes, Ollama to vLLM.

Unlike the Ollama version, this does NOT need raw_pressure_call's native-endpoint bypass:
VllmJsonClient has no equivalent to Ollama's think=False + response_format silent-reasoning-burn
bug (see VllmJsonClient's own docstring) -- complete_json(think=False) already gives production's
real call shape directly.

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_pressure_action_open_menu_baseline.py
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from pressure_action_harness import (  # noqa: E402
    ACT_NAMES,
    ACTING_CODES,
    MANDATE_DEV,
    TICKS_TO_ELECTION,
    harvest_unambiguous_citizens,
)


def main() -> int:
    shipped = load_config()
    vllm_url = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")
    config = dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url=vllm_url),
        pressure_menu=dataclasses.replace(
            shipped.pressure_menu,
            electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
    )
    legal = menu_acts(config.pressure_menu)
    print(f"menu ouvert : {legal}\n")
    if set(ACTING_CODES) - set(legal):
        print("ABORT: acting codes still not legal under the opened menu -- check the config shape.")
        return 1

    holder, cases = harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (holder=cid{holder.citizen_id})\n")

    acts_seen: Counter[int] = Counter()
    outcomes: list[tuple[int, bool, bool | None]] = []

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for citizen, gap, expected_act in cases:
            cid = citizen.citizen_id
            ctx = PressureContext(
                cid=cid, target=holder.citizen_id, self_gap=gap, mandate_dev=MANDATE_DEV,
                ticks_to_election=TICKS_TO_ELECTION, available=legal,
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            citizen_stub = type("C", (), {"citizen_id": cid})()
            system_prompt = build_pressure_system_prompt([citizen_stub], config)
            user_prompt = build_pressure_user_prompt([citizen_stub], {cid: ctx})

            act = None
            try:
                raw = client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=PRESSURE_JSON_SCHEMA,
                    max_tokens=compute_max_tokens(1),
                    think=False,
                )
                act = json.loads(raw)["decisions"][0]["act"]
            except Exception as exc:  # noqa: BLE001 -- a malformed/failed answer is a result to record
                print(f"  cid={cid} CALL FAILED: {exc}")
            agree = None
            if act is not None:
                acts_seen[act] += 1
                agree = (act in ACTING_CODES) == expected_act
            outcomes.append((cid, expected_act, agree))
            print(f"  cid={cid} expected_act={expected_act} -> act={act} ({ACT_NAMES.get(act, '?') if act is not None else '?'}) [{'AGREE' if agree else 'DISAGREE'}]")

    should_act = [o for o in outcomes if o[1] and o[2] is not None]
    should_act_ok = sum(1 for o in should_act if o[2])
    checked = [o for o in outcomes if o[2] is not None]
    total_ok = sum(1 for o in checked if o[2])

    print("\n--- result ---")
    print(f"distribution des actes emis : { {ACT_NAMES.get(a, a): n for a, n in sorted(acts_seen.items())} }")
    print(f"codes d'action (1/2/3) emis : {sum(n for a, n in acts_seen.items() if a in ACTING_CODES)}/{len(checked)}")
    if should_act:
        print(f"pole informatif « devrait agir » : {should_act_ok}/{len(should_act)} ({should_act_ok / len(should_act):.1%})  <- Ollama: 9/17 (52.9%)")
    if checked:
        print(f"accord global (deux poles) : {total_ok}/{len(checked)} ({total_ok / len(checked):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
