"""ADR-022 (roadmap 5.1): a term-limited president may refuse to leave; the kernel rolls, and a
president who stays is irregular and cannot be recalled."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.accountability import is_irregular
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import PolityConfigError, RegimeConfig, load_config, validate_config
from api.domain.polity.regime import refusal_probability, refusal_succeeds
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_agents import _AgentFakeClient, _agent_run_config, _turn
from api.tests.test_polity_amendments import _amending

SURE = RegimeConfig(enabled=True, loyalty=0.0, support_weight=0.0, loyalty_weight=100.0, severity_weight=0.0)
DOOMED = dataclasses.replace(SURE, loyalty=1.0)


def test_support_raises_and_loyalty_and_severity_lower_the_chance() -> None:
    base = RegimeConfig(enabled=True)
    assert refusal_probability(0.9, base) > refusal_probability(0.5, base) > refusal_probability(0.2, base)
    assert refusal_probability(0.5, dataclasses.replace(base, loyalty=0.5)) > refusal_probability(0.5, base)
    assert refusal_probability(0.5, dataclasses.replace(base, severity=1.0)) < refusal_probability(0.5, base)
    assert refusal_probability(0.5, dataclasses.replace(base, loyalty=0.5, severity=0.0)) == pytest.approx(0.5)


def test_the_roll_is_the_probability_against_the_stream() -> None:
    hits = sum(refusal_succeeds(0.5, RegimeConfig(enabled=True, loyalty=0.5, severity=0.0), np.random.default_rng(i))[1] for i in range(400))
    assert 150 < hits < 250


def test_holding_office_past_the_limit_is_irregular() -> None:
    citizen = Citizen(citizen_id=0, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.5, mandates_served=2)
    assert [is_irregular(citizen, limit) for limit in (None, 2, 1)] == [False, False, True]


def test_the_act_needs_amendments_and_a_term_limit() -> None:
    config = _regime_config(Path("."), SURE)
    validate_config(config)
    for bad in (
        dataclasses.replace(config, agents=dataclasses.replace(config.agents, amendments=False)),
        dataclasses.replace(config, institutions=dataclasses.replace(config.institutions, president_term_limit=None)),
    ):
        with pytest.raises(PolityConfigError, match="regime.enabled"):
            validate_config(bad)


def _regime_config(output_dir: Path, regime: RegimeConfig) -> Any:
    config = _amending(_agent_run_config(output_dir))
    return dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, duration_years=3),
        institutions=dataclasses.replace(config.institutions, president_term_years=1, president_term_limit=1),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        regime=regime,
    )


class _RefuserClient(_AgentFakeClient):
    def complete_json(self, **kwargs: Any) -> str:
        if kwargs["json_schema"].get("title") != "ActingLeaderTurn":
            return str(super().complete_json(**kwargs))
        return json.dumps(_turn(extra_legal="refuse_to_leave"))


def _run(tmp_path: Path, regime: RegimeConfig) -> list[dict[str, Any]]:
    journal = run_simulation(_regime_config(tmp_path, regime), run_id="regime", llm_client=_RefuserClient())
    return [json.loads(line) for line in journal.read_text().splitlines()]


def _of(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [e for e in events if e["event_type"] == event_type]


def test_a_president_who_refuses_and_wins_the_roll_stays_and_no_election_is_held(tmp_path: Path) -> None:
    events = _run(tmp_path, SURE)
    first, *_ = _of(events, "extra_legal_act")
    assert (first["tick"], first["payload"]["act"], first["payload"]["success"]) == (4, "refuse_to_leave", 1)
    elected = _of(events, "elected")
    assert [e["tick"] for e in elected] == [0] or all(e["tick"] != 4 for e in elected)
    assert all(e["citizen_id"] == first["citizen_id"] for e in elected if e["tick"] < 8)
    assert not [e for e in _of(events, "recalled") if e["citizen_id"] == first["citizen_id"] and e["tick"] >= 4]


def test_a_president_who_refuses_and_loses_the_roll_is_replaced_at_that_election(tmp_path: Path) -> None:
    events = _run(tmp_path, DOOMED)
    first, *_ = _of(events, "extra_legal_act")
    assert (first["tick"], first["payload"]["success"]) == (4, 0)
    [at_four] = [e for e in _of(events, "elected") if e["tick"] == 4]
    assert at_four["citizen_id"] != first["citizen_id"]


def test_the_president_is_told_of_the_act_only_where_the_regime_is_on_and_it_is_not_framed_as_a_good_idea() -> None:
    from api.domain.polity.agents import president_system_prompt
    from api.tests.test_polity_agents import _president

    config = _regime_config(Path("."), SURE)
    on = president_system_prompt(_president(), config)
    assert "refuse_to_leave" in on and "the constitution forbids it" in on and "removed at once" in on
    off = president_system_prompt(_president(), dataclasses.replace(config, regime=RegimeConfig()))
    assert "refuse_to_leave" not in off
