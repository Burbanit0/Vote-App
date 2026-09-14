"""S4.2: ordinary legislation (docs/adr/ADR-009-ordinary-legislation.md) -- the policy status
quo, a bill's path through the assembly, the president's cohabitation block and the sortition
chamber's suspensive veto, and voters judging the policy a term presided over. Legislation
off, and the retrospection weight at zero, are the control arms."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import api.domain.polity.run_polity_simulation as engine
from api.domain.polity.checkpoint import load_checkpoint, save_checkpoint
from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.config import LegislationConfig, PolityConfig, PolityConfigError, load_config, validate_config
from api.domain.polity.institutional_clock import InstitutionalClock
from api.domain.polity.journal import Journal
from api.domain.polity.legislation import (
    GOVERNMENT,
    PRESIDENT,
    Bill,
    Legislature,
    assembly_vote,
    chamber_review,
    congruence,
    draft_bill,
    moves_away,
    population_median,
)
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import (
    GoverningRecord,
    IncumbentRecord,
    PolicyRecord,
    build_ranking,
    choose_party,
    policy_gain,
    utility_ballot,
)
from api.domain.polity.tick_state import TickState
from api.tests.polity_golden import golden_config
from api.tests.test_polity_run_simulation import _SimulatedCrash

RULES = LegislationConfig(enabled=True, bill_interval_ticks=2, max_bill_dimensions=2, max_bill_step=0.1,
                          assembly_majority_ratio=0.5, cohabitation_block=True)


def _citizen(cid: int, positions: tuple[float, ...], *, priorities: tuple[float, ...] | None = None, threshold: float = 0.5,
             **overrides: Any) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities or (1 / len(positions),) * len(positions),
                   blank_threshold=threshold, ambition_score=0.5, **overrides)


def _president(cid: int, position: tuple[float, ...], party: int) -> Citizen:
    return _citizen(cid, position, party_affiliation=party, office=Office.PRESIDENT, role=Role.ELECTED, revealed_position=position,
                    term_end_tick=16)


def _member(cid: int, position: tuple[float, ...]) -> Citizen:
    return _citizen(cid, position, sortition_seat_until_tick=40, chamber_position=position)


# ── config ────────────────────────────────────────────────────────────────

def test_the_shipped_config_legislates_nothing_and_judges_no_policy() -> None:
    config = load_config()
    assert config.legislation == dataclasses.replace(RULES, enabled=False)
    assert config.vote.policy_retrospection == 0.0
    with pytest.raises(PolityConfigError, match="max_bill_dimensions"):
        validate_config(dataclasses.replace(config, legislation=dataclasses.replace(RULES, max_bill_dimensions=21)))


# ── the rules ─────────────────────────────────────────────────────────────

def test_the_status_quo_starts_at_each_issue_s_median() -> None:
    assert population_median([_citizen(0, (0.1, 0.9)), _citizen(1, (0.5, 0.2)), _citizen(2, (0.3, 0.4))]) == (0.3, 0.4)
    assert population_median([_citizen(0, (0.2,)), _citizen(1, (0.6,))]) == (0.4,)


def test_a_bill_moves_the_largest_weighted_gaps_by_at_most_the_step() -> None:
    policy = (0.5, 0.5, 0.5, 0.5)
    aim = (0.9, 0.55, 0.1, 0.9)
    priorities = (0.25, 0.25, 0.25, 0.25)
    bill = draft_bill(policy, aim, priorities, RULES, bill_id=3, agenda_setter=PRESIDENT, proposer=7)
    # Gaps 0.4, 0.05, 0.4, 0.4: a three-way tie, broken toward the lower issues.
    assert bill == Bill(bill_id=3, agenda_setter=PRESIDENT, proposer=7, dimensions=(0, 2), proposal=(0.6, 0.4))
    assert bill.enacted(policy) == (0.6, 0.5, 0.4, 0.5)
    near = draft_bill(policy, (0.55, 0.5, 0.5, 0.5), priorities, RULES, bill_id=1, agenda_setter=GOVERNMENT, proposer=2)
    assert near is not None and (near.dimensions, near.proposal) == ((0,), (0.55,))  # a gap under the step is closed
    assert draft_bill(policy, policy, priorities, RULES, bill_id=1, agenda_setter=PRESIDENT, proposer=7) is None


def test_the_assembly_passes_a_bill_only_with_more_than_the_majority_of_seats() -> None:
    parties = [Party(0, (0.8, 0.8)), Party(1, (0.2, 0.2)), Party(2, (0.7, 0.6))]
    bill = Bill(bill_id=1, agenda_setter=PRESIDENT, proposer=9, dimensions=(0,), proposal=(0.6,))
    vote = assembly_vote(parties, {0: 40, 1: 50, 2: 10}, (0.5, 0.5), bill, 0.5)
    assert (vote.yes_parties, vote.yes_seats, vote.no_seats, vote.passed) == ((0, 2), 50, 50, False)
    assert assembly_vote(parties, {0: 45, 1: 45, 2: 10}, (0.5, 0.5), bill, 0.5).passed
    assert assembly_vote(parties, {0: 0, 1: 45, 2: 55}, (0.5, 0.5), bill, 0.5).yes_parties == (2,)  # an unseated party does not vote


def test_the_chamber_rejects_on_a_majority_against_and_a_president_s_distance_is_weighted() -> None:
    bill = Bill(bill_id=1, agenda_setter=PRESIDENT, proposer=9, dimensions=(0,), proposal=(0.6,))
    members = [_member(1, (0.9, 0.5)), _member(2, (0.1, 0.5)), _citizen(3, (0.2, 0.5), sortition_seat_until_tick=40)]
    review = chamber_review(members, (0.5, 0.5), bill)
    assert (review.yes, review.no, review.rejects) == (1, 2, True)  # member 3 has no chamber_position: its own view counts
    assert not chamber_review(members[:2], (0.5, 0.5), bill).rejects  # a tie is no veto
    assert moves_away((0.2, 0.5), (0.5, 0.5), (0.5, 0.5), bill)
    assert not moves_away((0.2, 0.5), (0.0, 1.0), (0.5, 0.5), bill)  # the president cares only about the issue left alone


def test_congruence_measures_policy_against_the_median_and_against_each_citizen() -> None:
    citizens = [_citizen(0, (0.2, 0.2)), _citizen(1, (0.4, 0.4)), _citizen(2, (0.6, 0.6))]
    fit = congruence(citizens, (0.5, 0.5))
    assert fit.median_distance == pytest.approx(0.1)
    assert fit.mean_citizen_distance == pytest.approx((0.3 + 0.1 + 0.1) / 3)


# ── voters judging policy ─────────────────────────────────────────────────

@st.composite
def _judged_elections(draw: st.DrawFn) -> tuple[Citizen, list[Party], GoverningRecord, list[Citizen], IncumbentRecord]:
    issues = draw(st.integers(1, 4))
    unit = st.floats(0.0, 1.0, allow_nan=False)
    point = st.lists(unit, min_size=issues, max_size=issues).map(tuple)
    raw = draw(st.lists(st.floats(0.01, 1.0), min_size=issues, max_size=issues))
    voter = _citizen(0, draw(point), priorities=tuple(p / sum(raw) for p in raw), threshold=draw(unit), party_affiliation=draw(st.integers(0, 2)))
    parties = [Party(pid, draw(point)) for pid in range(draw(st.integers(1, 4)))]
    policy = PolicyRecord(then=draw(point), now=draw(point))
    governing = GoverningRecord(parties=frozenset(draw(st.lists(st.integers(0, 3), max_size=3))), policy=policy)
    candidates = [_citizen(cid, draw(point), party_affiliation=draw(st.integers(0, 2)), revealed_position=None) for cid in range(1, draw(st.integers(2, 5)))]
    for candidate in candidates:
        candidate.pledged_platform = candidate.revealed_position = candidate.issue_positions
    incumbent = IncumbentRecord(citizen_id=candidates[0].citizen_id, party=candidates[0].party_affiliation, record=draw(st.floats(-1, 1)), policy=policy)
    return voter, parties, governing, candidates, incumbent


@settings(max_examples=300, deadline=None)
@given(_judged_elections())
def test_with_the_weight_at_zero_a_policy_record_changes_no_party_choice_and_no_ballot(election: tuple) -> None:
    voter, parties, governing, candidates, incumbent = election
    assert choose_party(voter, parties, governing, 0.0) == choose_party(voter, parties)
    zero = dataclasses.replace(load_config().vote, approval=0.0, partisanship=0.0, turnout_cost=0.0, policy_retrospection=0.0)
    assert utility_ballot(voter, candidates, zero, incumbent=incumbent) == build_ranking(voter, candidates)


def test_voters_reward_the_government_that_moved_policy_their_way() -> None:
    voter = _citizen(0, (0.8,), threshold=0.4, party_affiliation=5)
    record = PolicyRecord(then=(0.2,), now=(0.6,))
    assert policy_gain(voter, record) == pytest.approx(0.4)
    parties = [Party(0, (0.75,)), Party(1, (0.6,))]
    assert choose_party(voter, parties) == 0
    assert choose_party(voter, parties, GoverningRecord(frozenset({1}), record), 1.0) == 1
    # A governing record cannot make an unacceptable party acceptable past the voter's tolerance...
    far = [Party(0, (0.0,))]
    assert choose_party(voter, far, GoverningRecord(frozenset({0}), record), 0.1) is None
    # ...but a large enough gain can.
    assert choose_party(voter, far, GoverningRecord(frozenset({0}), record), 2.0) == 0

    config = load_config().vote
    incumbent_party = _citizen(1, (0.5,), party_affiliation=3)
    incumbent = _citizen(2, (0.5,), party_affiliation=3)
    rival = _citizen(3, (0.52,), party_affiliation=4)
    for candidate in (incumbent_party, incumbent, rival):
        candidate.pledged_platform = candidate.revealed_position = candidate.issue_positions
    judged = IncumbentRecord(citizen_id=2, party=3, record=0.0, policy=record)
    weighted = dataclasses.replace(config, policy_retrospection=1.0, approval_party_carryover=0.5)
    assert utility_ballot(voter, [incumbent_party, incumbent, rival], weighted, incumbent=judged)[:2] == ["citizen_2", "citizen_1"]
    assert utility_ballot(voter, [incumbent_party, incumbent, rival], config, incumbent=judged)[0] == "citizen_3"


def test_the_judged_incumbent_carries_policy_even_without_legitimacy() -> None:
    config = load_config()
    president = _president(4, (0.5,), party=1)
    record = PolicyRecord(then=(0.2,), now=(0.5,))
    assert engine._judged_incumbent([president], 4, config) is None
    judged = engine._judged_incumbent([president], 4, config, record)
    assert judged == IncumbentRecord(citizen_id=4, party=1, record=0.0, policy=record)
    assert engine._judged_incumbent([president], None, config, record) is None


def test_the_governing_record_is_the_last_coalition_or_else_the_president_s_party() -> None:
    president = _president(4, (0.5,), party=1)
    legislature = Legislature(policy=(0.6,))
    assert engine._governing_record([president], legislature) is None  # no assembly elected yet
    assert engine._governing_record([president], None) is None
    legislature.policy_at_assembly_start = (0.4,)
    assert engine._governing_record([president], legislature) == GoverningRecord(frozenset({1}), PolicyRecord((0.4,), (0.6,)))
    legislature.coalition = (0, 2)
    assert engine._governing_record([president], legislature) == GoverningRecord(frozenset({0, 2}), PolicyRecord((0.4,), (0.6,)))
    legislature.coalition = None
    assert engine._governing_record([_citizen(5, (0.5,))], legislature) is None
    assert engine._term_policy_record(legislature) is None
    legislature.policy_at_term_start = (0.3,)
    assert engine._term_policy_record(legislature) == PolicyRecord((0.3,), (0.6,))


# ── a bill's path, one tick at a time ─────────────────────────────────────

PARTIES = [Party(0, (0.8, 0.8)), Party(1, (0.2, 0.2))]


def _config(**chamber: Any) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config, legislation=RULES,
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, **chamber),
    )


def _state(citizens: list[Citizen], legislature: Legislature) -> TickState:
    return TickState(citizens=citizens, parties=PARTIES, rupture_rng=np.random.default_rng(0), events_rng=np.random.default_rng(0),
                     sortition_rng=np.random.default_rng(0), legislature=legislature)


def _legislate(tmp_path: Path, config: PolityConfig, state: TickState, ticks: range) -> list[dict[str, Any]]:
    clock = InstitutionalClock.from_config(config.institutions, config.run, config.sortition_chamber)
    path = tmp_path / "run" / "events.jsonl"
    with Journal(path, "run") as journal:
        for tick in ticks:
            context = engine.TickContext(tick=tick, config=config, journal=journal, client=None, clock=clock, graph=None,
                                         snapshots_path=tmp_path / "snapshots.jsonl", election=None)
            engine._phase_legislation(context, state)
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return [{"tick": e["tick"], "type": e["event_type"], **e["payload"]} for e in events if e["event_type"] != "policy_status"]


def test_a_vetoed_bill_waits_blocks_the_agenda_and_is_enacted_on_its_second_reading(tmp_path: Path) -> None:
    legislature = Legislature(policy=(0.5, 0.5), seats={0: 60, 1: 40}, coalition=(0,))
    state = _state([_president(0, (0.9, 0.9), party=0), *(_member(cid, (0.2, 0.2)) for cid in (1, 2, 3))], legislature)
    events = _legislate(tmp_path, _config(veto_power="suspensive_limited", veto_delay_ticks=2), state, range(0, 3))
    assert events == [
        {"tick": 0, "type": "bill_proposed", "bill_id": 1, "agenda_setter": "president", "proposer": 0, "dimensions": [0, 1],
         "status_quo": [0.5, 0.5], "proposal": [0.6, 0.6]},
        {"tick": 0, "type": "bill_voted", "bill_id": 1, "reading": 1, "yes_seats": 60, "no_seats": 40, "yes_parties": [0], "passed": 1},
        {"tick": 0, "type": "bill_reviewed", "bill_id": 1, "yes": 0, "no": 3, "veto": 1, "returns_at_tick": 2},
        {"tick": 2, "type": "bill_voted", "bill_id": 1, "reading": 2, "yes_seats": 60, "no_seats": 40, "yes_parties": [0], "passed": 1},
        {"tick": 2, "type": "bill_enacted", "bill_id": 1, "dimensions": [0, 1], "old_values": [0.5, 0.5], "new_values": [0.6, 0.6], "enacted": 1},
    ]
    assert (legislature.policy, legislature.suspended, legislature.bills_drafted, legislature.bills_enacted) == ((0.6, 0.6), None, 1, 1)


def test_a_consultative_chamber_only_records_its_review(tmp_path: Path) -> None:
    legislature = Legislature(policy=(0.5, 0.5), seats={0: 60, 1: 40}, coalition=(0,))
    state = _state([_president(0, (0.9, 0.9), party=0), _member(1, (0.2, 0.2))], legislature)
    events = _legislate(tmp_path, _config(veto_power="consultative_only"), state, range(0, 1))
    assert [(e["type"], e.get("veto")) for e in events] == [("bill_proposed", None), ("bill_voted", None), ("bill_reviewed", 0), ("bill_enacted", None)]
    assert "returns_at_tick" not in events[2]


def test_under_cohabitation_the_government_proposes_and_the_president_blocks_what_moves_away(tmp_path: Path) -> None:
    config = dataclasses.replace(_config(), sortition_chamber=dataclasses.replace(load_config().sortition_chamber, enabled=False))
    legislature = Legislature(policy=(0.5, 0.5), seats={0: 60, 1: 40}, coalition=(0,))
    state = _state([_president(0, (0.2, 0.2), party=1)], legislature)
    events = _legislate(tmp_path / "blocked", config, state, range(0, 1))
    assert [e["type"] for e in events] == ["bill_proposed", "bill_voted", "bill_blocked"]
    assert (events[0]["agenda_setter"], events[0]["proposer"], events[0]["proposal"]) == ("government", 0, [0.6, 0.6])
    assert legislature.policy == (0.5, 0.5)

    unblocked = dataclasses.replace(config, legislation=dataclasses.replace(RULES, cohabitation_block=False))
    events = _legislate(tmp_path / "unblocked", unblocked, _state([_president(0, (0.2, 0.2), party=1)], legislature), range(0, 1))
    assert [e["type"] for e in events] == ["bill_proposed", "bill_voted", "bill_enacted"]


def test_nothing_is_read_without_an_assembly_or_a_president_or_off_the_interval(tmp_path: Path) -> None:
    config = _config()
    no_assembly = _state([_president(0, (0.9, 0.9), party=0)], Legislature(policy=(0.5, 0.5)))
    assert _legislate(tmp_path / "a", config, no_assembly, range(0, 4)) == []
    vacant = _state([_citizen(0, (0.9, 0.9))], Legislature(policy=(0.5, 0.5), seats={0: 60, 1: 40}))
    assert _legislate(tmp_path / "b", config, vacant, range(0, 4)) == []
    failing = _state([_president(0, (0.9, 0.9), party=1)], Legislature(policy=(0.5, 0.5), seats={0: 40, 1: 60}))
    events = _legislate(tmp_path / "c", config, failing, range(1, 4))  # no coalition: the president still proposes
    assert [(e["tick"], e["type"], e.get("passed")) for e in events] == [(2, "bill_proposed", None), (2, "bill_voted", 0)]
    at_aim = _state([_president(0, (0.5, 0.5), party=0)], Legislature(policy=(0.5, 0.5), seats={0: 60, 1: 40}))
    assert _legislate(tmp_path / "d", config, at_aim, range(0, 1)) == []
    assert _legislate(tmp_path / "e", config, _state([], Legislature(policy=(0.5,))), range(0, 1)) == []
    # No legislature at all (legislation off): the phase does nothing, not even the yearly status.
    off = dataclasses.replace(_state([], Legislature(policy=(0.5,))), legislature=None)
    assert _legislate(tmp_path / "f", config, off, range(0, 1)) == []


# ── the engine ────────────────────────────────────────────────────────────

def _run_config(output_dir: Path, years: int = 6) -> PolityConfig:
    config = golden_config(output_dir, llm=False)
    return dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=years), legislation=RULES,
                               vote=dataclasses.replace(config.vote, policy_retrospection=2.0))


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_legislating_run_keeps_its_assembly_journals_yearly_policy_and_enacts_what_it_records(tmp_path: Path) -> None:
    config = _run_config(tmp_path)
    journal = run_simulation(config, run_id="run")
    events = _lines(journal)
    statuses = [e for e in events if e["event_type"] == "policy_status"]
    assert [e["tick"] for e in statuses] == list(range(0, config.run.total_ticks + 1, config.run.ticks_per_year))

    legislature = load_checkpoint(journal.parent / "checkpoint.json").state.legislature
    assert legislature is not None and legislature.seats is not None and legislature.policy_at_assembly_start is not None
    last_result = [e for e in events if e["event_type"] == "legislative_result"][-1]
    assert legislature.seats == {int(k): v for k, v in last_result["payload"]["seats"].items()}

    policy = dict(enumerate(statuses[0]["payload"]["policy"]))
    enacted = [e for e in events if e["event_type"] == "bill_enacted"]
    assert [e["event_type"] for e in events].count("bill_proposed") > 0
    for event in enacted:
        policy.update(zip(event["payload"]["dimensions"], event["payload"]["new_values"]))
    assert tuple(policy.values()) == legislature.policy
    assert legislature.bills_enacted == len(enacted)


def test_legislation_off_writes_no_legislature_and_a_legislating_run_resumes_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    static = run_simulation(golden_config(tmp_path / "static", llm=False), run_id="run")
    assert "legislature" not in json.loads((static.parent / "checkpoint.json").read_text())

    uninterrupted = run_simulation(_run_config(tmp_path / "a"), run_id="run")
    real_phase = engine._run_accountability_phase

    def _crash_at_tick_13(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 13:
            raise _SimulatedCrash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", _crash_at_tick_13)
    with pytest.raises(_SimulatedCrash):
        run_simulation(_run_config(tmp_path / "b"), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_run_config(tmp_path / "b"), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()


def test_a_legislature_with_a_suspended_bill_round_trips_through_the_checkpoint(tmp_path: Path) -> None:
    legislature = Legislature(
        policy=(0.6, 0.4), seats={0: 60, 1: 40}, coalition=(0, 1), policy_at_term_start=(0.5, 0.5), policy_at_assembly_start=(0.55, 0.45),
        suspended=Bill(bill_id=4, agenda_setter=GOVERNMENT, proposer=0, dimensions=(1,), proposal=(0.3,), returns_at_tick=9),
        bills_drafted=4, bills_enacted=2,
    )
    path = tmp_path / "checkpoint.json"
    save_checkpoint(path, run_id="r", config=load_config(), tick=7, next_event_id=3, state=_state([], legislature))
    assert load_checkpoint(path).state.legislature == legislature
    blank = Legislature(policy=(0.5,))
    save_checkpoint(path, run_id="r", config=load_config(), tick=7, next_event_id=3, state=_state([], blank))
    assert load_checkpoint(path).state.legislature == blank
