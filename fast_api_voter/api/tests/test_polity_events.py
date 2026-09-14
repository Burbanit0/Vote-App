"""Typed journal events and their registry (S3.3). See api/domain/polity/events.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.domain.polity.events import (
    ALL_EVENT_TYPES,
    EVENT_TYPES,
    INSTITUTIONAL_EVENT_TYPES,
    LLM_DECISION_EVENT_TYPES,
    OMIT,
    PRESIDENT_ELECTION_OUTCOMES,
    CoalitionFailed,
    ElectionNoWinner,
    LlmProvenance,
    PressureAction,
    validate_event,
)
from api.domain.polity.journal import Journal
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.polity_golden import LLM_DECISION_TYPES, golden_config
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient, _events


def test_every_line_of_both_golden_journals_validates(tmp_path: Path) -> None:
    for llm in (False, True):
        journal = run_simulation(
            golden_config(tmp_path / str(llm), llm=llm), run_id="golden", llm_client=_ElectingFakeLlmClient() if llm else None,
        )
        events = _events(journal)
        assert events
        assert [problem for event in events for problem in validate_event(event)] == []


def test_the_registry_reproduces_the_sets_three_modules_kept_by_hand() -> None:
    # The literal lists run_digest, viz_export and indexer carried before S3.3.
    assert ALL_EVENT_TYPES == {
        "candidacy_declared", "candidacy_considered", "party_nomination_choice", "nomination_lost",
        "campaign_positioning", "clamped_at_bound", "vote_cast", "election_invalidated", "elected",
        "election_no_winner", "mandate_pledge_declared", "snap_election_triggered", "legislative_result",
        "coalition_formed", "coalition_failed", "coalition_decision", "scandal_occurred", "economic_shock_tick",
        "reaction_to_event", "representative_response", "mandate_deviation_recorded", "pressure_action",
        "petition_launched", "petition_signed", "legitimacy_updated", "confidence_vote_triggered",
        "confidence_vote_result", "petition_expired", "recalled", "sortition_rotation", "chamber_deliberation",
    } | {"opinion_dynamics_step", "emotions_updated"}  # S4.3, after the lists were retired
    assert INSTITUTIONAL_EVENT_TYPES == {
        "elected", "election_no_winner", "election_invalidated", "snap_election_triggered", "legislative_result",
        "coalition_formed", "coalition_failed", "petition_launched", "petition_expired", "confidence_vote_triggered",
        "confidence_vote_result", "recalled", "scandal_occurred", "economic_shock_tick",
    }
    assert PRESIDENT_ELECTION_OUTCOMES == {"elected", "election_no_winner", "election_invalidated"}
    assert LLM_DECISION_EVENT_TYPES == set(LLM_DECISION_TYPES)


def test_payload_omits_keys_left_at_omit_and_flattens_provenance() -> None:
    deterministic = PressureAction(target=3, act=4)
    assert deterministic.payload() == {"target": 3, "act": 4}
    llm = PressureAction(target=3, act=1, ctx={"self_gap": 0.2}, provenance=LlmProvenance(0, 1, "abcd"))
    assert llm.payload() == {
        "target": 3, "act": 1, "ctx": {"self_gap": 0.2}, "llm_fallback": 0, "retry_sampling_varied": 1, "llm_call_id": "abcd",
    }
    # None is a value, OMIT is an absence.
    assert CoalitionFailed(coalition=None, seats={1: 3}).payload() == {"coalition": None, "seats": {1: 3}}
    assert ElectionNoWinner(office="president", reason=OMIT).payload() == {"office": "president"}


def test_payload_keys_separate_always_present_from_path_dependent() -> None:
    required, optional = PressureAction.payload_keys()
    assert required == {"target", "act"}
    assert optional == {"ctx", "llm_fallback", "retry_sampling_varied", "llm_call_id"}


def test_provenance_for_a_unit_absent_from_the_maps_is_a_clean_first_attempt() -> None:
    assert LlmProvenance.for_unit({}, {7: True}, {}, 7) == LlmProvenance(0, 1, None)


@pytest.mark.parametrize(
    ("event", "problems"),
    [
        ({"event_type": "pressure_action", "payload": {"target": 1, "act": 2}}, []),
        ({"event_type": "pressure_action", "payload": {"act": 2}}, ["pressure_action: missing payload key 'target'"]),
        ({"event_type": "pressure_action", "payload": {"target": 1, "act": 2, "mood": 3}},
         ["pressure_action: unexpected payload key 'mood'"]),
        ({"event_type": "rain_started", "payload": {}}, ["unknown event_type 'rain_started'"]),
    ],
)
def test_validate_event_names_what_is_wrong(event: dict[str, object], problems: list[str]) -> None:
    assert validate_event(event) == problems


def test_write_event_writes_the_same_line_as_the_dict_it_replaced(tmp_path: Path) -> None:
    typed = PressureAction(target=3, act=1, ctx={"self_gap": 0.2}, provenance=LlmProvenance(0, 0, None))
    with Journal(tmp_path / "typed.jsonl", "run") as journal:
        journal.write_event(tick=2, event=typed, citizen_id=9, motif="301", codebook_version="v1")
    with Journal(tmp_path / "dict.jsonl", "run") as journal:
        journal.write(2, "pressure_action", typed.payload(), citizen_id=9, motif="301", codebook_version="v1")
    assert (tmp_path / "typed.jsonl").read_bytes() == (tmp_path / "dict.jsonl").read_bytes()
    assert json.loads((tmp_path / "typed.jsonl").read_text())["event_type"] == "pressure_action"


def test_every_registered_type_names_itself() -> None:
    assert all(cls.EVENT_TYPE == name for name, cls in EVENT_TYPES.items())
