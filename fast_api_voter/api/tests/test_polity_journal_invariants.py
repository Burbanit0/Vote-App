"""The journal invariant checker (api/domain/polity/journal_invariants.py), and the
simulator held to it over runs Hypothesis draws.

The first half proves each check can fail: a real journal passes, and each defect
injected into a copy of it is reported under its catalogue ID. The second half runs the
simulator -- the golden scenario on both engines, then small runs over drawn seeds,
populations, mechanism switches and constitutional amendments -- and asserts the
checker finds nothing. Only the second half is linked to the catalogue
(docs/spec/behaviors.md): it is what checks the simulator.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from api.domain.polity.config import ARTICLES, PolityConfig, PolityConfigError, ScriptedAmendment, validate_config
from api.domain.polity.journal_invariants import Violation, check_journal, presidential_calendar
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import golden_config
from api.tests.test_polity_constitution import _legal_value
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

def _run(config: PolityConfig, *, llm: bool = False) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as out:
        config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=out))
        path = run_simulation(config, run_id="invariants", llm_client=_ElectingFakeLlmClient() if llm else None)
        return [json.loads(line) for line in path.read_text().splitlines()]


def _config() -> PolityConfig:
    config = golden_config(Path("unused"), llm=False)
    return dataclasses.replace(config, emotions=dataclasses.replace(config.emotions, enabled=True))


def _ids(violations: list[Violation]) -> set[str]:
    return {violation.behavior for violation in violations}


def _renumber(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for position, event in enumerate(events):
        event["event_id"] = position
    return events


def _event(event_type: str, tick: int, payload: dict[str, Any], citizen_id: int | None = None) -> dict[str, Any]:
    return {"event_id": -1, "tick": tick, "event_type": event_type, "citizen_id": citizen_id, "payload": payload}


def _first(events: list[dict[str, Any]], event_type: str) -> int:
    return next(i for i, event in enumerate(events) if event["event_type"] == event_type)


@pytest.fixture(scope="module")
def clean() -> list[dict[str, Any]]:
    return _run(_config())


@pytest.fixture
def events(clean: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy(clean)


# ── each check can fail ──────────────────────────────────────────────────


def test_a_real_journal_passes_and_shows_what_the_checks_read(clean: list[dict[str, Any]]) -> None:
    assert check_journal(clean, _config()) == []
    types = {event["event_type"] for event in clean}
    assert {"elected", "legislative_result", "legitimacy_updated", "emotions_updated"} <= types


def test_a_skipped_event_id_is_reported(events: list[dict[str, Any]]) -> None:
    events[5]["event_id"] = 99
    assert [v.behavior for v in check_journal(events, _config())] == ["JRN-01"]


def test_a_line_off_its_type_is_reported(events: list[dict[str, Any]]) -> None:
    events[3]["payload"]["surplus"] = 1
    assert _ids(check_journal(events, _config())) == {"JRN-02"}


def test_seats_not_summing_to_the_assembly_are_reported(events: list[dict[str, Any]]) -> None:
    result = events[_first(events, "legislative_result")]
    party = next(iter(result["payload"]["seats"]))
    result["payload"]["seats"][party] += 1
    [violation] = check_journal(events, _config())
    assert (violation.behavior, violation.event_id) == ("ELE-01", result["event_id"])


def test_seats_follow_an_amended_assembly_size(events: list[dict[str, Any]]) -> None:
    at = _first(events, "legislative_result")
    seats = events[at]["payload"]["seats"]
    total = sum(seats.values())
    amended = _event("constitution_amended", events[at]["tick"], {
        "article": "institutions.assembly_seats", "old": total, "new": total + 1, "version": 1, "source": "scripted",
    })
    events.insert(at, amended)
    assert _ids(check_journal(_renumber(events), _config())) == {"ELE-01"}
    party = next(iter(seats))
    seats[party] += 1
    assert check_journal(events, _config()) == []


def test_an_assembly_left_empty_when_no_party_clears_the_threshold_passes(events: list[dict[str, Any]]) -> None:
    seats = events[_first(events, "legislative_result")]["payload"]["seats"]
    for party in seats:
        seats[party] = 0
    assert check_journal(events, _config()) == []


def test_a_malformed_line_is_reported_without_hiding_the_rest(events: list[dict[str, Any]]) -> None:
    neutral = max(i for i, event in enumerate(events) if event["event_type"] == "legitimacy_updated")
    del events[neutral]["tick"]  # a line no calendar or seat check reads
    result = events[_first(events, "legislative_result")]
    del result["payload"]["seats"]
    events[_first(events, "legitimacy_updated")]["payload"]["legitimacy"] = 2.0
    violations = check_journal(events, _config())
    assert {(v.behavior, v.event_id) for v in violations} == {
        ("JRN-02", neutral), ("JRN-02", result["event_id"]), ("CIT-01", events[_first(events, "legitimacy_updated")]["event_id"]),
    }


def test_a_missing_or_extra_legislative_result_is_reported(events: list[dict[str, Any]]) -> None:
    at = _first(events, "legislative_result")
    events.insert(at, copy.deepcopy(events[at]))
    assert _ids(check_journal(_renumber(events), _config())) == {"ELE-02"}
    del events[at : at + 2]
    assert _ids(check_journal(_renumber(events), _config())) == {"ELE-02"}


def test_a_presidential_outcome_off_the_calendar_is_reported(events: list[dict[str, Any]]) -> None:
    elected = events[_first(events, "elected")]
    assert elected["tick"] == 0
    elected["tick"] = 1
    violations = check_journal(events, _config())
    assert _ids(violations) == {"ELE-02"}
    assert {v.message for v in violations} == {
        "tick 0: 0 presidential outcome(s), 1 expected", "tick 1: 1 presidential outcome(s), 0 expected",
    }


def test_a_rerun_replaces_the_calendar_until_it_resolves() -> None:
    config = _config()
    invalidated = {"office": "president", "blank_share": 0.6, "threshold": 0.5, "attempt": 1,
                   "candidate_ids": [1], "barred_candidate_ids": [], "next_attempt_tick": 3}
    elected = {"office": "president", "attempt": 1, "forced": 0}
    journal = [_event("election_invalidated", 0, invalidated), _event("elected", 3, elected)]
    assert _calendar(journal, config) == []
    journal[1]["tick"] = 2
    assert _calendar(journal, config) == ["tick 2: 1 presidential outcome(s), 0 expected"]


def test_a_snap_election_is_held_on_its_tick_off_the_calendar() -> None:
    config = _config()
    journal = [
        _event("elected", 0, {"office": "president", "attempt": 0, "forced": 0}),
        _event("snap_election_triggered", 2, {"office": "president", "recalled_citizen_id": 4, "next_attempt_tick": 3}),
        _event("election_no_winner", 3, {"office": "president"}),
    ]
    assert _calendar(journal, config) == []
    del journal[2]
    assert _calendar(journal, config) == ["tick 3: 0 presidential outcome(s), 1 expected"]


def test_a_president_kept_on_by_refusal_cancels_the_election() -> None:
    config = _config()
    refusal = {"act": "refuse_to_leave", "approval": 0.7, "probability": 0.6, "success": 1}
    journal = [_event("extra_legal_act", 0, refusal, citizen_id=4)]
    assert _calendar(journal, config) == []
    journal[0]["payload"]["success"] = 0
    assert _calendar(journal, config) == ["tick 0: 0 presidential outcome(s), 1 expected"]


def _calendar(journal: list[dict[str, Any]], config: PolityConfig) -> list[str]:
    """The presidential half of ELE-02 alone, on a hand-made journal."""
    return [v.message for v in presidential_calendar(_renumber(journal), config)]


def test_an_elected_event_with_a_reason_is_reported(events: list[dict[str, Any]]) -> None:
    events[_first(events, "elected")]["payload"]["reason"] = "no_candidates"
    assert _ids(check_journal(events, _config())) == {"ELE-05", "JRN-02"}


def test_a_second_counted_vote_is_reported_and_an_audit_ballot_is_not() -> None:
    config = _config()
    ballot = {"blank": 0, "ranking": [1, 2], "llm_fallback": 0, "retry_sampling_varied": 0, "llm_call_id": None}
    journal = [_event("vote_cast", 0, ballot, citizen_id=7), _event("vote_cast", 0, {**ballot, "audit": 1}, citizen_id=7)]
    assert "ELE-10" not in _ids(check_journal(_renumber(journal), config))
    journal.append(_event("vote_cast", 0, ballot, citizen_id=7))
    journal.append(_event("vote_cast", 4, ballot, citizen_id=7))
    [violation] = [v for v in check_journal(_renumber(journal), config) if v.behavior == "ELE-10"]
    assert violation.event_id == 2


@pytest.mark.parametrize(("event_type", "key", "behavior"), [
    ("legitimacy_updated", "legitimacy", "CIT-01"),
    ("emotions_updated", "anger", "CIT-10"),
    ("emotions_updated", "enthusiasm", "CIT-10"),
])
@pytest.mark.parametrize("value", [-0.01, 1.01, None, True])
def test_a_value_out_of_the_unit_interval_is_reported(
    events: list[dict[str, Any]], event_type: str, key: str, behavior: str, value: float | None,
) -> None:
    event = events[_first(events, event_type)]
    event["payload"][key] = value
    [violation] = check_journal(events, _config())
    assert (violation.behavior, violation.event_id) == (behavior, event["event_id"])


# ── the simulator, held to the catalogue ─────────────────────────────────


@pytest.mark.behavior("JRN-01", "JRN-02", "ELE-01", "ELE-02", "ELE-05", "ELE-10", "CIT-01", "CIT-10")
@pytest.mark.parametrize(("llm", "vote_mode"), [(False, None), (True, None), (True, "llm")], ids=["rules", "llm", "llm-ballots"])
def test_the_golden_scenario_keeps_every_journal_invariant(llm: bool, vote_mode: str | None) -> None:
    config = golden_config(Path("unused"), llm=llm)
    if vote_mode is not None:
        config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, mode=vote_mode))
    events = _run(config, llm=llm)
    assert check_journal(events, config) == []
    if vote_mode == "llm":  # ELE-10 needs counted ballots; the utility mode journals audit ones only
        assert any(e["event_type"] == "vote_cast" and "audit" not in e["payload"] for e in events)


# Each switch sets its keys together: validate_config requires these to agree
# (petition and street pressure need legitimacy; a petition key lives in two sections;
# events.enabled is the or of its two kinds).
MECHANISMS: dict[str, tuple[tuple[str, str], ...]] = {
    "blank_vote_competitive": (("institutions", "blank_vote_competitive"),),
    "snap_election_on_recall": (("institutions", "snap_election_on_recall"),),
    "rupture": (("candidacy", "rupture_path_enabled"),),
    "accountability": (
        ("legitimacy", "enabled"), ("petition", "enabled"), ("pressure_menu", "petition_enabled"),
        ("street_pressure", "enabled"), ("pressure_menu", "mobilization_enabled"),
    ),
    "mandate": (("mandate", "enabled"),),
    "events": (("events", "enabled"), ("events", "scandal_enabled"), ("events", "economic_shock_enabled")),
    "emotions": (("emotions", "enabled"),),
    "sortition": (("sortition_chamber", "enabled"),),
}


def _switched(config: PolityConfig, switches: dict[str, bool]) -> PolityConfig:
    for name, on in switches.items():
        for section, field in MECHANISMS[name]:
            config = dataclasses.replace(config, **{section: dataclasses.replace(getattr(config, section), **{field: on})})
    return config


@st.composite
def _amendments(draw: st.DrawFn, last_tick: int) -> tuple[ScriptedAmendment, ...]:
    paths = draw(st.lists(st.sampled_from(sorted(ARTICLES)), max_size=3, unique=True))
    return tuple(
        ScriptedAmendment(tick=draw(st.integers(0, last_tick)), article=path, value=draw(_legal_value(ARTICLES[path])))
        for path in paths
    )


@pytest.mark.behavior("JRN-01", "JRN-02", "ELE-01", "ELE-02", "ELE-05", "ELE-10", "CIT-01", "CIT-10")
@settings(max_examples=25, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(
    seed=st.integers(0, 2**31 - 1),
    population=st.integers(20, 60),
    switches=st.fixed_dictionaries({name: st.booleans() for name in MECHANISMS}),
    blank_threshold=st.sampled_from([0.05, 0.2, 0.5]),
    years=st.integers(2, 3),
    terms=st.tuples(st.integers(1, 2), st.integers(1, 2), st.integers(0, 1)),
    amendments=_amendments(last_tick=8),
)
def test_any_small_run_keeps_every_journal_invariant(
    seed: int, population: int, switches: dict[str, bool], blank_threshold: float, years: int,
    terms: tuple[int, int, int], amendments: tuple[ScriptedAmendment, ...],
) -> None:
    """Terms of a year or two over two or three years put several presidential and
    legislative elections in each run, so a calendar election follows a rerun or a snap
    election, not only the founding one at tick 0."""
    president, assembly, offset = terms
    config = _switched(golden_config(Path("unused"), llm=False), switches)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, seed=seed, population_size=population, duration_years=years),
        institutions=dataclasses.replace(
            config.institutions, blank_invalidation_threshold=blank_threshold,
            president_term_years=president, assembly_term_years=assembly, assembly_offset_years=offset,
        ),
        constitution=dataclasses.replace(config.constitution, scripted=amendments),
    )
    try:
        validate_config(config)
    except PolityConfigError:
        assume(False)  # a mechanism another one requires was drawn off, or an amendment broke the rules
    assert check_journal(_run(config), config) == []
