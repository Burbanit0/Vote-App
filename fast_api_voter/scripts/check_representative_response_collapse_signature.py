"""
scripts/check_representative_response_collapse_signature.py

Follow-up to plan-pressure-action-remediation.md §3bis's reframed question: does the collapse
found for pressure_action generalize to representative_response, the OTHER decision type framed
around a citizen-vs-authority / adversarial-target relationship (stance toward citizen pressure)?

GROUND-TRUTH CHECK, DONE FIRST, PER DIRECT INSTRUCTION -- do not presume it exists just because
candidacy_considered had one. Verified directly against the code:
`decide_representative_response`'s own docstring states the "deterministic fallback" this
decision type replaced is simply "no delta, stance=silence" -- a CONSTANT, not a function of the
officeholder's actual situation (run_polity_simulation._run_representative_responses's own
docstring, cited there). There is no simple_rules.py baseline that varies with legitimacy/
mandate_dev/street the way deterministic_pressure_action or decide_candidacy do. Comparing the
LLM against a constant "always silence" baseline would not be a meaningful accuracy check --
every non-silence answer would trivially "disagree" without that being informative.

What CAN be tested cleanly without a proxy: the collapse SIGNATURE itself -- the same detection
method that first characterized pressure_action's own collapse (same output regardless of
wildly different, unambiguous inputs), not an accuracy rate. Two structurally opposite ctx
extremes, each tested on 3 different citizens playing the officeholder role (via declare_candidacy
for a deterministic, unshifted pledged_platform/revealed_position -- same construction as the
pressure_action redesign tests):

  CRISIS pole: L=0.05 (legitimacy nearly exhausted), mandate_dev=0.8 (badly off-pledge),
  street=3.0 (sustained heavy mobilization), ticks_left=2 (election imminent) -- a situation where
  *some* real response (concession, defiance, or counter-mobilization) is plausible, silence is
  not an obviously safe default.
  NO-PROBLEM pole: L=0.95 (near-perfect legitimacy), mandate_dev=0.0 (perfectly on pledge),
  street=0.0 (no mobilization), ticks_left=20 (no urgency) -- a situation where silence is the
  obviously unremarkable answer, any active response would be a real surprise.

If stance varies meaningfully between poles (not necessarily "correct" against any external
standard, since none exists) -> real content-sensitivity, no collapse signature found here.
If stance is IDENTICAL across all 6 calls regardless of pole -> the same collapse signature
already characterized for pressure_action, extending beyond it.

Same isolation discipline throughout: size=1 (one holder per call), think=False (production
path), real production prompt/schema, config.mandate bounds respected in the prompt as shipped.

Usage:
    python fast_api_voter/scripts/check_representative_response_collapse_signature.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ResponseContext,
    build_response_system_prompt,
    build_response_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_response_batch  # noqa: E402
from api.domain.polity.llm_schemas import RESPONSE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_POPULATION_SIZE = 190
_HOLDER_CIDS = [1, 2, 3]  # 3 different citizens playing the officeholder role, one per pole test
_STANCE_NAMES = {1: "CONCESSION", 2: "DEFIANCE", 3: "SILENCE", 4: "COUNTER_MOBILIZATION"}

_POLES = {
    "CRISIS (L=0.05, mandate_dev=0.8, street=3.0, ticks_left=2)": ResponseContext(
        cid=-1, legitimacy=0.05, mandate_dev=0.8, street=3.0, lame_duck=False, ticks_left=2
    ),
    "NO-PROBLEM (L=0.95, mandate_dev=0.0, street=0.0, ticks_left=20)": ResponseContext(
        cid=-1, legitimacy=0.95, mandate_dev=0.0, street=0.0, lame_duck=False, ticks_left=20
    ),
}


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, template_ctx in _POLES.items():
            print(f"\n########## {pole_label} ##########")
            for cid in _HOLDER_CIDS:
                holder = by_id[cid]
                declare_candidacy(holder)  # deterministic pledged_platform=revealed_position, no LLM shift
                ctx = ResponseContext(
                    cid=cid, legitimacy=template_ctx.legitimacy, mandate_dev=template_ctx.mandate_dev,
                    street=template_ctx.street, lame_duck=template_ctx.lame_duck, ticks_left=template_ctx.ticks_left,
                )
                try:
                    raw = client.complete_json(
                        system_prompt=build_response_system_prompt([holder], config),
                        user_prompt=build_response_user_prompt([holder], {cid: ctx}),
                        json_schema=RESPONSE_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1),
                        think=False,
                    )
                    decision = decode_response_batch(raw, [cid])[0]
                    stance_name = _STANCE_NAMES[decision.stance]
                    print(f"  holder=cid{cid} -> stance={decision.stance} ({stance_name}) shifts={len(decision.shifts)} motif={decision.motif}")
                    results.append((pole_label, cid, decision.stance, stance_name))
                except Exception as exc:  # noqa: BLE001 -- report per-holder failures without aborting the whole comparison
                    print(f"  holder=cid{cid} FAILED: {exc}")

    print("\n--- verdict ---")
    distinct_stances = {stance for _pole, _cid, stance, _name in results}
    if len(distinct_stances) == 1:
        only = next(iter(distinct_stances))
        print(
            f"IDENTICAL stance ({_STANCE_NAMES[only]}) across ALL 6 calls, both poles, all 3 "
            "holders -> the same content-blind collapse signature already characterized for "
            "pressure_action, extending to representative_response. This would be a finding "
            "beyond the scope of this remediation document -- a design principle to audit "
            "wherever this adversarial/target-relative framing appears, not a pressure_action-"
            "only issue."
        )
    else:
        crisis_stances = {stance for pole, _cid, stance, _name in results if pole.startswith("CRISIS")}
        noproblem_stances = {stance for pole, _cid, stance, _name in results if pole.startswith("NO-PROBLEM")}
        print(
            f"Stance VARIES across calls (crisis pole: {[_STANCE_NAMES[s] for s in crisis_stances]}, "
            f"no-problem pole: {[_STANCE_NAMES[s] for s in noproblem_stances]}) -> no collapse "
            "signature found here. Tightens the hypothesis to something specific to "
            "pressure_action beyond the general adversarial framing -- §3.3 (few-shot) becomes "
            "the reasonable next candidate again, with this new information in hand."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
