"""Lot 9 — metrics.py: the v0 subset of output metrics.

Contract (dev-plan-v0-worktree.md §3, Lot 9): Laakso-Taagepera verified by
hand on a known case (2 parties at 50/50 seats => N = 2.0).
"""
from api.domain.polity.metrics import (
    coalition_lifespans,
    cohabitation_rate,
    consultation_rate,
    effective_number_of_parties,
    is_cohabitation,
    mobilization_rate,
)


# ── effective_number_of_parties ──────────────────────────────────────────

def test_two_parties_at_50_50_gives_exactly_2():
    assert effective_number_of_parties({0: 50, 1: 50}) == 2.0


def test_single_party_gives_1():
    assert effective_number_of_parties({0: 100}) == 1.0


def test_four_equal_parties_gives_4():
    assert effective_number_of_parties({0: 25, 1: 25, 2: 25, 3: 25}) == 4.0


def test_zero_seat_parties_do_not_affect_the_result():
    with_dud = effective_number_of_parties({0: 50, 1: 50, 2: 0})
    without_dud = effective_number_of_parties({0: 50, 1: 50})
    assert with_dud == without_dud


def test_no_seats_at_all_returns_zero():
    assert effective_number_of_parties({0: 0, 1: 0}) == 0.0


def test_more_concentrated_distributions_give_a_lower_number():
    concentrated = effective_number_of_parties({0: 90, 1: 10})
    balanced = effective_number_of_parties({0: 50, 1: 50})
    assert concentrated < balanced


# ── is_cohabitation ───────────────────────────────────────────────────────

def test_cohabitation_when_president_party_outside_the_coalition():
    assert is_cohabitation(president_party_id=3, coalition=[0, 1]) is True


def test_no_cohabitation_when_president_party_is_in_the_coalition():
    assert is_cohabitation(president_party_id=0, coalition=[0, 1]) is False


def test_no_cohabitation_when_presidency_is_vacant():
    assert is_cohabitation(president_party_id=None, coalition=[0, 1]) is False


def test_no_cohabitation_when_coalition_failed():
    assert is_cohabitation(president_party_id=0, coalition=None) is False


# ── cohabitation_rate ─────────────────────────────────────────────────────

def test_cohabitation_rate_is_the_share_of_true_observations():
    assert cohabitation_rate([True, True, False, False]) == 0.5
    assert cohabitation_rate([False, False, False]) == 0.0
    assert cohabitation_rate([True, True]) == 1.0


def test_cohabitation_rate_of_no_observations_is_zero():
    assert cohabitation_rate([]) == 0.0


# ── coalition_lifespans ───────────────────────────────────────────────────

def test_coalition_lifespan_runs_until_the_next_election():
    events = [(8, [0, 1]), (24, [0, 1]), (40, [2])]
    assert coalition_lifespans(events, total_ticks=120) == [16, 16, 80]


def test_coalition_failed_produces_no_lifespan_entry():
    events = [(8, [0, 1]), (24, None), (40, [2])]
    assert coalition_lifespans(events, total_ticks=120) == [16, 80]


def test_no_events_gives_no_lifespans():
    assert coalition_lifespans([], total_ticks=120) == []


# ── mobilization_rate / consultation_rate (v4 Lot 4) ─────────────────────

def test_mobilization_rate_is_participants_over_population():
    assert mobilization_rate(25, 100) == 0.25


def test_mobilization_rate_with_zero_participants_is_zero():
    assert mobilization_rate(0, 100) == 0.0


def test_mobilization_rate_with_zero_population_is_zero():
    assert mobilization_rate(0, 0) == 0.0


def test_consultation_rate_is_consulted_over_population():
    assert consultation_rate(40, 100) == 0.4


def test_consultation_rate_with_zero_consulted_is_zero():
    assert consultation_rate(0, 100) == 0.0


def test_consultation_rate_with_zero_population_is_zero():
    assert consultation_rate(0, 0) == 0.0
