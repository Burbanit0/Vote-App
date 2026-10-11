"""ADR-025 (OBS-047): a president is recalled when the population is against them, not a mobilised few.
Pressure weighs on legitimacy like support (`legitimacy.pressure_like_support`), and legitimacy under the
floor calls a confidence vote that only a majority against the president loses (`legitimacy.floor_calls_vote`)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.citizen import DISENGAGED, Citizen
from api.domain.polity.journal import Journal
from api.domain.polity.legitimacy import update_legitimacy
from api.domain.polity.indexer import index_events
from api.domain.polity.run_digest import _petition_impact
from api.domain.polity.run_polity_simulation import _run_accountability_phase
from api.tests.test_polity_indexer import _config as _indexer_config
from api.tests.test_polity_indexer import _e
from api.tests.test_polity_run_simulation import _config_with_legitimacy_enabled, _legitimacy_test_citizen


def test_pressure_weighs_like_support_and_legitimacy_settles_at_support_minus_pressure(tmp_path: Path) -> None:
    shipped = _config_with_legitimacy_enabled(tmp_path).legitimacy
    alike = dataclasses.replace(shipped, pressure_like_support=True)
    assert update_legitimacy(0.5, 0.8, 0.3, shipped) == pytest.approx(0.9 * 0.5 + 0.1 * 0.8 - 0.3)
    assert update_legitimacy(0.5, 0.8, 0.3, alike) == pytest.approx(0.9 * 0.5 + 0.1 * (0.8 - 0.3))
    settled = {"shipped": 0.76, "alike": 0.76}
    for _ in range(300):  # phase11's median recalled president: support 0.76, pressure 0.16 (OBS-047)
        settled = {"shipped": update_legitimacy(settled["shipped"], 0.76, 0.16, shipped),
                   "alike": update_legitimacy(settled["alike"], 0.76, 0.16, alike)}
    assert settled["shipped"] == 0.0  # m - 10 e, clamped
    assert abs(settled["alike"] - 0.60) < 1e-9  # m - e


def _under_the_floor(tmp_path: Path, voters: list[Citizen], *, calls_vote: bool, petition: bool = False,
                     holder_engagement: str | None = None, holder_out: list[Citizen] | None = None,
                     irregular: bool = False) -> list[dict[str, Any]]:
    """A president whose legitimacy is under the floor (0.1 against 0.2), facing these citizens."""
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config, run=dataclasses.replace(config.run, population_size=1 + len(voters)),
        petition=dataclasses.replace(config.petition, enabled=True),
        legitimacy=dataclasses.replace(config.legitimacy, floor_calls_vote=calls_vote),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.1, mandate_strength_value=0.1)
    holder.revealed_position, holder.engagement = (0.5,), holder_engagement
    if irregular:  # ADR-022: stayed past their final term
        holder.mandates_served = config.institutions.president_term_limit + 1
    if holder_out is not None:
        holder_out.append(holder)
    if petition:
        holder.petition_open_since_tick = 0
        holder.petition_signers = frozenset(v.citizen_id for v in voters)
    path = tmp_path / f"events-{calls_vote}-{petition}-{len(voters)}.jsonl"
    with Journal(path, "run") as journal:
        _run_accountability_phase([holder, *voters], config, journal, tick=5)
    return [json.loads(line) for line in path.read_text().splitlines()]


def _citizen(cid: int, position: float, engagement: str | None = None) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=(position,), issue_priorities=(1.0,), blank_threshold=0.1,
                   ambition_score=0.5, engagement=engagement)


def _kinds(events: list[dict[str, Any]]) -> list[str]:
    return [e["event_type"] for e in events]


def test_the_floor_calls_a_vote_and_a_majority_keeps_the_president(tmp_path: Path) -> None:
    supporters = [_citizen(1, 0.5), _citizen(2, 0.5), _citizen(3, 0.0)]  # with the president, 3 of 4 keep
    events = _under_the_floor(tmp_path, supporters, calls_vote=True)
    assert _kinds(events) == ["legitimacy_updated", "confidence_vote_triggered", "confidence_vote_result"]
    assert events[1]["payload"] == {"office": "president", "cause": "legitimacy_floor"}  # no petition fields
    assert (events[2]["payload"]["retained"], events[2]["payload"]["keep_ratio"]) == (True, 0.75)
    assert events[2]["payload"]["averted_recall"] is False  # that flag stays a petition vote's veto of the floor
    # Without the switch, the same floor recalls outright.
    assert _kinds(_under_the_floor(tmp_path, supporters, calls_vote=False))[-1] == "recalled"


def test_the_floor_calls_a_vote_and_a_majority_against_recalls(tmp_path: Path) -> None:
    opponents = [_citizen(1, 0.0), _citizen(2, 0.0), _citizen(3, 0.5)]  # 2 of 4 keep: a tie removes
    events = _under_the_floor(tmp_path, opponents, calls_vote=True)
    assert _kinds(events)[-1] == "recalled" and events[-1]["payload"]["trigger"] == "confidence_vote"


def test_a_petition_vote_lost_the_same_tick_recalls_without_a_second_vote(tmp_path: Path) -> None:
    opponents = [_citizen(1, 0.0), _citizen(2, 0.0), _citizen(3, 0.0)]
    events = _under_the_floor(tmp_path, opponents, calls_vote=True, petition=True)
    assert _kinds(events).count("confidence_vote_result") == 1
    assert "cause" not in next(e for e in events if e["event_type"] == "confidence_vote_triggered")["payload"]
    assert events[-1]["payload"]["trigger"] == "confidence_vote"


def test_with_no_one_left_to_vote_the_floor_recalls_no_one(tmp_path: Path) -> None:
    gone = [_citizen(1, 0.0, DISENGAGED), _citizen(2, 0.0, DISENGAGED)]
    events = _under_the_floor(tmp_path, gone, calls_vote=True, holder_engagement=DISENGAGED)
    assert _kinds(events) == ["legitimacy_updated"]


def test_a_won_floor_vote_refreshes_the_mandate_and_restores_legitimacy(tmp_path: Path) -> None:
    holders: list[Citizen] = []
    _under_the_floor(tmp_path, [_citizen(1, 0.5), _citizen(2, 0.5), _citizen(3, 0.0)], calls_vote=True, holder_out=holders)
    assert holders[0].mandate_strength == 0.75 and holders[0].legitimacy_capital == 0.75


def test_a_president_who_stayed_faces_no_floor_vote(tmp_path: Path) -> None:
    opponents = [_citizen(1, 0.0), _citizen(2, 0.0), _citizen(3, 0.0)]
    assert _kinds(_under_the_floor(tmp_path, opponents, calls_vote=True, irregular=True)) == ["legitimacy_updated"]


def test_petition_metrics_leave_out_the_votes_the_floor_called() -> None:
    def vote(tick: int, retained: bool, **cause: str) -> list[dict[str, Any]]:
        return [_e(tick, "confidence_vote_triggered", {"office": "president", **cause}, citizen_id=1),
                _e(tick, "confidence_vote_result", {"office": "president", "retained": retained}, citizen_id=1)]

    events = [
        _e(0, "elected", {"office": "president"}, citizen_id=1),
        _e(1, "petition_launched", {"target": 1}, citizen_id=2),
        *vote(2, True),  # the petition's vote, kept
        *vote(5, False, cause="legitimacy_floor"),  # the floor's, lost
        _e(5, "recalled", {"office": "president", "trigger": "confidence_vote"}, citizen_id=1),
    ]
    metrics = index_events(events, _indexer_config(petition_success_rate=True))
    assert (metrics.petition_success_rate, metrics.petition_removal_rate) == (1.0, 0.0)
    assert _petition_impact({"confidence_vote_triggered": [e for e in events if e["event_type"] == "confidence_vote_triggered"]})[
        "confidence_votes"] == 1

