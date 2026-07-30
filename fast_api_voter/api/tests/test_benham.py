"""Unit tests for Benham's method (Condorcet-IRV): at each round, elect the
Condorcet winner among the remaining candidates if one exists, otherwise run
one IRV elimination round and repeat."""

from api.engine.utils.simulation_ranked_utils import get_benham_winner, get_condorcet_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_benham_elects_the_condorcet_winner_immediately_no_elimination_needed():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> Condorcet winner.
    assert get_condorcet_winner(ballots) == "A"
    assert get_benham_winner(ballots) == "A"


def test_benham_falls_back_to_irv_elimination_on_a_cycle():
    # Rock-paper-scissors cycle: no Condorcet winner among {A, B, C}.
    # First preferences: A=6, B=4, C=3 -> C (fewest) is eliminated.
    # Among the survivors {A, B}: A beats B 9-4 (the 3 ex-C ballots [C,A,B]
    # now read [A,B]) -> A is the Condorcet winner of the 2-candidate round.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_benham_winner(ballots) == "A"


def test_benham_single_and_empty():
    assert get_benham_winner([]) is None
    assert get_benham_winner([["A"]]) == "A"


def test_compare_all_methods_registers_benham():
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
    assert "benham" in res["methods"]
    assert res["methods"]["benham"]["winner"] in names
