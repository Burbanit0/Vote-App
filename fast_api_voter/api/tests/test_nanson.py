"""Unit tests for Nanson's method (1882): repeatedly eliminate every
candidate whose Borda score is below the mean of the remaining candidates.
No dedicated test file existed before (PR #157's mutation-testing baseline
found 38 surviving mutants here — the most of any function in this file)."""

from api.engine.utils.simulation_ranked_utils import get_nanson_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_nanson_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head.
    assert get_condorcet_winner(ballots) == "A"
    assert get_nanson_winner(ballots) == "A"


def test_nanson_resolves_a_top_cycle_by_iterative_below_mean_elimination():
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_nanson_winner(ballots) == "A"


def test_nanson_single_and_empty():
    assert get_nanson_winner([]) is None
    assert get_nanson_winner([["A"]]) == "A"


def test_compare_all_methods_registers_nanson():
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
    assert "nanson" in res["methods"]
    assert res["methods"]["nanson"]["winner"] in names
