"""
api.domain.polity.shock — §8's two exogenous generators (v5 Lot 2): a
per-tick scandal-arrival process and an AR(1) economic-climate variable.

Both functions are pure decision/generation primitives, in the same register
as simple_rules.py's `attempt_rupture_candidacy` -- they take no `Journal`,
no `Citizen`, no `tick`, and mutate nothing. The journal-writing
orchestration (finding the sitting president, resolving a scandal's target,
gating `economic_shock_tick`'s anti-saturation write) lives in
run_polity_simulation.py's `_run_exogenous_events`, mirroring the existing
`attempt_rupture_candidacy` (pure) / `_attempt_rupture_candidacies`
(orchestration + IO) split exactly.

Bernoulli-per-tick, not Poisson-lambda: `EventsConfig.scandal_rate_per_tick`
is parsed via `_get_ratio`, hard-constrained to [0, 1] -- the domain of a
per-tick arrival PROBABILITY, not a Poisson intensity (a legal lambda like
2.0 would be rejected by that constraint). The design doc's own "processus
de Poisson" language is not violated by this: a Bernoulli draw per unit tick
is the standard discretization of a Poisson process at unit time resolution
when the rate is expressed as a per-tick probability rather than a
continuous-time lambda.

`economic_shock_step`'s AR(1) variable, `x(t)`, is deliberately left
UNCLAMPED -- mirrors `accountability.update_street_pressure`'s own
"deliberately unclamped" precedent (its own docstring: L's [0,1] clamp
already owns that invariant; double-guarding it here would be redundant).
Nothing in this lot needs `x(t)` bounded; its only consumer is a magnitude
comparison against `economy_shock_threshold`, which works identically
whether `x` is bounded or not.
"""
from __future__ import annotations

import numpy as np

from api.domain.polity.config import EventsConfig


def scandal_arrival(rng: np.random.Generator, config: EventsConfig) -> bool:
    """§8: a Bernoulli-thinned Poisson arrival, gated at the sub-mechanism
    level (config.scandal_enabled) BEFORE any draw -- mirrors
    attempt_rupture_candidacy's own `rupture_path_enabled` gate, and is what
    makes the shipped default (scandal_enabled=False) provably draw zero
    times, not merely "happen not to trigger" this seed."""
    if not config.scandal_enabled:
        return False
    return rng.random() < config.scandal_rate_per_tick


def economic_shock_step(previous_x: float, rng: np.random.Generator, config: EventsConfig) -> float:
    """§8: one AR(1) step, x(t) = phi*x(t-1) + sigma*epsilon(t). Gated at the
    sub-mechanism level (config.economic_shock_enabled) BEFORE any draw --
    same discipline as scandal_arrival above. Disabled: returns previous_x
    unchanged and draws nothing, so the seeded 0.0 the caller starts from
    never moves for the life of a run with economic_shock_enabled=False."""
    if not config.economic_shock_enabled:
        return previous_x
    innovation = rng.normal()
    return config.economy_ar1_phi * previous_x + config.economy_ar1_sigma * innovation
