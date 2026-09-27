"""shock.py — §8's two exogenous generators (v5 Lot 2).

Contract: both generators are gated at the sub-mechanism level BEFORE any
draw, so the shipped default (scandal_enabled=False, economic_shock_enabled=
False) provably consumes zero rng draws -- the same discipline
attempt_rupture_candidacy already established for rupture_path_enabled.
"""
import numpy as np
import pytest

from api.domain.polity.config import EventsConfig
from api.domain.polity.shock import economic_shock_step, scandal_arrival

_EVENTS_CONFIG = EventsConfig(
    enabled=True,
    scandal_enabled=True,
    scandal_rate_per_tick=0.5,
    scandal_magnitude=0.3,
    economic_shock_enabled=True,
    economy_ar1_phi=0.8,
    economy_ar1_sigma=0.1,
    economy_shock_threshold=0.5,
    salience_decay=0.85,
    max_reaction_delta=0.3,
)


def _config(**overrides) -> EventsConfig:
    return EventsConfig(**{**_EVENTS_CONFIG.__dict__, **overrides})


# ── scandal_arrival ────────────────────────────────────────────────────────

def test_scandal_arrival_disabled_never_triggers_and_never_draws():
    config = _config(scandal_enabled=False)
    rng = np.random.default_rng(0)
    for _ in range(5):
        assert scandal_arrival(rng, config) is False
    # No draw consumed: an untouched rng of the same seed gives the same
    # first value as this one, which was never advanced.
    assert rng.random() == np.random.default_rng(0).random()


def test_scandal_arrival_never_triggers_when_rate_is_zero():
    config = _config(scandal_rate_per_tick=0.0)
    rng = np.random.default_rng(0)
    for _ in range(20):
        assert scandal_arrival(rng, config) is False


def test_scandal_arrival_always_triggers_when_rate_is_one():
    config = _config(scandal_rate_per_tick=1.0)
    rng = np.random.default_rng(0)
    for _ in range(20):
        assert scandal_arrival(rng, config) is True


def test_scandal_arrival_still_draws_when_rate_is_zero():
    config = _config(scandal_rate_per_tick=0.0)
    rng = np.random.default_rng(0)
    scandal_arrival(rng, config)
    # The draw WAS consumed (rate=0 is a live outcome, not a disabled
    # sub-mechanism) -- an untouched rng of the same seed now disagrees.
    assert rng.random() != np.random.default_rng(0).random()


# ── economic_shock_step ───────────────────────────────────────────────────

def test_economic_shock_step_disabled_returns_previous_x_unchanged_and_never_draws():
    config = _config(economic_shock_enabled=False)
    rng = np.random.default_rng(0)
    x = 0.42
    for _ in range(5):
        x = economic_shock_step(x, rng, config)
        assert x == 0.42
    assert rng.random() == np.random.default_rng(0).random()


def test_economic_shock_step_with_zero_phi_is_independent_of_previous_x():
    config = _config(economy_ar1_phi=0.0)
    rng_a = np.random.default_rng(0)
    rng_b = np.random.default_rng(0)
    result_low = economic_shock_step(-10.0, rng_a, config)
    result_high = economic_shock_step(10.0, rng_b, config)
    assert result_low == result_high


def test_economic_shock_step_with_zero_sigma_is_exact_geometric_decay():
    # sigma=0.0 makes the innovation term vanish exactly (0.0 * anything ==
    # 0.0), so the series is deterministic despite the rng still being drawn
    # from each step -- pytest.approx absorbs float repeated-multiplication
    # vs. ** rounding noise, not any real nondeterminism.
    config = _config(economy_ar1_sigma=0.0)
    rng = np.random.default_rng(0)
    x = 1.0
    for n in range(1, 6):
        x = economic_shock_step(x, rng, config)
        assert x == pytest.approx(config.economy_ar1_phi ** n)


def test_economic_shock_step_with_zero_sigma_still_draws_the_innovation():
    config = _config(economy_ar1_sigma=0.0)
    rng = np.random.default_rng(0)
    economic_shock_step(0.0, rng, config)
    assert rng.random() != np.random.default_rng(0).random()
