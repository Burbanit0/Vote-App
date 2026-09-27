"""Tests for `bayesian_regret` (api/engine/utils/simulation_metrics.py).

Three call sites used to carry their own copy of this formula — two in
simulation_metrics itself and one in workers_advanced, which rounds to 4 digits
and floors a missing winner at 0.0 instead of None. These pin the shared
behaviour so the two conventions cannot drift apart again.
"""
from api.engine.utils.simulation_metrics import bayesian_regret

VOTERS = [{"id": 0}, {"id": 1}]


def test_zero_when_every_voter_got_their_favourite():
    utilities = {0: {"A": 1.0, "B": 0.2}, 1: {"A": 0.9, "B": 0.1}}
    assert bayesian_regret(utilities, VOTERS, "A") == 0.0


def test_averages_the_utility_each_voter_gave_up():
    # Voter 0 loses 1.0 - 0.2 = 0.8, voter 1 loses 0.9 - 0.1 = 0.8.
    utilities = {0: {"A": 1.0, "B": 0.2}, 1: {"A": 0.9, "B": 0.1}}
    assert bayesian_regret(utilities, VOTERS, "B") == 0.8


def test_a_candidate_missing_from_a_row_counts_as_zero_utility():
    # Voter 1 never rated B: that voter loses their full 0.9, not nothing.
    utilities = {0: {"A": 1.0, "B": 0.2}, 1: {"A": 0.9}}
    assert bayesian_regret(utilities, VOTERS, "B") == round((0.8 + 0.9) / 2, 6)


def test_no_winner_has_no_regret_to_report():
    assert bayesian_regret({0: {"A": 1.0}}, [{"id": 0}], None) is None


def test_ndigits_is_the_callers_choice():
    utilities = {0: {"A": 1.0, "B": 0.123456789}, 1: {"A": 1.0, "B": 0.0}}
    assert bayesian_regret(utilities, VOTERS, "B") == 0.938272
    assert bayesian_regret(utilities, VOTERS, "B", ndigits=4) == 0.9383
