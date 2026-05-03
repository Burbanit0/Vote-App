"""
Unit tests for voting algorithm implementations.

Each class covers one algorithm and verifies:
  - A deterministic clear-winner case
  - Empty-input returning None (or winner=None for score methods)
  - At least one voting-theory scenario (cycle, paradox, or divergence)
  - dict-format ballot acceptance where applicable

No Flask app context is required — all tested functions are pure Python.
"""
import pytest

from app.utils.simulation_ranked_utils import (
    get_approval_winner,
    get_approval_winner_sincere,
    get_borda_winner,
    get_bucklin_winner,
    get_condorcet_winner,
    get_coombs_winner,
    get_irv_winner,
    get_kemeny_young_winner,
    get_minimax_winner,
    get_plurality_winner,
    get_positional_score_winner,
    get_schulze_winner,
    get_two_round_winner,
)
from app.utils.simulation_score_utils import (
    calculate_bayesian_regret,
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_simple_score_winner,
    get_star_voting_winner,
    get_variance_based_winner,
)


# ---------------------------------------------------------------------------
# Shared ballot fixtures
# ---------------------------------------------------------------------------

# 10 voters — A is the dominant Condorcet winner (beats both B and C head-to-head)
# Verified: A vs B → 7:3, A vs C → 7:3, B vs C → 9:1
DOMINANT_A = (
    [["A", "B", "C"]] * 7
    + [["B", "C", "A"]] * 2
    + [["C", "B", "A"]] * 1
)


def _dict_ballots(ballots):
    """Wrap plain-list ballots in the dict format {voter_id, ranking}."""
    return [{"voter_id": i, "ranking": b} for i, b in enumerate(ballots)]


# ============================================================================
# Ranked methods
# ============================================================================


class TestPlurality:
    def test_clear_winner(self):
        assert get_plurality_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_plurality_winner([]) is None

    def test_single_candidate(self):
        assert get_plurality_winner([["A"], ["A"]]) == "A"

    def test_dict_format(self):
        assert get_plurality_winner(_dict_ballots(DOMINANT_A)) == "A"

    def test_plurality_condorcet_divergence(self):
        # A leads first-choice votes but B is the Condorcet winner
        # 3×A>B>C, 2×B>C>A, 2×C>B>A
        # Plurality: A(3), Condorcet: B beats A(4>3), B beats C(5>2) → B
        ballots = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 2 + [["C", "B", "A"]] * 2
        assert get_plurality_winner(ballots) == "A"
        assert get_condorcet_winner(ballots) == "B"


class TestTwoRound:
    def test_majority_first_round(self):
        # A has 7/10 first-choice votes — wins without a runoff
        assert get_two_round_winner(DOMINANT_A) == "A"

    def test_runoff_needed(self):
        # No first-round majority; B wins the runoff over A
        # 4×A>B>C, 4×B>A>C, 3×C>B>A  (majority = 5.5)
        # Runoff: A vs B — C's voters prefer B → B:7, A:4
        ballots = [["A", "B", "C"]] * 4 + [["B", "A", "C"]] * 4 + [["C", "B", "A"]] * 3
        assert get_two_round_winner(ballots) == "B"

    def test_empty_returns_none(self):
        assert get_two_round_winner([]) is None

    def test_dict_format(self):
        assert get_two_round_winner(_dict_ballots(DOMINANT_A)) == "A"


class TestBorda:
    def test_clear_winner(self):
        # A dominates all ballots → highest Borda sum
        # 7×[A,B,C]: A=14, B=7, C=0
        # 2×[B,C,A]: B=4, C=2, A=0
        # 1×[C,B,A]: C=2, B=1, A=0
        # Total: A=14, B=12, C=4 → A wins
        assert get_borda_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_borda_winner([]) is None

    def test_dict_format(self):
        assert get_borda_winner(_dict_ballots(DOMINANT_A)) == "A"

    def test_borda_picks_condorcet_winner_over_plurality_leader(self):
        # Classic divergence: A leads plurality, B is both Condorcet and Borda winner
        # 3×A>B>C: A=6,B=3,C=0; 2×B>C>A: B=4,C=2,A=0; 2×C>B>A: C=4,B=2,A=0
        # Plurality: A(3). Borda totals: A=6, B=9, C=6 → B
        ballots = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 2 + [["C", "B", "A"]] * 2
        assert get_borda_winner(ballots) == "B"
        assert get_plurality_winner(ballots) == "A"


