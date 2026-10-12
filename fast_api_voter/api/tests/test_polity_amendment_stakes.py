"""ADR-026: the president's briefing shows what the last elections would have given under other rules, and every
turn answers whether to amend."""
from __future__ import annotations

import dataclasses
import re
from typing import Any

import pydantic
import pytest

from api.domain.polity.agents import ISSUES, PresidentBriefing, president_user_prompt
from api.domain.polity.amendments import stakes_text
from api.domain.polity.ballot_and_aggregation import allocate_seats, get_presidential_winner, seat_lot
from api.domain.polity.checkpoint import _legislature_from_dict, _legislature_to_dict
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import ARTICLES, PolityConfigError, load_config, validate_config
from api.domain.polity.legislation import Legislature
from api.domain.polity.llm_behavior_engine import ResponseContext
from api.domain.polity.llm_schemas import AMENDING_LEADER_TURN_JSON_SCHEMA, AmendingLeaderTurn

PRESIDENT = Citizen(citizen_id=1, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5,
                    ambition_score=0.5, party_affiliation=2)
A, B, C = "citizen_1", "citizen_2", "citizen_3"
# The president (A) leads on first choices; B is everyone's second and beats each rival head to head.
BALLOTS = [[A, B, C]] * 3 + [[B, C, A]] * 2 + [[C, B, A]] * 2
VOTES = {0: 50.0, 1: 34.0, 2: 9.0, 3: 7.0}
MIDDLE = (0.5,) * len(ISSUES)


def _groups(text: str) -> dict[str, list[str]]:
    """'X under m1, m2; Y under m3.' -> {X: [m1, m2], Y: [m3]}, from the voting-method line."""
    line = text.splitlines()[0].split(": ", 1)[1].rstrip(".")
    return {who: methods.split(", ") for who, methods in (part.split(" under ") for part in line.split("; "))}


def _seat_rows(text: str) -> dict[str, int]:
    """'dhondt 9, largest_remainder 9 ...; at an electoral threshold of 0% 9, ...' -> {name: seats}."""
    line = text.splitlines()[-1]
    return {name: int(n) for name, n in re.findall(r"([a-z_]+|\d+%) (\d+)(?=[,;.])", line.split("under each seat allocation: ")[1])}


def test_each_voting_method_is_named_once_with_whom_it_elects() -> None:
    text = stakes_text(load_config(), PRESIDENT, BALLOTS, None)
    assert text is not None
    groups = _groups(text)
    assert sorted(m for methods in groups.values() for m in methods) == sorted(map(str, ARTICLES["institutions.presidential_method"].choices))
    for who, methods in groups.items():
        for method in methods:
            winner = get_presidential_winner(BALLOTS, method)
            assert who == ("you" if winner == A else f"citizen {winner.removeprefix('citizen_')}")
    assert {"you", "citizen 2"} <= set(groups)  # plurality and the Condorcet methods disagree here


def test_the_party_seats_are_re_seated_under_each_rule_and_threshold_with_the_elections_own_lot() -> None:
    config = load_config()
    legislature = Legislature(policy=(0.5,), votes=VOTES, votes_tick=8)
    text = stakes_text(config, PRESIDENT, None, legislature)
    assert text is not None

    def seats(method: str, bar: float) -> int:
        cast = {str(p): v for p, v in VOTES.items()}
        return allocate_seats(cast, config.institutions.assembly_seats, method, bar, rng=seat_lot(config.run.seed, 8))["2"]

    in_force = seats(config.institutions.seat_allocation, config.institutions.electoral_threshold)
    assert f"your party (2) wins {in_force} of {config.institutions.assembly_seats} seats under the rules in force" in text
    rows = _seat_rows(text)
    for rule in ARTICLES["institutions.seat_allocation"].choices:
        assert rows[str(rule)] == seats(str(rule), config.institutions.electoral_threshold)
    assert rows["0%"] == seats(config.institutions.seat_allocation, 0.0) and rows["15%"] == 0  # 9% clears no 15% bar


def test_nothing_to_show_before_any_election_or_for_a_president_without_party() -> None:
    config = load_config()
    assert stakes_text(config, PRESIDENT, None, None) is None
    independent = dataclasses.replace(PRESIDENT, party_affiliation=None)
    assert stakes_text(config, independent, None, Legislature(policy=(0.5,), votes={0: 1.0})) is None


def test_the_stakes_state_facts_and_never_what_to_propose() -> None:  # contract C4
    text = stakes_text(load_config(), PRESIDENT, BALLOTS, Legislature(policy=(0.5,), votes=VOTES, votes_tick=8))
    assert text is not None
    assert not re.search(r"\b(should|recommend|propose|consider|best|better|advis)", text, re.IGNORECASE)


