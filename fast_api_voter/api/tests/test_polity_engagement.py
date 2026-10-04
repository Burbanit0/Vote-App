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
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import utility_ballot
from api.tests.polity_golden import golden_config
from api.tests.test_polity_dynamic_citizens import FELT, MOVING

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
    assert {c.engagement for c in citizens} <= {ACTIVE, DISENGAGED, EXITED}
    assert sum(c.engagement == EXITED for c in citizens) == exited[-1]
