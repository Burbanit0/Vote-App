"""
scripts/check_campaign_positioning_collapse_signature.py

One of the two genuinely untested decision types (per plan-decision-quality-validation.md's own
inventory, corrected: campaign_positioning replaces declare_candidacy's sincere-platform PIN -- a
constant "no shift", not a real per-nominee judgment function; no deterministic ground truth
exists). Tests plan-adversarial-framing-collapse.md's "act/response vs threshold" hypothesis on a
case explicitly predicted to be at-risk: campaign_positioning IS act/response-shaped (a nominee
choosing whether/how to shift their platform in response to rivals and the electorate), so the
hypothesis predicts it should show the same collapse signature as pressure_action/
representative_response/coalition_decision/reaction_to_event.

Collapse-signature method (no proxy possible): two structurally opposite poles.
  FAR pole: nominee's own issue_positions far from the electorate mean -- a real strategic
  incentive to shift toward the electorate exists.
  ALIGNED pole: nominee's own issue_positions already close to the electorate mean -- no
  strategic incentive to shift exists.
3 different nominees per pole. think=True (the real production call -- decide_campaign_
positioning always runs think=True, corrected from an original think=False guess during v4 Lot 8
live verification), _POSITIONING_THINK_TOKEN_ALLOWANCE (8000) matching production's own budget.

BATCHING NOTE, checked not presumed: decide_campaign_positioning deliberately does NOT use
chunk_voters -- batches "this tick's nominees (a handful, parties.initial_count in the shipped
config)" directly, same as coalition_decision. size=1 here is smaller than a typical production
batch (up to ~5 nominees together) -- an open gap, same caveat as coalition_decision/
reaction_to_event in plan-adversarial-framing-collapse.md.

Usage:
    python fast_api_voter/scripts/check_campaign_positioning_collapse_signature.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_positioning_batch  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation  # noqa: E402

_POPULATION_SIZE = 300
_THINK_TOKEN_ALLOWANCE = 8000
_N_PER_POLE = 3


def _electorate_mean(population: list[Citizen]) -> tuple[float, ...]:
    issue_count = len(population[0].issue_positions)
    sums = [0.0] * issue_count
    for c in population:
        for i, v in enumerate(c.issue_positions):
            sums[i] += v
    return tuple(s / len(population) for s in sums)


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    mean = _electorate_mean(population)

    ranked = sorted(population, key=lambda c: math.dist(c.issue_positions, mean))
    aligned = ranked[:_N_PER_POLE]
    far = ranked[-_N_PER_POLE:]

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, nominees in (("FAR from electorate mean", far), ("ALIGNED with electorate mean", aligned)):
            print(f"\n########## {pole_label} ##########")
            for nominee in nominees:
                dist = math.dist(nominee.issue_positions, mean)
                try:
                    raw = client.complete_json(
                        system_prompt=build_positioning_system_prompt([nominee], config),
                        user_prompt=build_positioning_user_prompt([nominee], parties_by_id, mean),
                        json_schema=POSITIONING_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE,
                        think=True,
                    )
                    decision = decode_positioning_batch(raw, [nominee.citizen_id])[0]
                    print(
                        f"  cid={nominee.citizen_id} dist_to_mean={dist:.4f} -> "
                        f"shifts={len(decision.shifts)} motif={decision.motif}"
                    )
                    results.append((pole_label, nominee.citizen_id, len(decision.shifts), decision.motif))
                except Exception as exc:  # noqa: BLE001 -- report per-nominee failures without aborting
                    print(f"  cid={nominee.citizen_id} dist_to_mean={dist:.4f} FAILED: {exc}")

    print("\n--- verdict ---")
    distinct_pairs = {(n_shifts, motif) for _pole, _cid, n_shifts, motif in results}
    if len(distinct_pairs) == 1:
        n_shifts, motif = next(iter(distinct_pairs))
        print(
            f"IDENTICAL (shifts={n_shifts}, motif={motif}) across ALL calls, both poles -> same "
            "content-blind collapse signature as the 4 confirmed act/response cases -- "
            "campaign_positioning extends the pattern, as the theory predicted."
        )
    else:
        far_vals = {(s, m) for pole, _c, s, m in results if pole.startswith("FAR")}
        aligned_vals = {(s, m) for pole, _c, s, m in results if pole.startswith("ALIGNED")}
        print(f"Response VARIES (far pole: {far_vals}, aligned pole: {aligned_vals}) -> no collapse signature found here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
