"""ADR-034: the welfare channel (voters judge the economy) and scripted events (the scenario names its crises)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import (
    _DEFAULT_CONFIG_PATH,
    PolityConfig,
    PolityConfigError,
    ScriptedEvent,
    VoteConfig,
    _parse_scripted_events,
    load_config,
    validate_config,
)
from api.domain.polity.legitimacy import approval
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import (
    GoverningRecord,
    IncumbentRecord,
    PolicyRecord,
    Party,
    candidate_utility,
    choose_party,
    policy_gain,
    weighted_distance,
)

RAW = yaml.safe_load(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def _citizen(cid: int, position: float = 0.5, threshold: float = 0.4, party: int | None = None, **overrides: Any) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=(position,), issue_priorities=(1.0,), blank_threshold=threshold,
                   ambition_score=0.5, party_affiliation=party, pledged_platform=(position,), **overrides)


def _vote(**weights: float) -> VoteConfig:
    neutral = {"partisanship": 0.0, "approval": 0.0, "valence": 0.0, "policy_retrospection": 0.0, "approval_party_carryover": 0.5}
    return dataclasses.replace(load_config().vote, **{**neutral, **weights})


# ── config ────────────────────────────────────────────────────────────────

def test_the_welfare_settings_ship_neutral() -> None:
    config = load_config()
    assert config.vote.economic_voting == 0.0 and config.events.scripted == ()


def test_scripted_events_are_parsed_sorted_and_checked_against_the_run() -> None:
    last = RAW["run"]["duration_years"] * RAW["run"]["ticks_per_year"]
    parsed = _parse_scripted_events(
        {"scripted": [{"tick": 9, "kind": "economic_shock", "magnitude": -0.6}, {"tick": 3, "kind": "scandal"}, {"tick": last, "kind": "scandal"}]}, RAW,
    )
    assert parsed == (ScriptedEvent(3, "scandal"), ScriptedEvent(9, "economic_shock", -0.6), ScriptedEvent(last, "scandal"))
    for entry, match in (
        ({"tick": 3, "kind": "coup"}, "kind"),
        ({"tick": last + 1, "kind": "scandal"}, "tick"),
        ({"tick": -1, "kind": "scandal"}, "tick"),
        ({"tick": True, "kind": "scandal"}, "tick"),
        ({"tick": 3, "kind": "scandal", "magnitude": 0.2}, "takes no magnitude"),
        ({"tick": 3, "kind": "economic_shock"}, "magnitude"),
        ({"tick": 3, "kind": "economic_shock", "magnitude": 0}, "magnitude"),
        ({"tick": 3}, "expected a mapping"),
        ({"tick": 3, "kind": "scandal", "extra": 1}, "expected a mapping"),
        ("scandal at 3", "expected a mapping"),
    ):
        with pytest.raises(PolityConfigError, match=match):
            _parse_scripted_events({"scripted": [entry]}, RAW)


def test_a_disabled_mechanism_stays_disabled_scripted_or_not_and_economic_voting_needs_an_economy(flagship: Any, tmp_path: Path) -> None:
    base = _twin(flagship, tmp_path)  # the scenario profile: scandals and economic shocks on, everything they need on
    scandal, shock = ScriptedEvent(2, "scandal"), ScriptedEvent(3, "economic_shock", -0.5)
    validate_config(dataclasses.replace(base, events=dataclasses.replace(base.events, scripted=(scandal, shock)),
                                        vote=dataclasses.replace(base.vote, economic_voting=1.0)))
    only_shock = dataclasses.replace(base.events, scandal_enabled=False, scripted=(scandal,))
    with pytest.raises(PolityConfigError, match="scandal_enabled"):
        validate_config(dataclasses.replace(base, events=only_shock))
    only_scandal = dataclasses.replace(base.events, economic_shock_enabled=False, scripted=(shock,))
    with pytest.raises(PolityConfigError, match="economic_shock_enabled"):
        validate_config(dataclasses.replace(base, events=only_scandal))
    no_economy = dataclasses.replace(base.events, economic_shock_enabled=False)
    with pytest.raises(PolityConfigError, match="economic_voting"):
        validate_config(dataclasses.replace(base, events=no_economy, vote=dataclasses.replace(base.vote, economic_voting=1.0)))


# ── the vote ──────────────────────────────────────────────────────────────

def _incumbent(party: int | None, economy: float, policy: bool = False) -> IncumbentRecord:
    record = PolicyRecord(then=(0.0,), now=(0.2,), economy=economy) if policy else PolicyRecord(then=(), now=(), economy=economy)
    return IncumbentRecord(citizen_id=0, party=party, record=0.0, policy=record)


def test_the_economy_rewards_the_incumbent_in_good_times_and_punishes_them_in_bad_the_same_for_every_voter() -> None:
    president, partner, rival = _citizen(0, 0.5, party=1), _citizen(1, 0.5, party=1), _citizen(2, 0.5, party=2)
    near, far = _citizen(10, 0.5), _citizen(11, 0.9)
    vote = _vote(economic_voting=2.0)
    for voter in (near, far):
        base = candidate_utility(voter, president, _vote(), _incumbent(1, 0.0))
        assert candidate_utility(voter, president, vote, _incumbent(1, 0.3)) == pytest.approx(base + 2.0 * 0.3)
        assert candidate_utility(voter, president, vote, _incumbent(1, -0.3)) == pytest.approx(base - 2.0 * 0.3)
    assert candidate_utility(near, partner, vote, _incumbent(1, 0.3)) == pytest.approx(
        candidate_utility(near, partner, _vote(), _incumbent(1, 0.0)) + 0.5 * 2.0 * 0.3)  # the incumbent's party shares it
    assert candidate_utility(near, rival, vote, _incumbent(1, 0.3)) == candidate_utility(near, rival, _vote(), None)  # a rival does not


def test_the_economic_term_is_exactly_zero_without_a_weight_without_a_record_and_beside_a_policy_record() -> None:
    voter, president = _citizen(10), _citizen(0, 0.5, party=1)
    plain = candidate_utility(voter, president, _vote(), None)
    assert candidate_utility(voter, president, _vote(), _incumbent(1, 0.5)) == plain  # no weight
    assert candidate_utility(voter, president, _vote(economic_voting=3.0), None) == plain  # no record
    assert candidate_utility(voter, president, _vote(economic_voting=3.0), IncumbentRecord(0, 1, 0.0)) == plain  # no policy record
    both = _vote(economic_voting=3.0, policy_retrospection=2.0)
    with_policy = candidate_utility(voter, president, both, _incumbent(1, 0.1, policy=True))
    assert with_policy == pytest.approx(plain + 2.0 * policy_gain(voter, PolicyRecord((0.0,), (0.2,))) + 3.0 * 0.1)  # the two add
    assert policy_gain(voter, PolicyRecord(then=(), now=(), economy=0.9)) == 0.0  # an economy-only record has no policy to gain from


def test_the_economy_decides_between_two_equally_near_parties_for_the_governing_one() -> None:
    parties = [Party(party_id=1, platform=(0.4,)), Party(party_id=2, platform=(0.6,))]
    voter = _citizen(10, 0.5)
    boom = GoverningRecord(parties=frozenset({1}), policy=PolicyRecord(then=(0.0,), now=(0.0,), economy=0.2))
    bust = GoverningRecord(parties=frozenset({1}), policy=PolicyRecord(then=(0.0,), now=(0.0,), economy=-0.2))
    assert choose_party(voter, parties, boom, 0.0, 1.0) == 1  # good times: the governing party keeps the vote
    assert choose_party(voter, parties, bust, 0.0, 1.0) == 2  # bad times: it loses it
    assert choose_party(voter, parties, bust, 0.0, 0.0) == 1  # no weight: the lowest party id, as before


def test_approval_follows_the_economy_through_the_same_term() -> None:
    president = _citizen(0, 0.5, party=1, revealed_position=(0.5,))
    # Each citizen's distance to the president is just past their tolerance: only good times keep them approving.
    voters = [_citizen(i, 0.5 + 0.45, threshold=0.4) for i in range(1, 11)]
    assert weighted_distance(voters[0], (0.5,)) > voters[0].blank_threshold
    vote = _vote(economic_voting=1.0)
    boom = approval(voters, president, vote, PolicyRecord(then=(), now=(), economy=0.2))
    flat = approval(voters, president, vote, PolicyRecord(then=(), now=(), economy=0.0))
    bust = approval(voters, president, vote, PolicyRecord(then=(), now=(), economy=-0.2))
    assert boom == 1.0 and flat == 0.0 and bust == 0.0


# ── scripted events in a run ──────────────────────────────────────────────

def _twin(flagship: Any, output_dir: Path, scripted: tuple[ScriptedEvent, ...] = (), economic_voting: float = 0.0, years: int = 4) -> PolityConfig:
    config = flagship._flagship_config(
        engine="deterministic", years=years, population=60, seats=9, seed=4, output_dir=output_dir,
        max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    return dataclasses.replace(
        config, events=dataclasses.replace(config.events, scripted=scripted),
        vote=dataclasses.replace(config.vote, economic_voting=economic_voting),
    )


def _events(journal: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in journal.read_text().splitlines()]


def test_a_scripted_scandal_and_shock_happen_at_their_tick_and_leave_the_random_stream_alone(flagship: Any, tmp_path: Path) -> None:
    schedule = (ScriptedEvent(5, "scandal"), ScriptedEvent(9, "economic_shock", -0.8))
    scripted = run_simulation(_twin(flagship, tmp_path / "scripted", schedule), run_id="run")
    plain = run_simulation(_twin(flagship, tmp_path / "plain"), run_id="run")
    events = _events(scripted)
    assert [e["tick"] for e in events if e["event_type"] == "scandal_occurred" and e["tick"] == 5] == [5]
    shock = [e for e in events if e["event_type"] == "economic_shock_tick" and e["tick"] == 9]
    assert shock and shock[0]["payload"]["x"] < -0.5  # the impulse crossed the "major shock" threshold
    # The AR(1) is linear and the draws are the same, so the whole difference in the economy is the impulse decayed:
    final_with = load_checkpoint(scripted.parent / "checkpoint.json").state.economy_x
    final_without = load_checkpoint(plain.parent / "checkpoint.json").state.economy_x
    ticks = 4 * 4
    phi = load_config().events.economy_ar1_phi
    assert final_with - final_without == pytest.approx(-0.8 * phi ** (ticks - 9))


def test_a_recession_before_an_election_costs_the_incumbent_approval_only_when_voters_judge_the_economy(flagship: Any, tmp_path: Path) -> None:
    recession = (ScriptedEvent(13, "economic_shock", -0.9),)

    def mean_approval(label: str, voting: float) -> float:
        journal = run_simulation(_twin(flagship, tmp_path / label, recession, voting, years=5), run_id="run")
        readings = [e["payload"]["approval"] for e in _events(journal)
                    if e["event_type"] == "legitimacy_updated" and 13 <= e["tick"] <= 15 and "approval" in e["payload"]]
        assert readings
        return sum(readings) / len(readings)

    ignoring, judging = mean_approval("ignoring", 0.0), mean_approval("judging", 3.0)
    assert judging < ignoring  # the same recession, the same seed: only the weight differs


def test_economic_voting_at_zero_leaves_the_run_exactly_as_it_was(flagship: Any, tmp_path: Path) -> None:
    before = run_simulation(_twin(flagship, tmp_path / "a"), run_id="run")
    again = run_simulation(_twin(flagship, tmp_path / "b", economic_voting=0.0), run_id="run")
    assert before.read_bytes() == again.read_bytes()
