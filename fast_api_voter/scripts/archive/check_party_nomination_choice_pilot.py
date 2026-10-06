"""
scripts/check_party_nomination_choice_pilot.py

Two purposes at once: (1) the Group A pilot for party_nomination_choice that
plan-decision-quality-validation.md scoped alongside pressure_action but never ran (only
pressure_action was chosen as the initial pilot case) -- a real ground truth exists
(select_party_nominee, simple_rules.py: max ambition_score among eligible members, tie-break
lowest cid); (2) the decisive test for plan-adversarial-framing-collapse.md's "act/response vs
threshold" hypothesis, raised after "named other actor present" failed to explain
representative_response's own collapse.

party_nomination_choice is a genuinely different shape from all 5 decision types tested so far:
a comparative judgment (unlike candidacy_considered's pure self-threshold) among a party's OWN
members (unlike coalition_decision's two-party negotiation) -- no external actor with a stake,
and not framed as an act/response to anything outside the party itself ("choisis lequel", not
"decide s'il agit/repond/rejoint").

Pre-registered readings, written before any call:
- If party_nomination_choice does NOT collapse (tracks ambition_score correctly) -> confirms
  "act/response vs threshold" as the real factor, independent of whether a named external actor
  is present. Sharper, more useful theory for remediation: the risk isn't "avoid referencing
  another actor", it's "any decision framed as an act or response (not a self-evaluation) needs
  checking before production."
- If it collapses too -> "act/response vs threshold" is eliminated as a SUFFICIENT explanation
  (comparative judgment among peers is itself enough to trigger it) -- real progress, not a null
  result: narrows the search for a third axis.

Real production prompt/schema (build_party_nomination_system_prompt/build_party_nomination_user_
prompt, decode_party_nomination_batch), think=False, one contested party per call (matches
production exactly -- decide_party_nominations deliberately never chunks, "a handful of parties
at most"). Contested slates constructed from a REAL population + REAL k-means party formation
(initialize_parties/assign_party_affiliation, both deterministic, no LLM) -- not synthesized --
selecting parties where one member's ambition_score dominates the rest by a wide, unambiguous
margin.

Usage:
    python fast_api_voter/scripts/check_party_nomination_choice_pilot.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    compute_max_tokens,
    resolve_party_nomination_cid,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_party_nomination_batch  # noqa: E402
from api.domain.polity.llm_schemas import PARTY_NOMINATION_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import Party, initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation, decide_candidacy, sympathizer_ratio  # noqa: E402

_POPULATION_SIZE = 500
_MIN_MARGIN = 0.10  # top ambition_score must exceed the WORST member of its own slate by this much
_MAX_CASES = 5
_SLATE_LOW_MEMBERS = 3  # slate = the top eligible member + this many of the LOWEST eligible members


def _find_contested_cases(
    population: list[Citizen], parties: list[Party], config: object
) -> list[tuple[int, list[Citizen], int]]:
    """Real, deterministic construction: for each party, eligible members (decide_candidacy)
    sorted by ambition_score. ambition_dist (beta(2,8), ADR-002) compresses scores tightly just
    above the 0.30 threshold, so top-vs-runner-up margins are small (measured: 0.008-0.083) --
    top-vs-LOWEST-eligible gives a real, wide, unambiguous margin instead (measured: 0.16-0.35).
    Slate = the single top member (the expected winner) plus the _SLATE_LOW_MEMBERS lowest
    eligible members (still legitimately eligible, just clearly less ambitious) -- every member
    of the slate is a real, qualifying candidate, not a synthetic filler."""
    by_party: dict[int, list[Citizen]] = {}
    for c in population:
        assert c.party_affiliation is not None
        by_party.setdefault(c.party_affiliation, []).append(c)

    cases = []
    for party_id, members in by_party.items():
        eligible = sorted(
            (c for c in members if decide_candidacy(c, config.candidacy)),  # type: ignore[attr-defined]
            key=lambda c: c.ambition_score,
            reverse=True,
        )
        if len(eligible) < _SLATE_LOW_MEMBERS + 1:
            continue
        top = eligible[0]
        lows = eligible[-_SLATE_LOW_MEMBERS:]
        margin = top.ambition_score - lows[-1].ambition_score
        if margin < _MIN_MARGIN:
            continue
        slate = [top] + lows
        cases.append((party_id, slate, top.citizen_id))
        if len(cases) >= _MAX_CASES:
            break
    return cases


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}

    cases = _find_contested_cases(population, parties, config)
    print(f"found {len(cases)} unambiguous contested-party cases (margin >= {_MIN_MARGIN})")
    if not cases:
        print("No usable cases found -- cannot conclude. Try a larger population.")
        return 1

    support_pool = population
    correct = 0
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for party_id, slate, expected_winner_cid in cases:
            support = {c.citizen_id: sympathizer_ratio(c, support_pool) for c in slate}
            contested = {party_id: slate}
            raw = client.complete_json(
                system_prompt=build_party_nomination_system_prompt(contested),
                user_prompt=build_party_nomination_user_prompt(contested, parties_by_id, support),
                json_schema=PARTY_NOMINATION_JSON_SCHEMA,
                max_tokens=compute_max_tokens(len(slate)),
                think=False,
            )
            decisions = decode_party_nomination_batch(raw, [party_id])
            decision = decisions[0]
            winner_cid = resolve_party_nomination_cid(decision, slate)
            agree = winner_cid == expected_winner_cid
            correct += agree
            ambitions = {c.citizen_id: round(c.ambition_score, 4) for c in slate}
            print(
                f"party={party_id} slate={[c.citizen_id for c in slate]} ambitions={ambitions} "
                f"expected_winner={expected_winner_cid} -> chosen_winner={winner_cid} "
                f"motif={decision.motif} [{'AGREE' if agree else 'DISAGREE'}]"
            )

    rate = correct / len(cases)
    print(f"\n--- result ---\naccuracy: {correct}/{len(cases)} ({rate:.1%})")

    print("\n--- verdict, per the pre-registered readings ---")
    if rate >= 0.8:
        print(
            "party_nomination_choice tracks ambition_score correctly on these unambiguous cases "
            "-> does NOT collapse -> confirms 'act/response vs threshold' as the real factor, "
            "independent of whether a named external actor is present."
        )
    else:
        print(
            "party_nomination_choice fails on these unambiguous cases too -> collapses despite "
            "being neither adversarial nor act/response-shaped -> 'act/response vs threshold' is "
            "eliminated as a SUFFICIENT explanation. Real progress: narrows the search for a "
            "third axis, rather than a null result."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
