"""Unit tests for Raynaud's method: repeatedly eliminate the loser of the
single largest pairwise defeat until one candidate remains."""

from api.engine.utils.simulation_ranked_utils import get_raynaud_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_raynaud_resolves_a_cycle_by_removing_the_biggest_defeat_first():
    # A rock-paper-scissors cycle: A>B by 5, B>C by 7, C>A by 1.
    # The single largest defeat is B>C (margin 7) -> C is eliminated first.
    # Among the survivors {A, B}, A>B (margin 5) -> B is eliminated.
    # A is left standing, even though no Condorcet winner exists.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_raynaud_winner(ballots) == "A"


def test_raynaud_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> Condorcet winner.
    assert get_condorcet_winner(ballots) == "A"
    assert get_raynaud_winner(ballots) == "A"


def test_raynaud_single_and_empty():
    assert get_raynaud_winner([]) is None
    assert get_raynaud_winner([["A"]]) == "A"


def test_compare_all_methods_registers_raynaud():
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
    assert "raynaud" in res["methods"]
    assert res["methods"]["raynaud"]["winner"] in names
