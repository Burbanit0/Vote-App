"""ADR-026: the president's briefing shows what the last elections would have given under other rules."""
from __future__ import annotations

import re
from typing import Any

from api.domain.polity.amendments import stakes_text
from api.domain.polity.ballot_and_aggregation import allocate_seats, get_presidential_winner
from api.domain.polity.checkpoint import _legislature_from_dict, _legislature_to_dict
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import ARTICLES, load_config
from api.domain.polity.legislation import Legislature

PRESIDENT = Citizen(citizen_id=1, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5,
                    ambition_score=0.5, party_affiliation=2)
A, B, C = "citizen_1", "citizen_2", "citizen_3"
# The president (A) leads on first choices; B is everyone's second and beats each rival head to head.
BALLOTS = [[A, B, C]] * 3 + [[B, C, A]] * 2 + [[C, B, A]] * 2


def test_each_voting_method_is_named_once_with_whom_it_elects() -> None:
    text = stakes_text(load_config(), PRESIDENT, BALLOTS, None)
    assert text is not None
    methods = ARTICLES["institutions.presidential_method"].choices
    for method in methods:
        winner = get_presidential_winner(BALLOTS, str(method))
        who = "you" if winner == A else f"citizen {winner.removeprefix('citizen_')}"
        group = next(part for part in text.split(": ", 1)[1].rstrip(".").split("; ") if re.search(rf"\b{method}\b", part))
        assert group.startswith(f"{who} under ")
    assert "you under" in text and "citizen 2 under" in text  # plurality and the Condorcet methods disagree here


def test_the_party_seats_are_re_seated_under_each_rule_and_threshold() -> None:
    config = load_config()
    votes = {0: 50.0, 1: 34.0, 2: 9.0, 3: 7.0}
    text = stakes_text(config, PRESIDENT, None, Legislature(policy=(0.5,), votes=votes))
    assert text is not None
    seats = lambda method, bar: allocate_seats({str(p): v for p, v in votes.items()}, config.institutions.assembly_seats, method, bar)["2"]  # noqa: E731
    in_force = seats(config.institutions.seat_allocation, config.institutions.electoral_threshold)
    assert f"your party (2) wins {in_force} of {config.institutions.assembly_seats} seats" in text
    for rule in ARTICLES["institutions.seat_allocation"].choices:
        assert f"{rule} {seats(str(rule), config.institutions.electoral_threshold)}" in text
    assert "15% 0" in text  # 9% of the vote clears no 15% bar
    assert f"0% {seats(config.institutions.seat_allocation, 0.0)}" in text


def test_nothing_to_show_before_any_election_or_for_a_president_without_party() -> None:
    config = load_config()
    assert stakes_text(config, PRESIDENT, None, None) is None
    independent = Citizen(citizen_id=1, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.5)
    assert stakes_text(config, independent, None, Legislature(policy=(0.5,), votes={0: 1.0})) is None


def test_the_legislatures_votes_survive_a_checkpoint() -> None:
    legislature = Legislature(policy=(0.5,), seats={2: 10}, votes={2: 9.0, 0: 50.0})
    restored: Any = _legislature_from_dict(_legislature_to_dict(legislature))
    assert restored.votes == {2: 9.0, 0: 50.0}
    before_adr026 = {k: v for k, v in _legislature_to_dict(Legislature(policy=(0.5,))).items() if k != "votes"}
    assert _legislature_from_dict(before_adr026).votes is None  # a checkpoint from before ADR-026 loads


def test_the_amendment_is_a_required_field_a_president_may_set_to_null() -> None:
    import pydantic

    from api.domain.polity.llm_schemas import AMENDING_LEADER_TURN_JSON_SCHEMA, AmendingLeaderTurn

    assert "amendment" in AMENDING_LEADER_TURN_JSON_SCHEMA["required"]  # OBS-031: a field the model may omit, it omits
    base = dict(rationale="r", positions=[], bill=[], speech="s", note_to_self="", other_initiative="")
    assert AmendingLeaderTurn(**base, amendment=None).amendment is None
    try:
        AmendingLeaderTurn(**base)
    except pydantic.ValidationError:
        pass
    else:
        raise AssertionError("a turn without its amendment field must not decode")

