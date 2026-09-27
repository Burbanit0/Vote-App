"""Unit tests for the cardinal batch: cumulative, maximin (Rawlsian), and Nash
(proportional welfare) -- three ways to aggregate per-voter scores beyond a
plain sum (simple_score) or median."""

from api.engine.utils.simulation_score_utils import (
    get_cumulative_winner,
    get_maximin_score_winner,
    get_nash_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_cumulative_normalises_each_ballots_budget_to_one():
    # Two voters give A their whole (small) budget; one voter gives B a
    # disproportionately large raw score. Cumulative normalises each ballot to
    # a shared 1-point budget, so A's two full-throated ballots (1.0 each)
    # beat B's single ballot (also capped at 1.0) -- a plain raw-score sum
    # would instead crown B (10 points beats 2), which is exactly the
    # scale-invariance cumulative voting is meant to guard against.
    votes = [
        {"A": 1, "B": 0},
        {"A": 1, "B": 0},
        {"A": 0, "B": 10},
    ]
    assert get_cumulative_winner(votes) == "A"


def test_maximin_picks_the_safest_option_not_the_highest_average():
    # A has a high mean (4) but one voter rates it 0 -- a landmine.
    # B is uniformly rated 3 by everyone -- nobody's worst case is bad.
    votes = [
        {"A": 5, "B": 3},
        {"A": 5, "B": 3},
        {"A": 0, "B": 3},
    ]
    assert get_maximin_score_winner(votes) == "B"


def test_nash_punishes_a_single_zero_more_than_a_low_score():
    votes = [
        {"A": 5, "B": 2},
        {"A": 0, "B": 2},
    ]
    assert get_nash_winner(votes) == "B"


def test_cardinal_batch_single_and_empty():
    assert get_cumulative_winner([]) is None
    assert get_maximin_score_winner([]) is None
    assert get_nash_winner([]) is None
    assert get_cumulative_winner([{"A": 3}]) == "A"
    assert get_maximin_score_winner([{"A": 3}]) == "A"
    assert get_nash_winner([{"A": 3}]) == "A"


def test_compare_all_methods_registers_cardinal_batch():
    names = ["A", "B", "C"]
    matrix = {
        i: {n: float(u) for n, u in zip(names, utils)}
        for i, utils in enumerate(
            [(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3 + [(0.5, 0.0, 1.0)] * 2
        )
    }
    res = compare_all_methods(
        [{"id": vid} for vid in matrix],
        [{"name": n} for n in names],
        [],
        override_utilities=matrix,
    )
    for key in ("cumulative", "maximin", "nash"):
        assert key in res["methods"]
        assert res["methods"][key]["winner"] in names
