"""
scripts/check_candidacy_considered_isolation_disposition.py

Reframed follow-up to plan-pressure-action-remediation.md §3bis. §3.1 and §3.2 both collapsed to
will_act=True for ALL 70 unambiguous citizens tested (not a content-correlated hard subset -- a
mathematical inevitability of two constant functions, verified by cross-referencing per-citizen
results between the two tests). That reframes the open question: is the collapse toward an
affirmative/engaged answer specific to pressure_action's own framing, or a general property of
this model on any isolated (size=1), single-decision binary judgment where one answer resembles
"engage/act"?

Tests candidacy_considered -- a DIFFERENT decision type, with its OWN pre-existing deterministic
ground truth (decide_candidacy, simple_rules.py: citizen.ambition_score >= config.candidacy.
ambition_threshold, shipped 0.30) -- on citizens whose ambition_score is FAR below the threshold
(not marginally below), same isolation discipline (size=1, think=False, REAL production prompt/
schema, untouched).

Pre-registered readings, written before any call:
- If the model says "declare" (outcome=1) even for these extreme low-ambition citizens -> a
  general isolation-disposition toward affirmative/engaged answers, independent of decision type.
  Would redirect the whole investigation beyond pressure_action.
- If candidacy_considered stays correct (outcome=0, "decline") on these cases -> the collapse is
  pressure_action-specific, not a general model disposition -- reopens the question of what in
  THAT decision type's own framing (the citizen-vs-authority frame, the word "pression") triggers
  it.

Usage:
    python fast_api_voter/scripts/check_candidacy_considered_isolation_disposition.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_candidacy_batch  # noqa: E402
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import sympathizer_ratio  # noqa: E402

_POPULATION_SIZE = 190
# The 5 lowest ambition_score citizens in this population (0.0069-0.0214), far below the shipped
# 0.30 threshold -- 14x to 43x below, not marginal.
_TARGET_CIDS = [8, 178, 42, 41, 77]


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}
    support = {cid: sympathizer_ratio(by_id[cid], population) for cid in _TARGET_CIDS}

    declared = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in _TARGET_CIDS:
            citizen = by_id[cid]
            raw = client.complete_json(
                system_prompt=build_candidacy_system_prompt([citizen]),
                user_prompt=build_candidacy_user_prompt([citizen], support),
                json_schema=CANDIDACY_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
            )
            decision = decode_candidacy_batch(raw, [cid])[0]
            expected = 0  # ambition_score << threshold -> decide_candidacy would say decline
            agree = decision.outcome == expected
            if decision.outcome == 1:
                declared.append(cid)
            print(
                f"cid={cid} ambition_score={citizen.ambition_score:.4f} "
                f"(threshold={config.candidacy.ambition_threshold}) perceived_support={support[cid]:.4f} "
                f"-> outcome={decision.outcome} ({'declare' if decision.outcome == 1 else 'decline'}) "
                f"motif={decision.motif} [{'AGREE' if agree else 'DISAGREE'}]"
            )

    print("\n--- verdict, per the pre-registered readings ---")
    if declared:
        print(
            f"{len(declared)}/{len(_TARGET_CIDS)} extreme-low-ambition citizens still 'declared' "
            f"({declared}) -> supports a GENERAL isolation-disposition toward affirmative/engaged "
            "answers, independent of decision type. This would extend well beyond pressure_action."
        )
    else:
        print(
            "0 declared -- candidacy_considered stays correct on these extreme cases -> the "
            "collapse is pressure_action-SPECIFIC, not a general model disposition. Reopens what "
            "in that decision type's own framing triggers it."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
