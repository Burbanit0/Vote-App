"""ADR-024: the wasted vote at legislative elections. The sincere vote is the poll; a voter it strands
below the electoral threshold may desert to the best party above it, at most `vote.strategic_margin` worse."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api.domain.polity.citizen import Citizen
from api.domain.polity.config import load_config
from api.domain.polity.journal import Journal
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import _hold_legislative_election
from api.domain.polity.reseat import reseat
from api.domain.polity.run_digest import effective_parties
from api.domain.polity.simple_rules import (
    GoverningRecord,
    PolicyRecord,
    choose_party,
    strategic_party,
    viable_parties,
    weighted_distance,
)

A, B = Party(0, (0.5,)), Party(1, (0.2,))


def _voter(cid: int, position: float, tolerance: float = 0.5) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=(position,), issue_priorities=(1.0,), blank_threshold=tolerance,
                   ambition_score=0.5)


def test_the_poll_measures_the_threshold_as_seat_allocation_does() -> None:
    assert viable_parties([0, 0, 0, 1, None, None], 0.25) == {0, 1}  # 1 of 4 party votes: blanks left out
    assert viable_parties([0, 0, 0, 1], 0.3) == {0}
    assert viable_parties([None], 0.05) == frozenset()


def test_a_stranded_voter_deserts_only_within_the_margin_and_their_tolerance() -> None:
    near = _voter(1, 0.3)  # B at 0.1, A at 0.2: deserting costs 0.1
    assert strategic_party(near, [A, B], 1, frozenset({0}), 0.15) == 0
    assert strategic_party(near, [A, B], 1, frozenset({0}), 0.05) == 1  # costs more than the margin
    assert strategic_party(_voter(2, 0.3, tolerance=0.15), [A, B], 1, frozenset({0}), 0.15) == 1  # A is past tolerance
    assert strategic_party(near, [A, B], 1, frozenset({0, 1}), 0.15) == 1  # B clears the threshold: no reason to move
    assert strategic_party(near, [A, B], 1, frozenset({0}), 0.0) == 1  # margin 0: the sincere vote
    assert strategic_party(near, [A, B], None, frozenset({0}), 0.15) is None  # a blank ballot stays blank
    assert strategic_party(near, [A, B], 1, frozenset(), 0.15) == 1  # nothing clears the threshold


def _legislative(tmp_path: Path, citizens: list[Citizen], margin: float) -> dict:
    config = load_config()
    config = dataclasses.replace(
        config, vote=dataclasses.replace(config.vote, strategic_margin=margin),
        institutions=dataclasses.replace(config.institutions, electoral_threshold=0.25),
    )
    path = tmp_path / f"events-{margin}.jsonl"
    with Journal(path, "run") as journal:
        _hold_legislative_election(citizens, [A, B], config, journal, 8)
    return json.loads(path.read_text().splitlines()[0])["payload"]


@pytest.mark.behavior("ELE-11")
def test_the_legislative_election_counts_the_deserters_and_journals_them(tmp_path: Path) -> None:
    # Sincerely A 8, B 2: B's 20% is under the 25% bar. The voter at 0.3 gives up 0.1 to vote A; the one at 0.1, 0.3.
    citizens = [*(_voter(i, 0.5) for i in range(8)), _voter(8, 0.3), _voter(9, 0.1)]
    strategic = _legislative(tmp_path, citizens, 0.15)
    assert (strategic["votes"], strategic["deserted"]) == ({"0": 9.0, "1": 1.0}, 1)
    assert strategic["sincere_votes"] == {"0": 8.0, "1": 2.0}  # the poll, kept for reseat
    sincere = _legislative(tmp_path, citizens, 0.0)
    assert sincere["votes"] == {"0": 8.0, "1": 2.0}
    assert "deserted" not in sincere and "sincere_votes" not in sincere


def test_the_governing_partys_policy_gain_counts_in_the_cost_of_deserting() -> None:
    # A governs and moved policy 0.15 toward the voter at 0.3: A is then worth -0.2 + 0.15 = -0.05 to them,
    # B -0.1. Sincerely they vote A; deserting to B costs 0.05 -- not the -0.1 the distance alone would say.
    voter = _voter(1, 0.3)
    governing = GoverningRecord(frozenset({0}), PolicyRecord(then=(0.6,), now=(0.45,)))
    assert choose_party(voter, [A, B], governing, 1.0) == 0
    assert strategic_party(voter, [A, B], 0, frozenset({1}), 0.1, governing, 1.0) == 1
    assert strategic_party(voter, [A, B], 0, frozenset({1}), 0.03, governing, 1.0) == 0


def test_reseat_starts_another_bar_from_the_vote_before_desertion() -> None:
    founding = {"institutions": {"electoral_threshold": 0.25, "seat_allocation": "dhondt", "assembly_seats": 10},
                "run": {"seed": 0}}
    result = {"event_type": "legislative_result", "tick": 8, "payload": {
        "seats": {"0": 10, "1": 0}, "votes": {"0": 9.0, "1": 1.0}, "sincere_votes": {"0": 8.0, "1": 2.0}}}
    assert reseat([result], founding)[0]["reseated_seats"] == {"0": 10, "1": 0}  # the record, from the recorded vote
    assert reseat([result], founding, threshold=0.15)[0]["reseated_seats"] == {"0": 8, "1": 2}  # B's sincere 20%


@pytest.mark.behavior("ELE-11")
@settings(max_examples=200, deadline=None)
@given(
    st.lists(st.tuples(st.floats(0, 1), st.floats(0.05, 0.6)), min_size=1, max_size=30),
    st.lists(st.floats(0, 1), min_size=1, max_size=6),
    st.floats(0.0, 0.5), st.floats(0.0, 0.3),
)
def test_a_deserter_lands_within_the_margin_on_a_party_above_the_threshold(voters, platforms, threshold, margin) -> None:
    citizens = [_voter(i, position, tolerance) for i, (position, tolerance) in enumerate(voters)]
    parties = [Party(i, (p,)) for i, p in enumerate(platforms)]
    by_id = {p.party_id: p for p in parties}
    sincere = [choose_party(c, parties) for c in citizens]
    viable = viable_parties(sincere, threshold)
    for citizen, choice in zip(citizens, sincere):
        moved = strategic_party(citizen, parties, choice, viable, margin)
        if choice is not None and choice not in viable and viable:  # stranded, with somewhere to go
            best = min(viable, key=lambda pid: (weighted_distance(citizen, by_id[pid].platform), pid))
            gap = weighted_distance(citizen, by_id[best].platform) - weighted_distance(citizen, by_id[choice].platform)
            should = gap <= margin and weighted_distance(citizen, by_id[best].platform) <= citizen.blank_threshold
            assert moved == (best if should and margin > 0 else choice)
        if moved == choice:
            continue
        assert choice is not None and choice not in viable and moved in viable
        cost = weighted_distance(citizen, by_id[moved].platform) - weighted_distance(citizen, by_id[choice].platform)
        assert cost <= margin + 1e-12
        assert weighted_distance(citizen, by_id[moved].platform) <= citizen.blank_threshold + 1e-12


def test_the_digest_reports_the_deserters_per_legislative_election() -> None:
    config = load_config()
    payload = {"seats": {"0": 10}, "votes": {"0": 9.0, "1": 1.0}, "blank_count": 0}
    events = [{"event_type": "legislative_result", "tick": 8, "payload": {**payload, "deserted": 3}},
              {"event_type": "legislative_result", "tick": 24, "payload": payload}]
    rows = effective_parties(events, config)
    assert rows is not None and rows[0]["deserted"] == 3 and "deserted" not in rows[1]

