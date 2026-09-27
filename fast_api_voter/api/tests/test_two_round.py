"""Unit tests for the Two-Round System: outright majority wins round 1,
otherwise the top two by first-choice go to a runoff decided by whichever of
the two is preferred on each ballot. No dedicated test file existed before
(PR #157's mutation-testing baseline found 27 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_two_round_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_two_round_majority_winner_decided_in_round_one():
    ballots = [["A", "B", "C"]] * 6 + [["B", "C", "A"]] * 2 + [["C", "A", "B"]] * 2
    # A has 6/10 first-choice votes -- an outright majority, no runoff needed.
    assert get_two_round_winner(ballots) == "A"


def test_two_round_runoff_between_top_two_first_choice_candidates():
    ballots = [["A", "B", "C"]] * 4 + [["B", "C", "A"]] * 3 + [["C", "A", "B"]] * 3
    # No majority (4/10 for the leader A). Top two by first choice: A(4), B(3)
    # -- C's 3 ballots rank A over B, so in the runoff A picks up all of C's
    # transferred votes: A=4+3=7 vs B=3.
    assert get_two_round_winner(ballots) == "A"


def test_two_round_single_and_empty():
    assert get_two_round_winner([]) is None
    assert get_two_round_winner([["A"]]) == "A"


def test_compare_all_methods_registers_two_round():
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
    assert "two_round" in res["methods"]
    assert res["methods"]["two_round"]["winner"] in names
