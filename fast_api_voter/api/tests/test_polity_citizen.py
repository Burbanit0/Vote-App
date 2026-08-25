"""Lot 2 — citizen.py: the Citizen entity + deterministic population generation.

Contract (dev-plan-v0-worktree.md §3, Lot 2): two generations with the same
seed are identical field-for-field.
"""
import numpy as np
import pytest

from api.domain.polity.citizen import (
    Office,
    Role,
    _FACTOR_STRUCTURE_N_FACTORS,
    _generate_factor_structure_positions,
    _parse_beta_params,
    generate_population,
)
from api.domain.polity.config import load_config


def _citizens_config():
    return load_config().citizens


def _factor_structure_config():
    config = _citizens_config()
    return config.__class__(**{**config.__dict__, "position_dist": "factor_structure"})


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


# ── factor_structure position_dist (plan-distribution-positions-seeds.md,
#    Phase 2, 2026-08-25) ───────────────────────────────────────────────────

def test_factor_structure_same_seed_produces_field_for_field_identical_populations():
    config = _factor_structure_config()
    pop_a = generate_population(config, population_size=50, seed=42)
    pop_b = generate_population(config, population_size=50, seed=42)
    assert pop_a == pop_b


def test_factor_structure_different_seed_produces_a_different_population():
    config = _factor_structure_config()
    pop_a = generate_population(config, population_size=50, seed=42)
    pop_b = generate_population(config, population_size=50, seed=43)
    assert pop_a != pop_b


def test_factor_structure_population_shape_and_invariants():
    """Same invariant checks as test_population_shape_and_invariants, applied
    to the factor_structure branch -- every non-position field is produced by
    the exact same draw calls regardless of position_dist, so this is mostly
    a regression guard that switching branches doesn't disturb them."""
    config = _factor_structure_config()
    pop = generate_population(config, population_size=100, seed=1)
    assert len(pop) == 100
    assert [c.citizen_id for c in pop] == list(range(100))
    for c in pop:
        assert len(c.issue_positions) == config.issue_count
        assert all(0.0 < x < 1.0 for x in c.issue_positions)  # open interval: sigmoid, never clipped
        assert len(c.issue_priorities) == config.issue_count
        assert pytest.approx(sum(c.issue_priorities), abs=1e-9) == 1.0
        assert 0.0 <= c.blank_threshold <= 1.0
        assert 0.0 <= c.ambition_score <= 1.0
    assert any(c.base_threshold != 0.0 for c in pop)


def test_factor_structure_and_uniform_produce_different_populations_at_the_same_seed():
    """The two branches consume different quantities from rng (factor_structure
    draws loadings + per-citizen factors + noise, not one flat (n, k) array),
    so the RNG state diverges before priorities are even drawn -- nothing
    downstream of the position draw is expected to agree between branches,
    only that each branch is independently reproducible (see the two
    determinism tests above)."""
    uniform_pop = generate_population(_citizens_config(), population_size=50, seed=7)
    factor_pop = generate_population(_factor_structure_config(), population_size=50, seed=7)
    assert uniform_pop != factor_pop


def test_generate_factor_structure_positions_is_deterministic_given_an_rng_state():
    positions_a = _generate_factor_structure_positions(np.random.default_rng(1), n=50, k=20)
    positions_b = _generate_factor_structure_positions(np.random.default_rng(1), n=50, k=20)
    assert np.array_equal(positions_a, positions_b)


def test_generate_factor_structure_positions_shape_and_open_interval():
    positions = _generate_factor_structure_positions(np.random.default_rng(1), n=50, k=20)
    assert positions.shape == (50, 20)
    assert np.all(positions > 0.0) and np.all(positions < 1.0)


def test_factor_structure_correlates_issue_dimensions_unlike_uniform():
    """The whole point of the low-rank factor model (plan §1.3): issues share
    N_FACTORS latent drivers, so distinct issue dimensions should be
    genuinely correlated across the population -- unlike uniform's
    independent per-dimension draw, whose own correlation is noise around 0.
    A population-level statistical property, not something a single-citizen
    unit test could show."""
    factor_positions = _generate_factor_structure_positions(np.random.default_rng(1), n=200, k=20)
    factor_corr = np.corrcoef(factor_positions.T)
    factor_mean_abs_corr = np.mean(np.abs(factor_corr[np.triu_indices(20, k=1)]))

    uniform_positions = np.random.default_rng(1).uniform(0.0, 1.0, size=(200, 20))
    uniform_corr = np.corrcoef(uniform_positions.T)
    uniform_mean_abs_corr = np.mean(np.abs(uniform_corr[np.triu_indices(20, k=1)]))

    assert factor_mean_abs_corr > 5 * uniform_mean_abs_corr
    assert factor_mean_abs_corr > 0.3  # calibration script measured ~0.54 at n=100


def test_factor_structure_marginal_spread_is_not_collapsed_relative_to_uniform():
    """plan §2's own selection criterion: a distribution that eliminates the
    Blank-wins problem by crushing all variability (an artificial consensus)
    is as unrealistic as the problem it would "solve". Uniform[0,1]'s own
    per-dimension stdev is 1/sqrt(12) ~= 0.289; factor_structure should stay
    in the same order of magnitude, not collapse toward 0."""
    positions = _generate_factor_structure_positions(np.random.default_rng(1), n=200, k=20)
    mean_marginal_std = float(np.mean(np.std(positions, axis=0)))
    assert mean_marginal_std > 0.15


def test_factor_structure_n_factors_matches_the_design_docs_two_named_axes():
    """plan §1.3: N_FACTORS=2 is not an arbitrary tuning knob -- it matches
    the "axe économique / axe sociétal" pair design doc §14.2 already names
    for the meso visualization."""
    assert _FACTOR_STRUCTURE_N_FACTORS == 2
