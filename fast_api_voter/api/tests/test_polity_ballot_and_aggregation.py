"""Lot 5 — ballot_and_aggregation.py: the deterministic adapter to engine/utils.

Contract (dev-plan-v0-worktree.md §3, Lot 5): parity with the existing
golden-fixture harness on known cases. Since this module is an adapter, not
a reimplementation, "parity" means (a) every presidential_method the config
schema accepts (config.py's _PRESIDENTIAL_METHODS) actually has a working
dispatch entry here, and (b) known scenarios produce the same winners the
engine/utils test suite already establishes for these algorithms.
"""
import pytest

from api.domain.polity.ballot_and_aggregation import (
    RANKED_METHODS,
    SCORE_METHODS,
    allocate_seats,
    confidence_keep_ratio,
    get_presidential_winner,
    resolve_confidence_vote,
)

# Mirrors config.py's _PRESIDENTIAL_METHODS — a config value with no dispatch
# entry here would be accepted at load time and only blow up mid-run.
_ALL_PRESIDENTIAL_METHODS = {
    "plurality", "two_round", "borda", "irv", "coombs", "bucklin",
    "minimax", "schulze", "kemeny_young", "copeland", "nanson", "baldwin",
    "approval", "simple_score", "star", "median", "majority_judgment",
}


def test_every_configured_presidential_method_has_a_dispatch_entry():
    assert set(RANKED_METHODS) | set(SCORE_METHODS) == _ALL_PRESIDENTIAL_METHODS


def test_every_ranked_method_picks_the_unanimous_winner():
    ballots = [["A", "B", "C"]] * 7 + [["B", "A", "C"]] * 3
    for method in RANKED_METHODS:
        assert get_presidential_winner(ballots, method) == "A", method


def test_every_score_method_picks_the_unanimous_winner():
    ballots = [{"A": 5, "B": 1, "C": 0}] * 10
    for method in SCORE_METHODS:
        assert get_presidential_winner(ballots, method) == "A", method


def test_two_round_resolves_a_case_plurality_gets_wrong():
    # A leads on first preferences (40%) but a majority (60%) ranks B over A.
    ballots = (
        [["A", "C", "B"]] * 40
        + [["B", "C", "A"]] * 35
        + [["C", "B", "A"]] * 25
    )
    assert get_presidential_winner(ballots, "plurality") == "A"
    assert get_presidential_winner(ballots, "two_round") == "B"


def test_empty_ballots_return_no_winner():
    assert get_presidential_winner([], "plurality") is None
    assert get_presidential_winner([], "star") is None


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="unknown presidential_method"):
        get_presidential_winner([["A"]], "coin_flip")


def test_dhondt_matches_hand_computed_allocation():
    # 60/40 split, 10 seats: D'Hondt quotients give party A 6 seats, B 4.
    seats = allocate_seats({"A": 60.0, "B": 40.0}, total_seats=10, method="dhondt", electoral_threshold=0.0)
    assert seats == {"A": 6, "B": 4}
    assert sum(seats.values()) == 10


def test_electoral_threshold_zeroes_out_small_parties():
    seats = allocate_seats(
        {"A": 60.0, "B": 36.0, "C": 4.0}, total_seats=10, method="dhondt", electoral_threshold=0.05
    )
    assert seats["C"] == 0
    assert sum(seats.values()) == 10
    assert set(seats) == {"A", "B", "C"}


def test_all_parties_below_threshold_awards_no_seats():
    seats = allocate_seats({"A": 3.0, "B": 2.0}, total_seats=10, method="dhondt", electoral_threshold=0.9)
    assert seats == {"A": 0, "B": 0}


def test_no_votes_at_all_awards_no_seats():
    seats = allocate_seats({"A": 0.0, "B": 0.0}, total_seats=10, method="dhondt", electoral_threshold=0.05)
    assert seats == {"A": 0, "B": 0}


def test_sainte_lague_and_largest_remainder_allocate_all_seats():
    for method in ("sainte_lague", "largest_remainder"):
        seats = allocate_seats(
            {"A": 55.0, "B": 30.0, "C": 15.0}, total_seats=20, method=method, electoral_threshold=0.05
        )
        assert sum(seats.values()) == 20, method


def test_unknown_seat_allocation_raises():
    with pytest.raises(ValueError, match="unknown seat_allocation"):
        allocate_seats({"A": 1.0}, total_seats=1, method="coin_flip", electoral_threshold=0.0)


# ── confidence vote (v4 Lot 5, §7bis.4a) ──────────────────────────────────

def test_confidence_keep_ratio_is_hand_computed():
    assert confidence_keep_ratio([True, True, True, False]) == 0.75


def test_confidence_keep_ratio_raises_on_empty_ballots():
    with pytest.raises(ValueError, match="no ballots"):
        confidence_keep_ratio([])


def test_confidence_vote_retains_on_a_strict_majority():
    assert resolve_confidence_vote([True, True, False]) is True


def test_confidence_vote_removes_on_an_exact_tie():
    assert resolve_confidence_vote([True, True, False, False]) is False


def test_confidence_vote_removes_on_a_minority_keep():
    assert resolve_confidence_vote([True, False, False]) is False


def test_unanimous_confidence_ballots_resolve_both_ways():
    assert resolve_confidence_vote([True, True, True]) is True
    assert resolve_confidence_vote([False, False, False]) is False


def test_confidence_vote_raises_on_empty_ballots():
    with pytest.raises(ValueError, match="no ballots"):
        resolve_confidence_vote([])


def test_unsupported_confidence_vote_format_raises():
    with pytest.raises(NotImplementedError, match="confidence_vote_format"):
        resolve_confidence_vote([True, False], ballot_format="multi_candidate")
