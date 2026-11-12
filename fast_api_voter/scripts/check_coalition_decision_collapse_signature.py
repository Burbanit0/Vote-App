"""
scripts/check_coalition_decision_collapse_signature.py

Follow-up requested before writing a new, separately-scoped document on the adversarial/target-
relative framing pattern found for pressure_action and representative_response (both collapse to
a fixed answer in isolation; candidacy_considered, purely self-referential, does not). Tests
coalition_decision -- a party's join/decline answer to another party's coalition proposal,
relational/strategic (not adversarial in the pressure_action/representative_response sense, but
still framed relative to a specific other actor, not self-referential).

GROUND TRUTH CHECKED FIRST, not presumed: plan-decision-quality-validation.md's own inventory
(§1) already found coalition_decision has only a PARTIAL deterministic equivalent -- form_coalition
decides which coalition forms overall via algorithm, not "would THIS specific party join THIS
specific proposed coalition" the way deterministic_pressure_action/decide_candidacy answer their
own decision directly. No clean per-response proxy exists to build an accuracy test against
(same situation as representative_response). Test used instead: the collapse SIGNATURE itself
(same detection method used throughout this investigation) -- does the response vary between two
structurally opposite, unambiguous situations, or collapse to one fixed answer regardless.

Two poles, 3 different responder party_ids each (party_id doesn't correspond to a real simulated
party -- constructed directly, same synthetic-but-realistic discipline as the representative_
response test, since this needs specific extreme numeric profiles, not a harvested real run):

  JOIN-OBVIOUS pole: platform IDENTICAL to the initiator (distance=0.0), joining pushes the
  coalition comfortably past the majority threshold (48+10=58 > 50), the initiator does not
  already have a majority alone -- every factor favors joining.
  DECLINE-OBVIOUS pole: platform maximally distant from the initiator (20-dimension issue space,
  0.1 vs 0.9 on every axis), the initiator ALREADY has a majority alone (60 > 50, this party's
  seats are not needed) -- every factor favors declining.

Same isolation discipline: size=1 (one responder per call), think=False (production path), real
production prompt/schema, unmodified.

Usage:
    python fast_api_voter/scripts/check_coalition_decision_collapse_signature.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typing import Any  # noqa: E402

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_coalition_system_prompt,
    build_coalition_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_coalition_batch  # noqa: E402
from api.domain.polity.llm_schemas import COALITION_JSON_SCHEMA  # noqa: E402

_INITIATOR = 1
_RESPONDER_IDS = [50, 51, 52]
_ACTION_NAMES = {1: "JOIN", 2: "DECLINE"}


def main() -> int:
    config = load_config()
    issue_count = config.citizens.issue_count

    poles: dict[str, dict[str, Any]] = {
        "JOIN-OBVIOUS (identical platform, pushes over majority, initiator needs it)": {
            "initiator_platform": (0.5,) * issue_count,
            "responder_platform": (0.5,) * issue_count,
            "initiator_seats": 48,
            "responder_seats": 10,
            "total_seats": 100,
            "majority_seats_threshold": 50.0,
        },
        "DECLINE-OBVIOUS (max distance, initiator already has majority alone)": {
            "initiator_platform": (0.1,) * issue_count,
            "responder_platform": (0.9,) * issue_count,
            "initiator_seats": 60,
            "responder_seats": 10,
            "total_seats": 100,
            "majority_seats_threshold": 50.0,
        },
    }

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, p in poles.items():
            print(f"\n########## {pole_label} ##########")
            for responder_id in _RESPONDER_IDS:
                platforms = {_INITIATOR: p["initiator_platform"], responder_id: p["responder_platform"]}
                seats = {_INITIATOR: p["initiator_seats"], responder_id: p["responder_seats"]}
                votes = {_INITIATOR: 0.45, responder_id: 0.10}
                try:
                    raw = client.complete_json(
                        system_prompt=build_coalition_system_prompt(
                            [responder_id], _INITIATOR, p["initiator_seats"], p["total_seats"],
                            p["majority_seats_threshold"],
                        ),
                        user_prompt=build_coalition_user_prompt(
                            [responder_id], _INITIATOR, platforms, seats, votes,
                            p["total_seats"], p["majority_seats_threshold"],
                        ),
                        json_schema=COALITION_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1),
                        think=False,
                    )
                    decision = decode_coalition_batch(raw, [responder_id])[0]
                    action_name = _ACTION_NAMES[decision.action]
                    print(f"  responder=party{responder_id} -> action={decision.action} ({action_name}) motif={decision.motif}")
                    results.append((pole_label, responder_id, decision.action, action_name))
                except Exception as exc:  # noqa: BLE001 -- report per-party failures without aborting
                    print(f"  responder=party{responder_id} FAILED: {exc}")

    print("\n--- verdict ---")
    distinct_actions = {action for _pole, _pid, action, _name in results}
    if len(distinct_actions) == 1:
        only = next(iter(distinct_actions))
        print(
            f"IDENTICAL action ({_ACTION_NAMES[only]}) across ALL calls, both poles -> same "
            "content-blind collapse signature as pressure_action/representative_response, "
            "extending to coalition_decision -- a third relational/target-relative decision type."
        )
    else:
        join_actions = {a for pole, _pid, a, _n in results if pole.startswith("JOIN")}
        decline_actions = {a for pole, _pid, a, _n in results if pole.startswith("DECLINE")}
        print(
            f"Action VARIES (join pole: {[_ACTION_NAMES[a] for a in join_actions]}, decline pole: "
            f"{[_ACTION_NAMES[a] for a in decline_actions]}) -> no collapse signature found here."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
