"""Tests for the two cardinal functions test_cardinal_orphans.py doesn't cover.

get_simple_score_winner and calculate_bayesian_regret are the same file's other
zero-dedicated-test rules — outside the six named in test_cardinal_orphans.py, but
in the same file and the same mutmut scope, and just as unasserted before this:
exercised only indirectly through domain workers and route-level TestClient tests
that mutmut's selection list excludes entirely.

Same discipline as test_cardinal_orphans.py: assert on the numbers, not just who won.
"""

import pytest

from api.engine.utils.simulation_score_utils import (
    calculate_bayesian_regret,
    get_simple_score_winner,
)


# ------------------------------------------------------------------ simple score


def test_simple_score_picks_the_highest_average_not_the_highest_total():
    """A: 5 from one voter -> avg 5.0. B: 4+4+4 from three voters -> avg 4.0.
    A has the lower TOTAL (5 vs 12) but wins on average -- pins the /count
    division rather than a raw sum."""
    votes = [{"A": 5, "B": 4}, {"B": 4}, {"B": 4}]
    out = get_simple_score_winner(votes)

    assert out["winner"] == "A"
    assert out["details"] == {"A": 5.0, "B": 4.0}
    assert out["method"] == "Simple Score"


def test_simple_score_orders_every_candidate_by_average_descending():
    votes = [{"A": 1, "B": 5, "C": 3}]
    out = get_simple_score_winner(votes)

    assert list(out["details"].keys()) == ["B", "C", "A"]


def test_simple_score_empty_ballots_have_no_winner():
    out = get_simple_score_winner([])

    assert out["winner"] is None
    assert out["details"] == {}


# -------------------------------------------------------------- bayesian regret


def test_bayesian_regret_zero_for_a_candidate_always_top_rated():
    """A voter's regret for their own most-preferred candidate is always 0 --
    best_utility and current_utility are identical for that candidate on
    that ballot. A is every voter's top choice here, so its average regret
    must be exactly 0, not just the lowest."""
    votes = [{"A": 5, "B": 2}, {"A": 5, "B": 0}]
    out = calculate_bayesian_regret(votes)

    by_name = {r["candidate"]: r for r in out["details"]}
    assert by_name["A"]["avg_regret"] == pytest.approx(0.0)
    assert out["winner"] == "A"


def test_bayesian_regret_scales_the_gap_by_five_not_by_the_raw_scores():
    """One voter: A=5 (their top pick), B=0. Regret for B on this ballot is
    (5/5) - (0/5) = 1.0 -- pins the /5 normalization; without it this would
    read 5.0 instead."""
    votes = [{"A": 5, "B": 0}]
    out = calculate_bayesian_regret(votes)

    by_name = {r["candidate"]: r for r in out["details"]}
    assert by_name["B"]["avg_regret"] == pytest.approx(1.0)
    assert by_name["B"]["avg_utility"] == pytest.approx(0.0)
    assert by_name["A"]["avg_utility"] == pytest.approx(1.0)


def test_bayesian_regret_orders_candidates_by_ascending_regret():
    """Lower regret is better -- the winner is the LOWEST-regret candidate,
    the opposite sort direction from every other rule in this file."""
    votes = [{"A": 5, "B": 3, "C": 0}]
    out = calculate_bayesian_regret(votes)

    assert [r["candidate"] for r in out["details"]] == ["A", "B", "C"]
    assert out["winner"] == "A"


def test_bayesian_regret_treats_a_missing_candidate_as_zero_utility():
    """A ballot that omits a candidate reads their score as 0 (via
    vote.get(candidate, 0)), not as absent from the regret calculation."""
    votes = [{"A": 5}, {"A": 5, "B": 5}]
    out = calculate_bayesian_regret(votes)

    by_name = {r["candidate"]: r for r in out["details"]}
    # ballot 1 has no B: current_utility for B reads 0, best_utility is 5/5=1
    # ballot 2: B ties A at 5, regret 0
    # avg over 2 ballots: (1.0 + 0.0) / 2 = 0.5
    assert by_name["B"]["avg_regret"] == pytest.approx(0.5)


def test_bayesian_regret_empty_ballots_have_no_winner():
    out = calculate_bayesian_regret([])

    assert out["details"] == []
    assert out["winner"] is None
