"""Unit tests for Copeland's method: score = pairwise wins minus pairwise
losses, ties broken by total wins then alphabetically. No dedicated test
file existed before (PR #157's mutation-testing baseline found 20 surviving
mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_copeland_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_copeland_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> beats everyone, max score.
    assert get_condorcet_winner(ballots) == "A"
    assert get_copeland_winner(ballots) == "A"


def test_copeland_resolves_a_top_cycle_by_win_loss_score():
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_copeland_winner(ballots) == "A"


def test_copeland_single_and_empty():
    assert get_copeland_winner([]) is None
    assert get_copeland_winner([["A"]]) == "A"


def test_compare_all_methods_registers_copeland():
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
    assert "copeland" in res["methods"]
    assert res["methods"]["copeland"]["winner"] in names
