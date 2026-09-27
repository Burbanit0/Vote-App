"""
scripts/check_pressure_action_forced_reasoning.py

Exploratory follow-up to check_pressure_action_quality_pilot.py's Group A
pilot -- NOT a new pilot, a cheap (4 calls) targeted probe on the 4 citizens
whose decisions disagreed with the deterministic gap/blank_threshold proxy
in the pilot run.

CAVEAT, stated once here and repeated in the output: pressure_action runs
think=False in production (decide_pressure_actions's own docstring) -- no
chain-of-thought was ever generated for the original decisions being
investigated, and this project doesn't durably persist raw reasoning even
when it IS generated (see plan-llm-decision-audit-sampling.md's own
finding). This script therefore does NOT recover "the reasoning that
produced the original decision" -- that never existed in inspectable form.
It re-asks the SAME real context (same citizen, same target, same self_gap/
mandate_dev/ticks_to_election, real petition state confirmed via the
journal -- no petition_launched/signed/expired event exists anywhere in
this run through tick 16) with think=True forced, a genuinely different
call configuration never used for this decision type in production.

Two honest readings, neither privileged over the other before running:
- Forced reasoning reproduces the original act -> weak circumstantial
  support that the reasoning is representative, NOT proof the original
  (untraced) mechanism followed the same logic. A model that arrives at
  the same conclusion via a different path when asked to deliberate stays
  a real possibility.
- Forced reasoning diverges from the original act -> a distinct, real
  finding in its own right (think=False/think=True disagree for these
  citizens), not evidence the original decision was wrong.

Real context per citizen, extracted from the pilot's own journal
(scripts/pressure_action_quality_pilot/pressure-action-quality-pilot/events.jsonl):
  cid=0,  tick=0, target=44, self_gap=0.3283, mandate_dev=0.0084, ticks_to_election=16, original act=0 (NOTHING)
  cid=5,  tick=0, target=44, self_gap=0.3280, mandate_dev=0.0084, ticks_to_election=16, original act=0 (NOTHING)
  cid=29, tick=2, target=44, self_gap=0.1448, mandate_dev=0.0353, ticks_to_election=14, original act=3 (MOBILIZE)
  cid=69, tick=2, target=44, self_gap=0.2951, mandate_dev=0.0353, ticks_to_election=14, original act=3 (MOBILIZE)

available=(0,1,2,3,4): pressure_menu.petition_enabled=True AND
mobilization_enabled=True in the pilot config, and menu_acts() is a pure
function of config, not live state. petition_open=already_signed=False,
petition_expires_at_tick=None: confirmed via the journal, not assumed --
zero petition_launched/signed/expired events exist anywhere in the run
through tick 16. neighbors_acting=None: social_graph disabled in the
pilot config (unchanged from load_config()'s own default).

Usage:
    python fast_api_voter/scripts/check_pressure_action_forced_reasoning.py
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

# Generous budget for an untested think=True configuration on this schema --
# not calibrated (this decision type has never run think=True in
# production), deliberately over- rather than under-provisioned so a
# truncation doesn't get misread as "no coherent reasoning".
_FORCED_THINK_TOKEN_ALLOWANCE = 8000

_CASES: list[dict[str, int | float]] = [
    {"cid": 0, "target": 44, "self_gap": 0.3283, "mandate_dev": 0.0084, "ticks_to_election": 16, "original_act": 0},
    {"cid": 5, "target": 44, "self_gap": 0.3280, "mandate_dev": 0.0084, "ticks_to_election": 16, "original_act": 0},
    {"cid": 29, "target": 44, "self_gap": 0.1448, "mandate_dev": 0.0353, "ticks_to_election": 14, "original_act": 3},
    {"cid": 69, "target": 44, "self_gap": 0.2951, "mandate_dev": 0.0353, "ticks_to_election": 14, "original_act": 3},
]

_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}


def main() -> int:
    config = load_config()
    citizens_by_id = {
        c.citizen_id: c
        for c in generate_population(config.citizens, config.run.population_size, config.run.seed)
    }

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for case in _CASES:
            cid = int(case["cid"])
            target = int(case["target"])
            ticks_to_election = int(case["ticks_to_election"])
            original_act = int(case["original_act"])
            citizen = citizens_by_id[cid]
            ctx = PressureContext(
                cid=cid,
                target=target,
                self_gap=float(case["self_gap"]),
                mandate_dev=float(case["mandate_dev"]),
                ticks_to_election=ticks_to_election,
                available=(0, 1, 2, 3, 4),
                petition_open=False,
                petition_expires_at_tick=None,
                already_signed=False,
                neighbors_acting=None,
            )
            system_prompt = build_pressure_system_prompt([citizen], config)
            user_prompt = build_pressure_user_prompt([citizen], {cid: ctx})
            raw = client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1) + _FORCED_THINK_TOKEN_ALLOWANCE,
                think=True,
            )
            decisions = decode_pressure_batch(raw, expected_cids=[cid])
            decision = decisions[0]
            original_name = _ACT_NAMES[original_act]
            forced_name = _ACT_NAMES[decision.act]
            match = "SAME" if decision.act == original_act else "DIFFERENT"
            print(f"\n=== cid={cid} (original: think=False -> {original_name}) ===")
            print(f"think=True forced -> act={forced_name} motif={decision.motif} [{match} as original]")
            print(f"raw response:\n{raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
