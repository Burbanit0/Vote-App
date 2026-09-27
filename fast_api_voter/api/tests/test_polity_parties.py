"""Lot 3 — parties.py: k-means party initialization.

Contract (dev-plan-v0-worktree.md §3, Lot 3): party count conforms, platforms
are distinct, and the result is deterministic.
"""
import pytest

from api.domain.polity.citizen import generate_population
from api.domain.polity.config import load_config
from api.domain.polity.parties import initialize_parties


def _population(size=100, seed=1):
    return generate_population(load_config().citizens, population_size=size, seed=seed)


def test_party_count_matches_initial_count():
    parties = initialize_parties(_population(), initial_count=5, seed=42)
    assert len(parties) == 5
    assert [p.party_id for p in parties] == [0, 1, 2, 3, 4]


def test_platforms_are_distinct():
    parties = initialize_parties(_population(), initial_count=5, seed=42)
    platforms = {p.platform for p in parties}
    assert len(platforms) == 5


def test_platform_dimensionality_matches_issue_count():
    config = load_config()
    pop = _population()
    parties = initialize_parties(pop, initial_count=5, seed=42)
    for p in parties:
        assert len(p.platform) == config.citizens.issue_count


def test_same_inputs_are_deterministic():
    pop = _population()
    parties_a = initialize_parties(pop, initial_count=5, seed=42)
    parties_b = initialize_parties(pop, initial_count=5, seed=42)
    assert parties_a == parties_b


def test_different_seed_can_change_the_result():
    pop = _population()
    parties_a = initialize_parties(pop, initial_count=5, seed=42)
    parties_b = initialize_parties(pop, initial_count=5, seed=7)
    assert parties_a != parties_b


def test_rejects_more_parties_than_citizens():
    with pytest.raises(ValueError, match="cannot form"):
        initialize_parties(_population(size=3), initial_count=5, seed=1)


def test_rejects_non_positive_initial_count():
    with pytest.raises(ValueError, match="positive"):
        initialize_parties(_population(), initial_count=0, seed=1)
