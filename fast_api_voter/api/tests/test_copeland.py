"""Unit tests for Copeland's method: score = pairwise wins minus pairwise
losses, ties broken by total wins then alphabetically. No dedicated test
file existed before (PR #157's mutation-testing baseline found 20 surviving
mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_copeland_winner, get_condorcet_winner
from api.engine.utils.tie_lot import draw
from api.tests.strict_outcomes import possible_winners
from api.engine.utils.simulation_metrics import compare_all_methods


def test_copeland_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> beats everyone, max score.
    assert get_condorcet_winner(ballots) == "A"
    assert get_copeland_winner(ballots) == "A"


def test_copeland_draws_a_top_cycle_by_lot_not_by_name():
    """A beats B, B beats C, C beats A: each has one win and one loss, so nothing in the rule
    separates them, and the seeded lot draws (it was the first name, A, before)."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_copeland_winner(ballots) == draw(["A", "B", "C"])
    assert get_copeland_winner(list(reversed(ballots))) == get_copeland_winner(ballots)


def test_copeland_breaks_a_score_tie_by_total_wins_before_the_lot():
    """B and D both score +1 (wins minus losses), but D wins two duels to B's one: total wins
    decide it, with no draw (D is the only candidate Copeland can elect here)."""
    ballots = [
        ["A", "B", "D", "C"], ["C", "B", "D", "A"], ["B", "A", "D", "C"], ["D", "A", "B", "C"],
        ["D", "C", "B", "A"], ["C", "B", "D", "A"], ["A", "C", "B", "D"], ["D", "A", "B", "C"],
    ]
    assert possible_winners(get_copeland_winner, ballots) == {"D"}


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
