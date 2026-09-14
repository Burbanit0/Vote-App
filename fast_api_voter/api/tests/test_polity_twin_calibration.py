"""Stage 4's calibration facts and selection rules (api/domain/polity/twin_calibration.py),
checked on hand-built records."""
from __future__ import annotations

from api.domain.polity.twin_calibration import (
    Arm,
    Election,
    Fact,
    FirstChoices,
    fewer_repeat_winners,
    grid,
    mean_turnout,
    partisanship,
    repeat_winner_share,
    retrospective_voting,
    select,
    turnout_band,
    utility_vote_arm,
    utility_vote_choice,
)


def _election(seed: int = 1, tick: int = 0, *, ballots: int = 70, incumbent: int | None = None, record: float | None = None,
              standing: bool = False, winner: int | None = None) -> Election:
    return Election(seed=seed, tick=tick, voters=100, ballots=ballots, incumbent_id=incumbent, incumbent_record=record,
                    incumbent_standing=standing, winner_id=winner)


def test_the_grid_varies_the_first_axis_slowest() -> None:
    assert grid({"a": (1, 2), "b": ("x", "y")}) == [{"a": 1, "b": "x"}, {"a": 1, "b": "y"}, {"a": 2, "b": "x"}, {"a": 2, "b": "y"}]


def test_selection_takes_the_first_qualifying_arm_by_the_key() -> None:
    good = Fact("f", True, "")
    arms = [Arm({"w": 2}, (good,)), Arm({"w": 1}, (good, Fact("g", False, ""))), Arm({"w": 3}, (good,))]
    assert select(arms, key=lambda arm: arm.setting["w"]) == arms[0]
    assert select(arms[1:2], key=lambda arm: 0) is None


def test_retrospective_voting_needs_both_groups_to_have_stood() -> None:
    elections = [
        _election(tick=16, incumbent=5, record=-0.4, standing=True, winner=7),
        _election(tick=32, incumbent=5, record=-0.1, standing=True, winner=5),
        _election(tick=16, seed=2, incumbent=8, record=0.3, standing=True, winner=8),
        _election(tick=20, seed=2, incumbent=9, record=-0.9, standing=False, winner=3),  # barred: not counted
    ]
    fact = retrospective_voting(elections)
    assert fact.holds and fact.reading == "re-elected 1/2 (50.0%) with a record below 0, 1/1 (100.0%) with 0 or more"
    assert not retrospective_voting(elections[:2]).holds  # nobody with a record of 0 or more stood


def test_turnout_is_the_mean_share_of_voters_casting_a_ballot() -> None:
    elections = [_election(ballots=60), _election(ballots=90)]
    assert mean_turnout(elections) == 0.75 and turnout_band(elections).holds
    assert not turnout_band([_election(ballots=95)]).holds
    assert mean_turnout([]) is None and not turnout_band([]).holds


def test_partisanship_must_rise_over_the_zero_arm_and_stay_below_the_ceiling() -> None:
    zero = FirstChoices(eligible=100, own_party_first=70)
    assert FirstChoices(1, 1) + FirstChoices(3, 1) == FirstChoices(4, 2)
    assert partisanship(FirstChoices(100, 80), zero).holds
    assert not partisanship(FirstChoices(100, 92), zero).holds
    assert not partisanship(FirstChoices(100, 70), zero).holds
    assert not partisanship(FirstChoices(), zero).holds


def test_repeat_winners_are_counted_within_each_run_in_tick_order() -> None:
    elections = [_election(tick=16, winner=4), _election(tick=0, winner=4), _election(tick=32, winner=9),
                 _election(tick=20, winner=None), _election(seed=2, tick=0, winner=1), _election(seed=2, tick=16, winner=1)]
    assert repeat_winner_share(elections) == 2 / 3  # seed 1: 4,4,9 ; seed 2: 1,1
    assert fewer_repeat_winners(elections[:3], elections).holds
    assert not fewer_repeat_winners(elections, elections).holds
    assert repeat_winner_share([_election(winner=3)]) is None


def test_a_utility_vote_arm_carries_its_facts_and_orders_by_weight_then_turnout() -> None:
    zero = [_election(tick=0, winner=1), _election(tick=16, winner=1)]
    elections = [_election(tick=0, ballots=66, winner=1), _election(tick=16, ballots=66, incumbent=1, record=0.2, standing=True, winner=2)]
    arm = utility_vote_arm({"partisanship": 0.05, "approval": 0.0}, elections, FirstChoices(10, 8), zero, FirstChoices(10, 7))
    assert [fact.holds for fact in arm.facts] == [False, True, True, True]
    assert arm.measures == {"turnout": 0.66, "own_party_first": 0.8, "repeat_winners": 0.0}
    assert utility_vote_choice(arm) == (0.05, abs(0.66 - 0.675))
    assert utility_vote_choice(Arm({"partisanship": 0.0, "approval": 0.1}, ())) == (0.1, 0.675)
