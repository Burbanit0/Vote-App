"""Lot 9 — metrics.py: the v0 subset of output metrics.

Contract (dev-plan-v0-worktree.md §3, Lot 9): Laakso-Taagepera verified by
hand on a known case (2 parties at 50/50 seats => N = 2.0).
"""
import pytest

from api.domain.polity.metrics import (
    blank_vote_rate,
    coalition_lifespans,
    cohabitation_rate,
    consultation_rate,
    effective_number_of_parties,
    inaction_rate,
    is_cohabitation,
    lame_duck_deviation_delta,
    mean_legitimacy,
    mobilization_rate,
    petition_success_rate,
    pressure_lever_mix,
    recall_frequency,
    signed_ratio,
    stance_distribution,
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


# ── signed_ratio (v4 Lot 5) ────────────────────────────────────────────────

def test_signed_ratio_hand_cases():
    assert signed_ratio(25, 100) == 0.25
    assert signed_ratio(0, 100) == 0.0
    assert signed_ratio(100, 100) == 1.0


def test_signed_ratio_with_zero_population_is_zero():
    assert signed_ratio(0, 0) == 0.0


# ── mean_legitimacy / recall_frequency (v4 Lot 8) ─────────────────────────

def test_mean_legitimacy_hand_case():
    assert mean_legitimacy([0.4, 0.6]) == 0.5


def test_mean_legitimacy_of_empty_series_is_zero():
    assert mean_legitimacy([]) == 0.0


def test_recall_frequency_is_recalls_over_terms():
    assert recall_frequency(1, 4) == 0.25


def test_recall_frequency_with_zero_terms_is_zero():
    assert recall_frequency(0, 0) == 0.0


# ── inaction_rate (v4 Lot 8) ───────────────────────────────────────────────

def test_inaction_rate_is_inactive_over_consulted():
    assert inaction_rate(3, 12) == 0.25


def test_inaction_rate_with_zero_consulted_is_zero():
    assert inaction_rate(0, 0) == 0.0


# ── pressure_lever_mix (v4 Lot 8) ─────────────────────────────────────────

def test_pressure_lever_mix_hand_case():
    assert pressure_lever_mix([0, 0, 3, 4]) == {0: 0.5, 1: 0.0, 2: 0.0, 3: 0.25, 4: 0.25}


def test_pressure_lever_mix_always_has_all_five_keys():
    assert set(pressure_lever_mix([0]).keys()) == {0, 1, 2, 3, 4}


def test_pressure_lever_mix_of_empty_acts_is_all_zero():
    assert pressure_lever_mix([]) == {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}


# ── petition_success_rate (v4 Lot 8) ──────────────────────────────────────

def test_petition_success_rate_is_triggered_over_launched():
    assert petition_success_rate(2, 8) == 0.25


def test_petition_success_rate_with_no_launches_is_none():
    assert petition_success_rate(0, 0) is None


# ── stance_distribution (v4 Lot 8) ────────────────────────────────────────

def test_stance_distribution_hand_case():
    assert stance_distribution([1, 1, 2, 3]) == {1: 0.5, 2: 0.25, 3: 0.25, 4: 0.0}


def test_stance_distribution_always_has_all_four_keys():
    assert set(stance_distribution([1]).keys()) == {1, 2, 3, 4}


def test_stance_distribution_of_empty_stances_is_all_zero():
    assert stance_distribution([]) == {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}


# ── lame_duck_deviation_delta (v4 Lot 8) ──────────────────────────────────

def test_lame_duck_deviation_delta_hand_case():
    # lame-duck mean 0.6, re-eligible mean 0.2 -> delta 0.4
    assert lame_duck_deviation_delta([0.5, 0.7], [0.1, 0.3]) == pytest.approx(0.4)


def test_lame_duck_deviation_delta_is_none_with_no_lame_duck_term():
    assert lame_duck_deviation_delta([], [0.1, 0.3]) is None


def test_lame_duck_deviation_delta_is_none_with_no_eligible_term():
    assert lame_duck_deviation_delta([0.5], []) is None


def test_lame_duck_deviation_delta_is_none_with_neither():
    assert lame_duck_deviation_delta([], []) is None


# ── blank_vote_rate (v4 Lot 8) ─────────────────────────────────────────────

def test_blank_vote_rate_hand_case():
    assert blank_vote_rate(10, 100) == 0.1


def test_blank_vote_rate_with_zero_ballots_is_zero():
    assert blank_vote_rate(0, 0) == 0.0
