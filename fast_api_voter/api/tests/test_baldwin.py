"""Unit tests for Baldwin's method: repeatedly eliminate the single
lowest-Borda-score candidate (alphabetical tie-break) until one remains. No
dedicated test file existed before (PR #157's mutation-testing baseline
found 24 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_baldwin_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_baldwin_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head.
    assert get_condorcet_winner(ballots) == "A"
    assert get_baldwin_winner(ballots) == "A"


def test_baldwin_resolves_a_top_cycle_by_iterative_single_elimination():
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_baldwin_winner(ballots) == "A"


def test_baldwin_single_and_empty():
    assert get_baldwin_winner([]) is None
    assert get_baldwin_winner([["A"]]) == "A"


def test_compare_all_methods_registers_baldwin():
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
    assert "baldwin" in res["methods"]
    assert res["methods"]["baldwin"]["winner"] in names