def test_the_briefing_carries_the_stakes_into_the_presidents_prompt() -> None:
    briefing = PresidentBriefing(
        tick=9, ticks_per_year=4, context=ResponseContext(cid=1, legitimacy=0.6, mandate_dev=0.0, street=0.1,
                                                         lame_duck=False, ticks_left=7),
        approval=0.6, agenda_closed=None, policy=None, public_median=MIDDLE, assembly_median=None,
        pledge=MIDDLE, stated=MIDDLE, constitution="The constitution in force:", stakes="Counted under each voting method",
    )
    prompt = president_user_prompt(briefing, "")
    assert "The constitution in force:\nCounted under each voting method" in prompt
    assert "Counted under" not in president_user_prompt(dataclasses.replace(briefing, stakes=None), "")


def test_the_switch_is_off_by_default_on_in_exploration_and_needs_amendments(flagship: Any, tmp_path: Any) -> None:
    assert load_config().agents.amendment_stakes is False
    explored = flagship._flagship_config(
        engine="llm", years=2, population=100, seats=15, seed=1, output_dir=tmp_path, max_batch_replays=2,
        provider="vllm", workers=1, profile="exploration",
    )
    assert explored.agents.amendment_stakes and explored.agents.amendments
    with pytest.raises(PolityConfigError, match="amendment_stakes"):
        validate_config(dataclasses.replace(explored, agents=dataclasses.replace(explored.agents, amendments=False)))


def test_the_legislatures_votes_survive_a_checkpoint() -> None:
    legislature = Legislature(policy=(0.5,), seats={2: 10}, votes={2: 9.0, 0: 50.0}, votes_tick=8)
    restored = _legislature_from_dict(_legislature_to_dict(legislature))
    assert (restored.votes, restored.votes_tick) == ({2: 9.0, 0: 50.0}, 8)
    before_adr026 = {k: v for k, v in _legislature_to_dict(Legislature(policy=(0.5,))).items() if k not in ("votes", "votes_tick")}
    assert _legislature_from_dict(before_adr026).votes is None  # a checkpoint from before ADR-026 loads


def test_the_amendment_is_a_required_field_a_president_may_set_to_null() -> None:
    assert "amendment" in AMENDING_LEADER_TURN_JSON_SCHEMA["required"]  # OBS-031: a field the model may omit, it omits
    base = dict(rationale="r", positions=[], bill=[], speech="s", note_to_self="", other_initiative="")
    assert AmendingLeaderTurn(**base, amendment=None).amendment is None
    with pytest.raises(pydantic.ValidationError):
        AmendingLeaderTurn(**base)


def test_the_presidents_briefing_shows_the_stakes_only_when_switched_on_and_a_proposal_is_open(tmp_path: Any) -> None:
    import numpy as np

    from api.domain.polity import run_polity_simulation as engine
    from api.domain.polity.citizen import Office, Role
    from api.domain.polity.institutional_clock import InstitutionalClock
    from api.domain.polity.journal import Journal
    from api.domain.polity.parties import Party
    from api.domain.polity.tick_state import TickState

    president = dataclasses.replace(PRESIDENT, issue_positions=(0.5, 0.5), issue_priorities=(0.5, 0.5),
                                    role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(0.5, 0.5))
    member = Citizen(citizen_id=7, issue_positions=(0.4, 0.4), issue_priorities=(0.5, 0.5), blank_threshold=0.5,
                     ambition_score=0.5, sortition_seat_until_tick=20)

    def briefing(*, stakes: bool, members: list[Citizen]) -> PresidentBriefing:
        config = load_config()
        config = dataclasses.replace(config, agents=dataclasses.replace(config.agents, amendments=True, amendment_stakes=stakes))
        state = TickState(citizens=[president, *members], parties=[Party(2, (0.5, 0.5)), Party(0, (0.1, 0.1))],
                          rupture_rng=np.random.default_rng(0), events_rng=np.random.default_rng(0),
                          sortition_rng=np.random.default_rng(0), last_ballots=BALLOTS,
                          legislature=Legislature(policy=(0.5, 0.5), votes=VOTES, votes_tick=8))
        clock = InstitutionalClock.from_config(config.institutions, config.run, config.sortition_chamber)
        with Journal(tmp_path / f"e-{stakes}-{len(members)}.jsonl", "run") as journal:
            context = engine.TickContext(tick=9, config=config, journal=journal, client=None, clock=clock, graph=None,
                                         snapshots_path=tmp_path / "s.jsonl", election=None)
            return engine._president_briefing(context, state, president, (0.5, 0.5), (0.5, 0.5), None)

    shown = briefing(stakes=True, members=[member]).stakes
    assert shown is not None and shown.startswith("Counted under each voting method")
    assert briefing(stakes=False, members=[member]).stakes is None
    assert briefing(stakes=True, members=[]).stakes is None  # no chamber drawn: no amendment can be proposed

