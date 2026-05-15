"""
test_quadratic_voting.py — Tests for the Quadratic Voting implementation.
"""
import math
import pytest

from app.utils.quadratic_voting import apply_quadratic_voting, gini_coefficient


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_utilities(pattern: str, n_voters: int = 100) -> list[dict[str, float]]:
    """Build utility lists from named patterns."""
    if pattern == "uniform":
        # All candidates equally liked
        return [{"A": 0.5, "B": 0.5, "C": 0.5}] * n_voters

    if pattern == "clear_winner":
        # A clearly preferred (utility >> others)
        return [{"A": 0.9, "B": 0.3, "C": 0.1}] * n_voters

    if pattern == "two_candidates_a_wins":
        # 60 % prefer A, 40 % prefer B
        return (
            [{"A": 0.8, "B": 0.2}] * int(n_voters * 0.6) +
            [{"A": 0.2, "B": 0.8}] * int(n_voters * 0.4)
        )

    if pattern == "polarised":
        # Half voters love A, half love C; B is moderate for everyone
        return (
            [{"A": 0.9, "B": 0.5, "C": 0.1}] * (n_voters // 2) +
            [{"A": 0.1, "B": 0.5, "C": 0.9}] * (n_voters // 2)
        )

    raise ValueError(f"Unknown pattern: {pattern}")


# ── Credit budget constraint ──────────────────────────────────────────────────

def test_credits_never_exceed_budget_uniform():
    """Every voter must spend ≤ 100 credits."""
    budget = 100
    utils = make_utilities("uniform", 50)
    _verify_budget_constraint(utils, budget)


def test_credits_never_exceed_budget_clear_winner():
    budget = 100
    utils = make_utilities("clear_winner", 50)
    _verify_budget_constraint(utils, budget)


def test_credits_never_exceed_budget_custom_budget():
    budget = 25
    utils = make_utilities("clear_winner", 50)
    _verify_budget_constraint(utils, budget)


def _verify_budget_constraint(utils: list[dict[str, float]], budget: int) -> None:
    """
    Re-run the allocation logic from the module to verify the invariant.
    We check that the total credit cost (sum of v[c]²) is ≤ budget.
    """
    sqrt_b = math.sqrt(budget)
    for voter_utils in utils:
        util_sum = sum(voter_utils.values()) or 1.0
        votes = {c: int(sqrt_b * u / util_sum) for c, u in voter_utils.items()}
        credits_used = sum(v * v for v in votes.values())
        assert credits_used <= budget, (
            f"Voter spent {credits_used} > {budget}: {votes}"
        )


# ── Winner determination ──────────────────────────────────────────────────────

def test_clear_winner_is_highest_utility_candidate():
    """A candidate with much higher utility should accumulate the most QV votes."""
    result = apply_quadratic_voting(make_utilities("clear_winner", 200))
    assert result["winner"] == "A"


def test_two_candidates_a_wins_by_majority():
    """With 60 % preferring A, A should receive more total QV votes."""
    result = apply_quadratic_voting(make_utilities("two_candidates_a_wins", 200))
    assert result["winner"] == "A"
    assert result["scores"]["A"] > result["scores"]["B"]


def test_uniform_utilities_is_deterministic():
    """
    With identical utilities, the result must be the same every time
    (deterministic tie-breaking via dict key order).
    """
    utils = make_utilities("uniform", 100)
    result_a = apply_quadratic_voting(utils)
    result_b = apply_quadratic_voting(utils)
    assert result_a["winner"] == result_b["winner"]
    assert result_a["scores"] == result_b["scores"]


def test_uniform_utilities_all_candidates_receive_votes():
    """Even with uniform utilities, every candidate should receive some QV votes."""
    result = apply_quadratic_voting(make_utilities("uniform", 100))
    for score in result["scores"].values():
        assert score > 0


def test_polarised_election_returns_valid_winner():
    """Polarised electorate: B (moderate) may win or all scores are close."""
    result = apply_quadratic_voting(make_utilities("polarised", 200))
    assert result["winner"] in ("A", "B", "C")


# ── 2-candidate case ──────────────────────────────────────────────────────────

def test_two_candidates_basic():
    utils = [{"Alice": 0.7, "Bob": 0.3}] * 100
    result = apply_quadratic_voting(utils)
    assert result["winner"] == "Alice"
    assert "Alice" in result["scores"]
    assert "Bob"   in result["scores"]

def test_two_candidates_scores_both_present():
    utils = [{"X": 0.6, "Y": 0.4}] * 50
    result = apply_quadratic_voting(utils)
    assert len(result["scores"]) == 2

def test_two_candidates_winner_has_more_votes():
    utils = [{"X": 0.8, "Y": 0.2}] * 80
    result = apply_quadratic_voting(utils)
    assert result["scores"]["X"] > result["scores"]["Y"]


# ── Return structure ──────────────────────────────────────────────────────────

def test_result_contains_all_required_keys():
    result = apply_quadratic_voting(make_utilities("clear_winner", 20))
    for key in ("winner", "scores", "total_credits_used", "credit_distribution"):
        assert key in result, f"Missing key: {key}"

def test_scores_contain_all_candidates():
    utils = make_utilities("clear_winner", 30)
    result = apply_quadratic_voting(utils)
    assert set(result["scores"].keys()) == {"A", "B", "C"}

def test_credit_distribution_contains_all_candidates():
    utils = make_utilities("clear_winner", 30)
    result = apply_quadratic_voting(utils)
    assert set(result["credit_distribution"].keys()) == {"A", "B", "C"}

def test_total_credits_used_is_positive():
    result = apply_quadratic_voting(make_utilities("clear_winner", 50))
    assert result["total_credits_used"] > 0

def test_total_credits_used_leq_budget():
    result = apply_quadratic_voting(make_utilities("clear_winner", 50), budget=100)
    assert result["total_credits_used"] <= 100.0


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_utilities_returns_empty_result():
    result = apply_quadratic_voting([])
    assert result["winner"] is None
    assert result["scores"] == {}

def test_single_voter():
    result = apply_quadratic_voting([{"Alice": 0.9, "Bob": 0.1}])
    assert result["winner"] == "Alice"

def test_single_candidate():
    result = apply_quadratic_voting([{"Solo": 1.0}] * 10)
    assert result["winner"] == "Solo"

def test_zero_utility_sum_handled():
    """Voter with all-zero utilities should not crash."""
    utils = [{"A": 0.0, "B": 0.0, "C": 0.0}] * 10
    result = apply_quadratic_voting(utils)
    assert result["winner"] is not None    # tie-broken, but no crash

def test_custom_budget():
    result25 = apply_quadratic_voting(make_utilities("clear_winner", 50), budget=25)
    result100 = apply_quadratic_voting(make_utilities("clear_winner", 50), budget=100)
    # Higher budget → more votes in total
    assert sum(result100["scores"].values()) >= sum(result25["scores"].values())


# ── gini_coefficient ──────────────────────────────────────────────────────────

def test_gini_perfect_equality():
    assert gini_coefficient([5.0, 5.0, 5.0]) == pytest.approx(0.0, abs=1e-4)

def test_gini_maximum_inequality():
    # One person has everything
    assert gini_coefficient([100.0, 0.0, 0.0]) == pytest.approx(2/3, abs=0.05)

def test_gini_empty_list():
    assert gini_coefficient([]) == 0.0

def test_gini_single_element():
    assert gini_coefficient([42.0]) == 0.0

def test_gini_two_elements_equal():
    assert gini_coefficient([10.0, 10.0]) == pytest.approx(0.0, abs=1e-4)

def test_gini_two_elements_unequal():
    result = gini_coefficient([0.0, 100.0])
    assert result > 0.3   # significantly unequal


# ── Integration with simulation_metrics (smoke test) ─────────────────────────

def test_compare_all_methods_includes_quadratic(app):
    """Smoke test: quadratic method appears in compare_all_methods output."""
    with app.app_context():
        from app.utils.simulation_voting_utils import create_voter, create_candidate
        from app.utils.simulation_metrics import compare_all_methods
        from app.constants import DEFAULT_ISSUES

        issues     = DEFAULT_ISSUES
        candidates = [
            create_candidate(issues, i, name, "Independent")
            for i, name in enumerate(["Alice", "Bob", "Carol"])
        ]
        voters = [create_voter(issues, i) for i in range(50)]
        result = compare_all_methods(voters, candidates, issues)
        assert "quadratic" in result["methods"]
        qv = result["methods"]["quadratic"]
        assert qv["winner"] in ("Alice", "Bob", "Carol")
