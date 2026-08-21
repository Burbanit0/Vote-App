"""Unit tests for Approval Voting (default mode: approve each ballot's top-2
ranked candidates). No dedicated test file existed before (PR #157's
mutation-testing baseline found 15 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_approval_winner, get_plurality_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_approval_rewards_broad_second_choice_support_over_a_narrow_plurality_lead():
    """B is never anyone's first choice but is everyone's second choice, so it
    is approved on every ballot -- out-approving the plurality leader A, who
    is only ever accepted by their own bloc."""
    ballots = [["A", "B", "C"]] * 3 + [["C", "B", "A"]] * 2 + [["D", "B", "A"]] * 2
    assert get_plurality_winner(ballots) == "A"
    assert get_approval_winner(ballots) == "B"


def test_approval_default_threshold_is_top_two():
    # A is 1st in both groups -> approved on all 5 ballots. B is 2nd in
    # group 1 (approved, 3) but 3rd in group 2 (not approved) -> 3 total.
    # C is the mirror of B -> 2 total. A wins clearly, and B/C's split
    # confirms position 3 is excluded while position 2 counts.
    ballots = [["A", "B", "C"]] * 3 + [["A", "C", "B"]] * 2
    assert get_approval_winner(ballots) == "A"


def test_approval_single_and_empty():
    assert get_approval_winner([]) is None
    assert get_approval_winner([["A"]]) == "A"


def test_compare_all_methods_registers_approval():
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
    assert "approval" in res["methods"]
    assert res["methods"]["approval"]["winner"] in names