class TestCondorcet:
    def test_clear_winner(self):
        assert get_condorcet_winner(DOMINANT_A) == "A"

    def test_cycle_returns_none(self):
        # A>B, B>C, C>A — classic three-way cycle
        ballots = [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]]
        assert get_condorcet_winner(ballots) is None

    def test_empty_returns_none(self):
        assert get_condorcet_winner([]) is None

    def test_dict_format(self):
        assert get_condorcet_winner(_dict_ballots(DOMINANT_A)) == "A"

    def test_two_candidates(self):
        ballots = [["A", "B"]] * 3 + [["B", "A"]] * 2
        assert get_condorcet_winner(ballots) == "A"


class TestApproval:
    def test_top_n_approval(self):
        # With threshold=2: B appears in top-2 for all 7 voters (total 9), A for 7 only
        # 7×[A,B,C]: approves A,B → A:7, B:7
        # 2×[B,C,A]: approves B,C → B:2, C:2
        # 1×[C,B,A]: approves C,B → B:1, C:1
        # Totals: A=7, B=10, C=3 → B wins
        assert get_approval_winner(DOMINANT_A, approval_threshold=2) == "B"

    def test_sincere_utility_mode(self):
        # Voter 0 and 2 strongly prefer A (above their mean) → A wins
        votes = [
            {"voter_id": 0, "ranking": ["A", "B", "C"]},
            {"voter_id": 1, "ranking": ["B", "A", "C"]},
            {"voter_id": 2, "ranking": ["A", "B", "C"]},
        ]
        utility_scores = {
            0: {"A": 0.9, "B": 0.2, "C": 0.1},  # mean=0.4 → approves A only
            1: {"A": 0.2, "B": 0.8, "C": 0.1},  # mean=0.37 → approves B only
            2: {"A": 0.8, "B": 0.3, "C": 0.1},  # mean=0.4 → approves A only
        }
        # A=2, B=1 → A wins
        assert get_approval_winner(votes, utility_scores=utility_scores) == "A"

    def test_approval_winner_sincere_helper(self):
        utility_scores = {
            0: {"A": 0.9, "B": 0.2},
            1: {"A": 0.8, "B": 0.3},
            2: {"A": 0.1, "B": 0.9},
        }
        assert get_approval_winner_sincere(utility_scores) == "A"

    def test_empty_returns_none(self):
        assert get_approval_winner([]) is None


class TestIRV:
    def test_majority_first_round(self):
        assert get_irv_winner(DOMINANT_A) == "A"

    def test_elimination_needed(self):
        # 5×A>B>C, 4×B>A>C, 3×C>B>A → C eliminated → B:7, A:5 → B wins
        ballots = [["A", "B", "C"]] * 5 + [["B", "A", "C"]] * 4 + [["C", "B", "A"]] * 3
        assert get_irv_winner(ballots) == "B"

    def test_empty_returns_none(self):
        assert get_irv_winner([]) is None

    def test_dict_format(self):
        ballots = [["A", "B", "C"]] * 5 + [["B", "A", "C"]] * 4 + [["C", "B", "A"]] * 3
        assert get_irv_winner(_dict_ballots(ballots)) == "B"

    def test_irv_plurality_divergence(self):
        # A leads first-choice (4) but B wins after C's votes transfer
        # 4×A>C>B, 3×B>C>A, 2×C>B>A
        # IRV: A=4,B=3,C=2 → C eliminated → [C,B,A]→B → B=5,A=4 → B wins
        ballots = [["A", "C", "B"]] * 4 + [["B", "C", "A"]] * 3 + [["C", "B", "A"]] * 2
        assert get_plurality_winner(ballots) == "A"
        assert get_irv_winner(ballots) == "B"


