"""Unit tests for Smith-IRV (Tideman's Alternative): restrict to the Smith
set, eliminate the plurality loser(s) among the survivors, and repeat."""

from api.engine.utils.simulation_ranked_utils import (
    get_smith_irv_winner,
    get_irv_winner,
    get_condorcet_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_smith_irv_elects_the_condorcet_winner_immediately():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> Smith set is {A} alone.
    assert get_condorcet_winner(ballots) == "A"
    assert get_smith_irv_winner(ballots) == "A"


def test_smith_irv_resolves_a_top_cycle_via_irv_elimination():
    # No Condorcet winner -> the Smith set is all of {A, B, C} (a genuine
    # cycle), so no candidate is dropped by the Smith-set step alone. First
    # preferences A=6, B=4, C=3 -> C is eliminated. Among the survivors
    # {A, B}, A beats B 9-4, so the next Smith-set pass narrows to {A} alone.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_smith_irv_winner(ballots) == "A"


def test_smith_irv_can_diverge_from_plain_irv_by_protecting_the_smith_set():
    """Found by random search: plain IRV can eliminate its way to a winner
    that plurality-style elimination alone would never protect against
    dropping a Smith-set member early. On this profile IRV and Smith-IRV
    reach different winners once the Smith-set restriction kicks in."""
    ballots = [
        ["C", "D", "B", "A"],
        ["B", "A", "D", "C"],
        ["B", "A", "C", "D"],
        ["A", "D", "C", "B"],
        ["B", "D", "A", "C"],
        ["D", "A", "C", "B"],
        ["D", "B", "C", "A"],
        ["C", "D", "B", "A"],
        ["B", "A", "C", "D"],
        ["A", "D", "B", "C"],
        ["A", "B", "D", "C"],
    ]
    assert get_condorcet_winner(ballots) is None
    assert get_irv_winner(ballots) == "B"
    assert get_smith_irv_winner(ballots) == "D"


def test_smith_irv_single_and_empty():
    assert get_smith_irv_winner([]) is None
    assert get_smith_irv_winner([["A"]]) == "A"


def test_compare_all_methods_registers_smith_irv():
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
    assert "smith_irv" in res["methods"]
    assert res["methods"]["smith_irv"]["winner"] in names
