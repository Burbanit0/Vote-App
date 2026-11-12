"""
scripts/check_reaction_to_event_collapse_signature.py

Fourth and last decision-type check requested before writing a new, separately-scoped document on
the adversarial/target-relative framing pattern found so far for pressure_action,
representative_response, and coalition_decision (all three collapse to a fixed answer in
isolation; candidacy_considered, purely self-referential, does not).

Tests reaction_to_event under EventType.SCANDAL specifically -- unlike ECONOMIC_SHOCK (target
always null, a systemic/impersonal event), SCANDAL carries a real `target` (the sitting president
it implicates, codebook.py's own EventType docstring), making it the one reaction_to_event branch
that is at least partially framed around a specific other actor rather than a purely impersonal
event -- the closest point of comparison to the other three cases within this decision type.

GROUND TRUTH CHECKED FIRST, not presumed: plan-decision-quality-validation.md's own inventory
(§1), itself corrected from the 2026-08-24 source document's unverified assumption, already
established deterministic_reaction_to_event takes no Citizen parameter at all -- "no per-citizen
judgment by construction" -- so it cannot ground a per-citizen accuracy check for ANY event_type,
SCANDAL included. Collapse-signature method used instead, same as representative_response/
coalition_decision: two structurally opposite ctx.event_salience poles (the only per-citizen
variable this schema exposes), 3 different citizens each.

  LOW-SALIENCE pole: event_salience=0.0 (citizen previously untouched by any past event).
  HIGH-SALIENCE pole: event_salience=0.9 (citizen already heavily sensitized/attentive).

If salience_delta/motif varies meaningfully between poles -> real content-sensitivity. If
identical regardless -> the same collapse signature extends to a fourth decision type.

Same isolation discipline: size=1, think=False (production path), real production prompt/schema,
unmodified.

Usage:
    python fast_api_voter/scripts/check_reaction_to_event_collapse_signature.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.codebook import EventType  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ReactionContext,
    build_reaction_system_prompt,
    build_reaction_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_reaction_batch  # noqa: E402
from api.domain.polity.llm_schemas import REACTION_JSON_SCHEMA  # noqa: E402

_POPULATION_SIZE = 190
_REACTOR_CIDS = [10, 20, 30]
_SCANDAL_TARGET = 5

_POLES = {
    "LOW-SALIENCE (event_salience=0.0)": 0.0,
    "HIGH-SALIENCE (event_salience=0.9)": 0.9,
}


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, salience in _POLES.items():
            print(f"\n########## {pole_label} ##########")
            for cid in _REACTOR_CIDS:
                citizen = by_id[cid]
                ctx = ReactionContext(cid=cid, event_salience=salience)
                try:
                    raw = client.complete_json(
                        system_prompt=build_reaction_system_prompt([citizen], EventType.SCANDAL, config),
                        user_prompt=build_reaction_user_prompt(
                            [citizen], {cid: ctx}, event_type=EventType.SCANDAL,
                            target=_SCANDAL_TARGET, magnitude=0.0,
                        ),
                        json_schema=REACTION_JSON_SCHEMA,
                        max_tokens=compute_max_tokens(1),
                        think=False,
                    )
                    decision = decode_reaction_batch(raw, [cid])[0]
                    print(f"  cid={cid} -> salience_delta={decision.salience_delta:.4f} motif={decision.motif}")
                    results.append((pole_label, cid, decision.salience_delta, decision.motif))
                except Exception as exc:  # noqa: BLE001 -- report per-citizen failures without aborting
                    print(f"  cid={cid} FAILED: {exc}")

    print("\n--- verdict ---")
    distinct_pairs = {(delta, motif) for _pole, _cid, delta, motif in results}
    if len(distinct_pairs) == 1:
        delta, motif = next(iter(distinct_pairs))
        print(
            f"IDENTICAL (salience_delta={delta:.4f}, motif={motif}) across ALL calls, both poles "
            "-> same content-blind collapse signature extends to reaction_to_event (SCANDAL), a "
            "fourth relational/target-carrying decision type."
        )
    else:
        low_vals = {(d, m) for pole, _cid, d, m in results if pole.startswith("LOW")}
        high_vals = {(d, m) for pole, _cid, d, m in results if pole.startswith("HIGH")}
        print(f"Response VARIES (low pole: {low_vals}, high pole: {high_vals}) -> no collapse signature found here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
