"""Unit tests for Plurality: whoever has the most first-choice votes wins, no
majority required. No dedicated test file existed before (PR #157's
mutation-testing baseline found 16 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_plurality_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_plurality_winner_needs_no_majority():
    ballots = [["A", "B", "C"]] * 3 + [["B", "A", "C"]] * 2 + [["C", "A", "B"]] * 1
    # A has 3/6 first-choice votes -- a plurality, not a majority, still wins.
    assert get_plurality_winner(ballots) == "A"


def test_plurality_ignores_lower_preferences():
    """A candidate ranked second on every ballot (Condorcet-strong) still
    loses to whoever has more raw first-choice votes -- plurality only
    counts the top slot."""
    ballots = [["A", "B", "C"]] * 3 + [["C", "B", "A"]] * 2
    assert get_plurality_winner(ballots) == "A"


def test_plurality_single_and_empty():
    assert get_plurality_winner([]) is None
    assert get_plurality_winner([["A"]]) == "A"


def test_compare_all_methods_registers_plurality():
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
    assert "plurality" in res["methods"]
    assert res["methods"]["plurality"]["winner"] in names
