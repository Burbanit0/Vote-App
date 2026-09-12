"""Unit tests for Approval Voting (default mode: approve each ballot's top-2
ranked candidates). No dedicated test file existed before (PR #157's
mutation-testing baseline found 15 surviving mutants here).

The sincere-threshold mode (each voter approves every candidate whose
utility exceeds their own mean utility) and its `get_approval_winner_sincere`
convenience wrapper were entirely untested until CODE_AUDIT.md §7 item 6
flagged them -- the `utility_scores=` branch inside `get_approval_winner`
(lines ~276-298) had zero coverage of its own, not just the wrapper."""

from api.engine.utils.simulation_ranked_utils import (
    get_approval_winner,
    get_approval_winner_sincere,
    get_plurality_winner,
)
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


class TestGetApprovalWinnerSincere:
    """Sincere-threshold approval: each voter approves every candidate whose
    utility exceeds their own mean utility, rather than a fixed top-N count."""

    def test_sincere_majority_case(self):
        utility_scores = {
            "v1": {"A": 10, "B": 5, "C": 0},
            "v2": {"A": 10, "B": 5, "C": 0},
            "v3": {"A": 0, "B": 5, "C": 10},
        }
        # v1/v2's mean is 5 -> only A (10 > 5) is approved, B ties the mean
        # and is not counted. v3 approves only C by the same logic.
        assert get_approval_winner_sincere(utility_scores) == "A"

    def test_sincere_flips_the_winner_relative_to_default_top_two(self):
        """B1's second choice (B) barely clears last place, so sincere
        threshold voters withhold approval from it -- unlike the default
        top-2 heuristic, which always credits a ballot's 2nd choice
        regardless of how close it is to being a non-choice.

        Sincere: b1 (x3) approves only A (mean 3.67, only 10 clears it); b2
        (x2) approves B and C (mean 6.33, both 10 and 9 clear it).
        Totals: A=3, B=2, C=2 -> winner A.

        Default top-2 on the equivalent rankings: b1 approves A,B; b2
        approves B,C. Totals: A=3, B=5, C=2 -> winner B.
        """
        utility_scores = {
            "b1_1": {"A": 10, "B": 1, "C": 0},
            "b1_2": {"A": 10, "B": 1, "C": 0},
            "b1_3": {"A": 10, "B": 1, "C": 0},
            "b2_1": {"A": 0, "B": 10, "C": 9},
            "b2_2": {"A": 0, "B": 10, "C": 9},
        }
        assert get_approval_winner_sincere(utility_scores) == "A"

        rankings = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 2
        assert get_approval_winner(rankings) == "B"

    def test_sincere_voter_with_uniform_utility_approves_nobody(self):
        """A voter perfectly indifferent between all candidates has every
        candidate exactly AT their mean, so `score > threshold` is false for
        all of them -- that voter contributes zero approvals, but the
        election still resolves from the other voter's genuine preference."""
        utility_scores = {
            "flat": {"A": 5, "B": 5, "C": 5},
            "decisive": {"A": 10, "B": 0, "C": 0},
        }
        assert get_approval_winner_sincere(utility_scores) == "A"

    def test_sincere_all_voters_flat_yields_no_approvals(self):
        utility_scores = {
            "v1": {"A": 5, "B": 5},
            "v2": {"A": 3, "B": 3},
        }
        assert get_approval_winner_sincere(utility_scores) is None

    def test_sincere_empty(self):
        assert get_approval_winner_sincere({}) is None

    def test_sincere_defensive_branches_on_get_approval_winner_directly(self):
        """`get_approval_winner_sincere` always builds a votes list whose
        voter_ids exactly match `utility_scores`' keys, so it can never itself
        exercise `get_approval_winner`'s defensive handling of a ballot whose
        voter_id is missing from `utility_scores`, or a voter with an empty
        utility dict. Both are still reachable through `get_approval_winner`
        directly (e.g. a caller assembling ballots and utilities separately),
        so they get their own coverage here."""
        votes = [{"voter_id": "ghost"}, {"voter_id": "v1"}]
        utility_scores = {"v1": {"A": 10, "B": 0}}
        assert get_approval_winner(votes, utility_scores=utility_scores) == "A"

        votes2 = [{"voter_id": "v1"}, {"voter_id": "v2"}]
        utility_scores2: dict = {"v1": {}, "v2": {"A": 10, "B": 0}}
        assert get_approval_winner(votes2, utility_scores=utility_scores2) == "A"


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
