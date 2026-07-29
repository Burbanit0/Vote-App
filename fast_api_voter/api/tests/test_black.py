"""Unit tests for Black's method (Duncan Black, 1958): Condorcet winner if one
exists, otherwise Borda."""

from api.engine.utils.simulation_ranked_utils import (
    get_black_winner,
    get_condorcet_winner,
    get_borda_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_black_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head → Condorcet winner.
    assert get_condorcet_winner(ballots) == "A"
    assert get_black_winner(ballots) == "A"


def test_black_falls_back_to_borda_on_a_cycle():
    """A rock-paper-scissors cycle has no Condorcet winner, so Black defers to
    whichever candidate accumulates the most Borda points."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_black_winner(ballots) == get_borda_winner(ballots)


def test_black_single_and_empty():
    assert get_black_winner([]) is None
    assert get_black_winner([["A"]]) == "A"


def test_compare_all_methods_registers_black():
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
    assert "black" in res["methods"]
    assert res["methods"]["black"]["winner"] in names
