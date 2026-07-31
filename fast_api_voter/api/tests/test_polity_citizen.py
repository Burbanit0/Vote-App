"""Lot 2 — citizen.py: the Citizen entity + deterministic population generation.

Contract (dev-plan-v0-worktree.md §3, Lot 2): two generations with the same
seed are identical field-for-field.
"""
import pytest

from api.domain.polity.citizen import (
    Office,
    Role,
    _parse_beta_params,
    generate_population,
)
from api.domain.polity.config import load_config


def _citizens_config():
    return load_config().citizens


def test_same_seed_produces_field_for_field_identical_populations():
    config = _citizens_config()
    pop_a = generate_population(config, population_size=50, seed=42)
    pop_b = generate_population(config, population_size=50, seed=42)
    assert pop_a == pop_b


def test_different_seed_produces_a_different_population():
    config = _citizens_config()
    pop_a = generate_population(config, population_size=50, seed=42)
    pop_b = generate_population(config, population_size=50, seed=43)
    assert pop_a != pop_b


def test_population_shape_and_invariants():
    config = _citizens_config()
    pop = generate_population(config, population_size=100, seed=1)
    assert len(pop) == 100
    assert [c.citizen_id for c in pop] == list(range(100))
    for c in pop:
        assert len(c.issue_positions) == config.issue_count
        assert all(0.0 <= x <= 1.0 for x in c.issue_positions)
        assert len(c.issue_priorities) == config.issue_count
        assert pytest.approx(sum(c.issue_priorities), abs=1e-9) == 1.0
        assert 0.0 <= c.blank_threshold <= 1.0
        assert 0.0 <= c.ambition_score <= 1.0
        assert c.role == Role.ELECTOR
        assert c.office == Office.NONE
        assert c.term_end_tick is None
        assert c.party_affiliation is None
        assert c.mandates_served == 0
        assert c.pledged_platform is None
        assert c.revealed_position is None


def test_unsupported_position_dist_raises():
    config = _citizens_config()
    bad = config.__class__(**{**config.__dict__, "position_dist": "gaussian_mixture"})
    with pytest.raises(NotImplementedError, match="position_dist"):
        generate_population(bad, population_size=10, seed=1)


def test_unsupported_priority_dist_raises():
    config = _citizens_config()
    bad = config.__class__(**{**config.__dict__, "priority_dist": "flat"})
    with pytest.raises(NotImplementedError, match="priority_dist"):
        generate_population(bad, population_size=10, seed=1)


def test_parse_beta_params():
    assert _parse_beta_params("beta(3,5)") == (3.0, 5.0)
    assert _parse_beta_params("beta( 2.5 , 8 )") == (2.5, 8.0)


def test_parse_beta_params_rejects_unknown_spec():
    with pytest.raises(ValueError, match="unsupported distribution spec"):
        _parse_beta_params("gaussian(0,1)")
