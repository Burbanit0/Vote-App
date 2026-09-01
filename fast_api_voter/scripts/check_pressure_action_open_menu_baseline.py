"""
scripts/check_pressure_action_open_menu_baseline.py

THE decisive re-measurement after the 2026-08-31 discovery that most of this investigation's
pressure_action results measured an impossibility.

What was wrong: the shipped config is `electoral_only: true, petition_enabled: false,
mobilization_enabled: false` -- the design's own "GROUPE DE CONTRÔLE principal". Under it,
menu_acts() returns (0, 4) and build_pressure_system_prompt states "CONTRAINTE ABSOLUE : le champ
act doit valoir UN DES CODES SUIVANTS, et aucun autre : [0, 4]". Acts 1/2/3 (SIGN_PETITION,
LAUNCH_PETITION, MOBILIZE) are forbidden by construction. Yet pressure_action_harness's ground
truth labels a high-gap citizen `expected_act=True` where "act" means `act in {1,2,3}` -- an
expectation the active configuration makes unsatisfiable. Every "0/17 on the should-act pole",
"0/70 acting codes ever emitted", and the identical 17/70 failures of the §3.1/§3.2 redesigns were
measuring that constraint, not the model. (The ORIGINAL quality pilot,
check_pressure_action_quality_pilot.py, does NOT have this defect: it explicitly opens the menu
via dataclasses.replace, so its 41.7% disagreement finding stands.)

What this script does: the exact §2.3-era baseline protocol -- production prompt, size=1,
think=False, temperature 0.0, the same 70 harvested citizens -- with the ONE difference that the
menu is opened (electoral_only=False, petition_enabled=True, mobilization_enabled=True), so acts
1/2/3 are legal and the harness's own ground truth becomes satisfiable. This is the measurement
that decides whether pressure_action has a real collapse at all.

Reported both ways, deliberately: agreement on the informative "should act" pole (the number every
prior run reported as 0/17), and the full distribution of emitted acts (which says whether the
model uses the newly-legal levers at all).

Usage:
    python fast_api_voter/scripts/check_pressure_action_open_menu_baseline.py
"""
from __future__ import annotations

import dataclasses
import json
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
from api.domain.polity.llm_client import OllamaJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from pressure_action_harness import (  # noqa: E402
    ACT_NAMES,
    ACTING_CODES,
    MANDATE_DEV,
    TICKS_TO_ELECTION,
    harvest_unambiguous_citizens,
    raw_pressure_call,
)


def main() -> int:
    shipped = load_config()
    config = dataclasses.replace(
        shipped,
        pressure_menu=dataclasses.replace(
            shipped.pressure_menu,
            electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
    )
    legal = menu_acts(config.pressure_menu)
    print(f"menu livre  : {menu_acts(shipped.pressure_menu)}  <- ce que 18 scripts ont teste")
    print(f"menu ouvert : {legal}  <- ce que ce script teste\n")
    if set(ACTING_CODES) - set(legal):
        print("ABORT: acting codes still not legal under the opened menu -- check the config shape.")
        return 1

    holder, cases = harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (holder=cid{holder.citizen_id})\n")

    acts_seen: Counter[int] = Counter()
    outcomes: list[tuple[int, bool, bool | None]] = []

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
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

            raw = raw_pressure_call(
                client, system_prompt, user_prompt, PRESSURE_JSON_SCHEMA, compute_max_tokens(1)
            )
            act = None
            if raw.content:
                try:
                    act = json.loads(raw.content)["decisions"][0]["act"]
                except Exception:  # noqa: BLE001 -- a malformed answer is a result to record
                    pass
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
        print(f"pole informatif « devrait agir » : {should_act_ok}/{len(should_act)} ({should_act_ok / len(should_act):.1%})  <- 0/17 sous menu ferme")
    if checked:
        print(f"accord global (deux poles) : {total_ok}/{len(checked)} ({total_ok / len(checked):.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