class TestCoombs:
    def test_clear_winner(self):
        # 3×A>B>C, 2×B>A>C, 2×C>B>A
        # Last-place: C:5(from A and B voters), A:2(from C voters)
        # C eliminated → remaining [A,B]: A:3, B:4 → Coombs: A:3 last, B:4 last → A eliminated → B wins
        ballots = [["A", "B", "C"]] * 3 + [["B", "A", "C"]] * 2 + [["C", "B", "A"]] * 2
        assert get_coombs_winner(ballots) == "B"

    def test_empty_returns_none(self):
        assert get_coombs_winner([]) is None

    def test_single_candidate(self):
        assert get_coombs_winner([["A"], ["A"]]) == "A"

    def test_dict_format(self):
        ballots = [["A", "B", "C"]] * 3 + [["B", "A", "C"]] * 2 + [["C", "B", "A"]] * 2
        assert get_coombs_winner(_dict_ballots(ballots)) == "B"


class TestPositionalScore:
    def test_clear_winner(self):
        assert get_positional_score_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_positional_score_winner([]) is None

    def test_single_candidate_single_voter(self):
        assert get_positional_score_winner([["A"]]) == "A"

    def test_dict_format(self):
        assert get_positional_score_winner(_dict_ballots(DOMINANT_A)) == "A"


class TestKemenyYoung:
    def test_clear_winner(self):
        assert get_kemeny_young_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_kemeny_young_winner([]) is None

    def test_two_candidates(self):
        ballots = [["A", "B"]] * 3 + [["B", "A"]] * 2
        assert get_kemeny_young_winner(ballots) == "A"

    def test_agrees_with_condorcet_winner(self):
        # Kemeny-Young must elect the Condorcet winner when one exists
        condorcet = get_condorcet_winner(DOMINANT_A)
        kemeny = get_kemeny_young_winner(DOMINANT_A)
        assert kemeny == condorcet


class TestBucklin:
    def test_winner_at_rank1(self):
        # A has 7/10 first-choice votes (majority=5) → wins at rank 1
        assert get_bucklin_winner(DOMINANT_A) == "A"

    def test_winner_at_rank2(self):
        # 2×A>B>C, 2×B>C>A, 1×C>B>A  (majority=2.5)
        # Rank-1 only: A=2, B=2, C=1 → none > 2.5
        # Rank-2 only: B=2(from A), C=2(from B), B+=1(from C) → B=3 > 2.5 → B wins
        ballots = [["A", "B", "C"]] * 2 + [["B", "C", "A"]] * 2 + [["C", "B", "A"]] * 1
        assert get_bucklin_winner(ballots) == "B"

    def test_empty_returns_none(self):
        assert get_bucklin_winner([]) is None


class TestMinimax:
    def test_clear_winner(self):
        # A beats everyone → A's worst pairwise loss is smallest
        assert get_minimax_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_minimax_winner([]) is None

    def test_agrees_with_condorcet_winner(self):
        condorcet = get_condorcet_winner(DOMINANT_A)
        assert get_minimax_winner(DOMINANT_A) == condorcet


class TestSchulze:
    def test_clear_winner(self):
        assert get_schulze_winner(DOMINANT_A) == "A"

    def test_empty_returns_none(self):
        assert get_schulze_winner([]) is None

    def test_agrees_with_condorcet_winner(self):
        # Schulze is Condorcet-consistent: elects the Condorcet winner when one exists
        condorcet = get_condorcet_winner(DOMINANT_A)
        assert get_schulze_winner(DOMINANT_A) == condorcet


# ============================================================================
# Score methods
# ============================================================================


class TestSimpleScore:
    def test_clear_winner(self):
        scores = [
            {"A": 5, "B": 3, "C": 1},
            {"A": 4, "B": 2, "C": 2},
            {"A": 3, "B": 4, "C": 2},
        ]
        # Averages: A=4, B=3, C=1.67 → A wins
        result = get_simple_score_winner(scores)
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = get_simple_score_winner([])
        assert result["winner"] is None

    def test_response_structure(self):
        result = get_simple_score_winner([{"A": 3, "B": 5}])
        assert "winner" in result
        assert "details" in result
        assert result["winner"] == "B"


