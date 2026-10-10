"""ADR-021 (roadmap 4.4): citizens give up. Engagement follows anger with hysteresis; a disengaged or
exited citizen neither votes nor signs, and exit is final."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import ACTIVE, DISENGAGED, EXITED, Citizen
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.emotions import engagement_after, update_engagement
from api.domain.polity.journal import Journal
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import _hold_legislative_election, _run_accountability_phase, run_simulation
from api.domain.polity.simple_rules import utility_ballot
from api.tests.polity_golden import golden_config
from api.tests.test_polity_dynamic_citizens import FELT, MOVING
from api.tests.test_polity_run_simulation import _config_with_legitimacy_enabled, _legitimacy_test_citizen

GIVING_UP = dataclasses.replace(FELT, disengage_anger=0.2, return_anger=0.05, exit_anger=0.6)


def _citizen(cid: int, anger: float, engagement: str | None = None) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5,
                   ambition_score=0.5, anger=anger, engagement=engagement, pledged_platform=(0.5,))


def test_engagement_follows_anger_with_hysteresis_and_exit_is_final() -> None:
    walk = [(0.1, ACTIVE), (0.3, DISENGAGED), (0.1, DISENGAGED), (0.04, ACTIVE), (0.7, EXITED), (0.0, EXITED)]
    state: str | None = None
    for anger, expected in walk:
        state = engagement_after(state, anger, GIVING_UP)
        assert state == expected
    assert engagement_after(ACTIVE, 1.0, dataclasses.replace(GIVING_UP, exit_anger=0.0)) == DISENGAGED


def test_a_disengaged_citizen_stays_home_and_the_update_counts_the_states() -> None:
    citizens = [_citizen(0, 0.0), _citizen(1, 0.3), _citizen(2, 0.9)]
    assert update_engagement(citizens, GIVING_UP) == {DISENGAGED: 1, EXITED: 1}
    candidate = _citizen(9, 0.0)
    vote = load_config().vote
    assert [utility_ballot(c, [candidate], vote) is None for c in citizens] == [False, True, True]


def test_a_disengaged_or_exited_citizen_casts_no_legislative_vote_either(tmp_path: Path) -> None:
    citizens = [_citizen(0, 0.0), _citizen(1, 0.0, ACTIVE), _citizen(2, 0.3, DISENGAGED), _citizen(3, 0.9, EXITED)]
    path = tmp_path / "events.jsonl"
    with Journal(path, "run") as journal:
        _, votes = _hold_legislative_election(citizens, [Party(0, (0.5,))], load_config(), journal, 8)
    assert votes == {0: 2.0}
    assert _events(path)[0]["payload"] == {"seats": {"0": 100}, "votes": {"0": 2.0}, "blank_count": 0, "abstained": 2}

    with Journal(tmp_path / "all.jsonl", "run") as journal:
        _hold_legislative_election(citizens[:2], [Party(0, (0.5,))], load_config(), journal, 8)
    assert "abstained" not in _events(tmp_path / "all.jsonl")[0]["payload"]  # no one stayed home: the key is absent

    with Journal(tmp_path / "none.jsonl", "run") as journal:  # everyone gave up: no seats, no crash
        assert _hold_legislative_election(citizens[2:], [Party(0, (0.5,))], load_config(), journal, 8) == ({0: 0}, {0: 0.0})
    assert _events(tmp_path / "none.jsonl")[0]["payload"]["abstained"] == 2


def _petitioned_president(tmp_path: Path, voters: list[Citizen], *, holder_engagement: str | None = None) -> list[dict[str, Any]]:
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config, run=dataclasses.replace(config.run, population_size=1 + len(voters)),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position, holder.engagement = (0.5,), holder_engagement
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset(v.citizen_id for v in voters)
    with Journal(tmp_path / "events.jsonl", "run") as journal:
        _run_accountability_phase([holder, *voters], config, journal, tick=3)
    return _events(tmp_path / "events.jsonl")


def test_those_who_gave_up_cast_no_confidence_ballot(tmp_path: Path) -> None:
    def voter(cid: int, position: float, engagement: str | None = None) -> Citizen:
        return Citizen(citizen_id=cid, issue_positions=(position,), issue_priorities=(1.0,), blank_threshold=0.1,
                       ambition_score=0.5, engagement=engagement)

    # The president and two others keep; two would remove but gave up -- counted, they would make it 3 of 5 ballots.
    voters = [voter(1, 0.5), voter(2, 0.5), voter(3, 0.0, DISENGAGED), voter(4, 0.0, EXITED)]
    result = next(e for e in _petitioned_president(tmp_path, voters) if e["event_type"] == "confidence_vote_result")
    assert (result["payload"]["ballots"], result["payload"]["keep"], result["payload"]["retained"]) == (3, 3, True)


def test_with_no_one_left_to_vote_the_confidence_vote_is_not_held(tmp_path: Path) -> None:
    gone = [Citizen(citizen_id=i, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.1,
                    ambition_score=0.5, engagement=EXITED) for i in (1, 2)]
    events = _petitioned_president(tmp_path, gone, holder_engagement=DISENGAGED)
    assert not [e for e in events if e["event_type"].startswith("confidence_vote")]


def test_the_rules_want_ordered_anger_thresholds_and_emotions_on() -> None:
    config = load_config()
    on = dataclasses.replace(config, emotions=GIVING_UP, awakening=dataclasses.replace(config.awakening, enabled=True))
    validate_config(on)
    for bad in (dataclasses.replace(GIVING_UP, return_anger=0.3), dataclasses.replace(GIVING_UP, exit_anger=0.1),
                dataclasses.replace(GIVING_UP, enabled=False)):
        with pytest.raises(PolityConfigError, match="disengage_anger"):
            validate_config(dataclasses.replace(on, emotions=bad))


def _events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_run_where_anger_makes_citizens_give_up_journals_it_and_cuts_turnout(tmp_path: Path) -> None:
    def run(name: str, emotions: Any) -> Path:
        base = golden_config(tmp_path / name, llm=False)
        config = dataclasses.replace(
            base, dynamics=MOVING, emotions=emotions,
            institutions=dataclasses.replace(base.institutions, president_term_years=1),
        )
        return run_simulation(config, run_id="run")

    calm, angry = run("calm", dataclasses.replace(FELT, disengage_anger=0.0)), run("angry", GIVING_UP)
    assert not any(e["event_type"] == "engagement_updated" for e in _events(calm))
    shifts = [e["payload"] for e in _events(angry) if e["event_type"] == "engagement_updated"]
    assert shifts and max(s["disengaged"] + s["exited"] for s in shifts) > 0
    exited = [s["exited"] for s in shifts]
    assert exited == sorted(exited)

    def abstained(path: Path) -> int:
        return sum(e["payload"].get("abstained", 0) for e in _events(path) if e["event_type"] == "elected")

    assert abstained(angry) > abstained(calm)
    citizens = load_checkpoint(angry.parent / "checkpoint.json").state.citizens

    # OBS-046: at every vote, those who gave up stay home -- the legislative election and the confidence vote too.
    gave_up, legislative_abstained = 0, []
    for event in _events(angry):
        payload = event["payload"]
        if event["event_type"] == "engagement_updated":
            gave_up = payload["disengaged"] + payload["exited"]
        elif event["event_type"] == "legislative_result":
            assert payload.get("abstained", 0) == gave_up
            assert sum(payload["votes"].values()) + payload["blank_count"] + gave_up == len(citizens)
            legislative_abstained.append(gave_up)
        elif event["event_type"] == "confidence_vote_result":
            assert payload["ballots"] + gave_up == len(citizens)
    assert max(legislative_abstained) > 0
    assert {c.engagement for c in citizens} <= {ACTIVE, DISENGAGED, EXITED}
    assert sum(c.engagement == EXITED for c in citizens) == exited[-1]
