"""Unit tests for Minimax: elect whoever's worst pairwise defeat is smallest
(0 for a Condorcet winner, since they have no defeat at all). No dedicated
test file existed before (PR #157's mutation-testing baseline found 35
surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_minimax_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_minimax_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> zero defeats, minimal max-defeat.
    assert get_condorcet_winner(ballots) == "A"
    assert get_minimax_winner(ballots) == "A"


def test_minimax_resolves_a_top_cycle_by_smallest_worst_defeat():
    """Rock-paper-scissors: A>B by 6-4(margin 2), B>C by ~ , C>A by the
    smallest margin -- the candidate whose single worst loss is least severe
    wins, unlike Split Cycle's whole-cycle discard rule."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_minimax_winner(ballots) == "A"


def test_minimax_single_and_empty():
    assert get_minimax_winner([]) is None
    assert get_minimax_winner([["A"]]) == "A"


def test_compare_all_methods_registers_minimax():
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
    assert "minimax" in res["methods"]
    assert res["methods"]["minimax"]["winner"] in names
