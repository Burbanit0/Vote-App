"""
scripts/check_chamber_deliberation_collapse_signature.py

Second and last genuinely untested decision type. No deterministic ground truth (checked, not
presumed): decide_chamber_deliberation's own docstring confirms there is no simple_rules.py
baseline -- "chamber_position is pinned to issue_positions at seating time and nothing else ever
touches it, so 'no delta' is already true by construction". Tests the "act/response vs threshold"
hypothesis on a case explicitly predicted to be at-risk: chamber_deliberation IS act/response-
shaped (a sortition member choosing whether to maintain or shift their stated position -- a
personal but still active choice with an outcome), so the theory predicts the same collapse
signature as the 4 already-confirmed cases.

Collapse-signature method: two poles built from the ONE lever this schema actually exposes.
  SAME pole: chamber_position == sincere_position (issue_positions) -- the system prompt ITSELF
  prescribes the correct answer for this exact state ("c'est l'etat normal... tranche motif=701,
  shifts vide, sans verification repetee ni hesitation") -- the closest thing to a real ground-
  truth check available for this decision type, not just a collapse signature.
  DRIFTED pole: chamber_position shifted 0.3 on one dimension from sincere_position (within
  sortition_chamber.max_deliberation_delta, a real, legal, already-occurred drift) -- no
  prescribed answer, checked for whether the response differs from the SAME pole at all.

3 different members per pole. think=True (real production call), _CHAMBER_THINK_TOKEN_ALLOWANCE
(8000) matching production's own budget.

BATCHING NOTE: decide_chamber_deliberation already runs at _CHAMBER_MAX_CHUNK_SIZE=1 in
production -- this test's size=1 IS the real production shape, not an artificial isolation
(same situation as representative_response, confirmed in plan-adversarial-framing-collapse.md).

Usage:
    python fast_api_voter/scripts/check_chamber_deliberation_collapse_signature.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_chamber_batch  # noqa: E402
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA  # noqa: E402

_POPULATION_SIZE = 190
_MEMBER_CIDS = [1, 2, 3]
_TICKS_LEFT = 15
_THINK_TOKEN_ALLOWANCE = 8000
_DRIFT_DIMENSION = 0
_DRIFT_DELTA = 0.3


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, drifted in (("SAME (chamber_position == sincere_position)", False), ("DRIFTED (0.3 shift on one dimension)", True)):
            print(f"\n########## {pole_label} ##########")
            for cid in _MEMBER_CIDS:
                member = by_id[cid]
                if drifted:
                    shifted = list(member.issue_positions)
                    shifted[_DRIFT_DIMENSION] = max(0.0, min(1.0, shifted[_DRIFT_DIMENSION] + _DRIFT_DELTA))
                    member.chamber_position = tuple(shifted)
                else:
                    member.chamber_position = member.issue_positions
                ctx = ChamberContext(cid=cid, ticks_left=_TICKS_LEFT)
                try:
                    raw = client.complete_json(
                        system_prompt=build_chamber_system_prompt([member], config),
                        user_prompt=build_chamber_user_prompt([member], {cid: ctx}),
                        json_schema=CHAMBER_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE,
                        think=True,
                    )
                    decision = decode_chamber_batch(raw, [cid])[0]
                    print(f"  cid={cid} -> shifts={len(decision.shifts)} motif={decision.motif}")
                    results.append((pole_label, cid, len(decision.shifts), decision.motif))
                except Exception as exc:  # noqa: BLE001 -- report per-member failures without aborting
                    print(f"  cid={cid} FAILED: {exc}")

    print("\n--- verdict ---")
    same_pole = [(s, m) for pole, _c, s, m in results if pole.startswith("SAME")]
    drifted_pole = [(s, m) for pole, _c, s, m in results if pole.startswith("DRIFTED")]
    same_correct = sum(1 for s, m in same_pole if s == 0 and m == 701)
    print(f"SAME pole: {same_correct}/{len(same_pole)} correctly resolved to shifts=[]/motif=701 (the prescribed answer)")
    distinct_pairs = {(s, m) for _pole, _c, s, m in results}
    if len(distinct_pairs) == 1:
        s, m = next(iter(distinct_pairs))
        print(
            f"IDENTICAL (shifts={s}, motif={m}) across ALL calls, both poles -> same content-blind "
            "collapse signature as the 4 confirmed act/response cases."
        )
    else:
        print(f"Response VARIES (same pole: {set(same_pole)}, drifted pole: {set(drifted_pole)}) -> no collapse signature found here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
