"""Lot 2 — citizen.py: the Citizen entity + deterministic population generation.

Contract (dev-plan-v0-worktree.md §3, Lot 2): two generations with the same
seed are identical field-for-field.
"""
import numpy as np
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
        assert 0.0 <= c.base_threshold <= 1.0
        assert c.legitimacy_capital == 0.0
        assert c.mandate_strength == 0.0
    assert any(c.base_threshold != 0.0 for c in pop)


def test_appended_base_threshold_draw_does_not_perturb_pre_existing_fields():
    """v4 Lot 2 DoD: base_threshold is drawn LAST, so every field that
    existed before Lot 2 must stay field-for-field identical at a fixed
    seed. Replicates the pre-Lot-2 draw sequence inline rather than trusting
    generate_population's own internals."""
    config = _citizens_config()
    n, k = 50, config.issue_count
    rng = np.random.default_rng(42)
    positions = rng.uniform(0.0, 1.0, size=(n, k))
    priorities = rng.dirichlet(np.ones(k), size=n)
    blank_a, blank_b = _parse_beta_params(config.blank_threshold_dist)
    blank_thresholds = rng.beta(blank_a, blank_b, size=n)
    ambition_a, ambition_b = _parse_beta_params(config.ambition_dist)
    ambitions = rng.beta(ambition_a, ambition_b, size=n)

    pop = generate_population(config, population_size=n, seed=42)
    for i, citizen in enumerate(pop):
        assert citizen.issue_positions == tuple(float(x) for x in positions[i])
        assert citizen.issue_priorities == tuple(float(x) for x in priorities[i])
        assert citizen.blank_threshold == pytest.approx(float(blank_thresholds[i]))
        assert citizen.ambition_score == pytest.approx(float(ambitions[i]))


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