class TestStarVoting:
    def test_top_scorer_wins_runoff(self):
        scores = [
            {"A": 5, "B": 3},
            {"A": 4, "B": 2},
            {"A": 3, "B": 4},
        ]
        # A has higher average; also preferred by majority in runoff → A wins
        result = get_star_voting_winner(scores)
        assert result["winner"] == "A"

    def test_runoff_flip(self):
        # B has higher average score but A wins the pairwise runoff
        # 3 voters: A=5, B=4 → prefer A over B in runoff
        # 2 voters: A=1, B=5 → prefer B over A in runoff
        # Averages: A=3.4, B=4.4 → top two: B and A
        # Runoff: 3 prefer A(5>4), 2 prefer B(5>1) → A wins despite lower average
        scores = [{"A": 5, "B": 4, "C": 1}] * 3 + [{"A": 1, "B": 5, "C": 2}] * 2
        result = get_star_voting_winner(scores)
        assert result["winner"] == "A"
        assert result["details"]["first_round"]["B"] > result["details"]["first_round"]["A"]

    def test_single_candidate(self):
        result = get_star_voting_winner([{"A": 3}, {"A": 4}])
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = get_star_voting_winner([])
        assert result["winner"] is None


class TestMedianVoting:
    def test_clear_winner(self):
        scores = [
            {"A": 5, "B": 3},
            {"A": 4, "B": 4},
            {"A": 5, "B": 2},
        ]
        # Medians: A=5, B=3 → A wins
        result = get_median_voting_winner(scores)
        assert result["winner"] == "A"

    def test_resistant_to_outlier(self):
        # B has one extreme high score but a low median; A wins on median
        scores = [{"A": 4, "B": 1}, {"A": 4, "B": 1}, {"A": 4, "B": 5}]
        # Median A=4, Median B=1 → A wins
        result = get_median_voting_winner(scores)
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = get_median_voting_winner([])
        assert result["winner"] is None


class TestMeanMedianHybrid:
    def test_clear_winner(self):
        scores = [{"A": 5, "B": 2}, {"A": 4, "B": 3}, {"A": 4, "B": 3}]
        # Mean A=4.33, B=2.67; Median A=4, B=3 → Combined A=4.17, B=2.83 → A wins
        result = get_mean_median_hybrid_winner(scores)
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = get_mean_median_hybrid_winner([])
        assert result["winner"] is None

    def test_response_structure(self):
        result = get_mean_median_hybrid_winner([{"A": 3, "B": 5}])
        assert "winner" in result
        assert "details" in result


class TestVarianceBased:
    def test_penalises_high_variance(self):
        # A: constant score 4 → mean=4, std=0 → weighted=4
        # B: volatile scores → mean≈4 but std>0 → weighted<4 → A wins
        scores = [
            {"A": 4, "B": 1},
            {"A": 4, "B": 5},
            {"A": 4, "B": 5},
            {"A": 4, "B": 1},
        ]
        result = get_variance_based_winner(scores)
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = get_variance_based_winner([])
        assert result["winner"] is None

    def test_response_structure(self):
        result = get_variance_based_winner([{"A": 3, "B": 5}])
        assert "winner" in result
        assert "details" in result


class TestBayesianRegret:
    def test_lowest_regret_wins(self):
        # A is everyone's top pick → zero regret for A
        scores = [
            {"A": 5, "B": 3, "C": 1},
            {"A": 5, "B": 2, "C": 0},
            {"A": 4, "B": 3, "C": 2},
        ]
        result = calculate_bayesian_regret(scores)
        assert result["winner"] == "A"

    def test_empty_returns_none(self):
        result = calculate_bayesian_regret([])
        assert result["winner"] is None

    def test_response_structure(self):
        result = calculate_bayesian_regret([{"A": 3, "B": 5}])
        assert "winner" in result
        assert "details" in result
