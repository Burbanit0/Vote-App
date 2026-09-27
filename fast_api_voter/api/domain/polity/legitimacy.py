"""api.domain.polity.legitimacy — §7's L(t): deterministic enclave #2 (§7.2).

```
L(t) = decay * L(t-1) + support(t) - ecart(t)
L0   = f(mandate strength)
```

support(t) := (1-decay)*m is the roadmap's own resolution of the design
doc's admitted gap (m = mandate_strength, fixed for a whole term). f is the
identity (initial_legitimacy) -- the only choice under which update_legitimacy,
applied every tick with no special-casing (including the election tick
itself), keeps L(t) == m for the whole term when ecart == 0: L(t-1)=m is
already a fixed point of L(t) = decay*L(t-1) + (1-decay)*m.

Maps onto §7bis.7's per-tick sequencing as steps 4 and 6 only:
1. mandate_deviation                            -- Lot 2
2. awakening gate -> pressure_action             -- Lot 4
3. aggregate petition_pressure/street_pressure   -- Lot 4/5
4. compose_ecart, then update_legitimacy         -- THIS LOT
5. petition signature threshold check            -- Lot 5
6. crosses_floor (§7.2 hard recall)              -- THIS LOT (floor half only;
                                                     Lot 5 adds the
                                                     floor-beats-petition
                                                     priority interaction)
7. representative sees street_pressure(t) next tick -- Lot 6

Since petition_pressure/street_pressure don't exist yet, this lot's only
call site passes literal 0.0 for both. ecart's third, optional term
(passive_erosion_weight * mandate_deviation) IS real this lot -- Lot 2's
mandate_deviation already exists, and the shipped default
(passive_erosion_weight: 0.0) keeps it inert either way.
"""
from __future__ import annotations

from api.domain.polity.config import LegitimacyConfig
from api.domain.polity.simple_rules import ballot_ranks_above_blank


def mandate_strength(ballots: list[list[str]], winner_label: str) -> float:
    """m: fraction of cast ballots ranking `winner_label` above blank --
    method-agnostic across all 13 RANKED_METHODS (run_simulation's own
    top-of-function guard already excludes score-based methods, whose
    ballots aren't list[str])."""
    if not ballots:
        raise ValueError("mandate_strength requires at least one ballot")
    above = sum(1 for ballot in ballots if ballot_ranks_above_blank(ballot, winner_label))
    return above / len(ballots)


def initial_legitimacy(strength: float) -> float:
    """L0 = f(mandate strength); f = identity (see module docstring for why
    this is the only choice making L(t) == m the whole term). Kept a named
    function so a later revision can change f in one place."""
    return strength


def compose_ecart(
    petition_pressure: float,
    street_pressure: float,
    deviation: float,
    *,
    petition_weight: float,
    street_weight: float,
    passive_erosion_weight: float,
) -> float:
    """§7bis.6: ecart(t) = w_pet*petition_pressure + w_mob*street_pressure
    + passive_erosion_weight*deviation. Plain floats, not config objects --
    the three weights live in three different config sections
    (petition.weight_in_ecart, street_pressure.weight_in_ecart,
    legitimacy.passive_erosion_weight)."""
    return (
        petition_weight * petition_pressure
        + street_weight * street_pressure
        + passive_erosion_weight * deviation
    )


def update_legitimacy(previous: float, strength: float, ecart: float, config: LegitimacyConfig) -> float:
    """L(t) = decay*L(t-1) + (1-decay)*m - ecart(t), clamped to [0, 1]."""
    updated = config.decay * previous + (1.0 - config.decay) * strength - ecart
    return max(0.0, min(1.0, updated))


def crosses_floor(legitimacy: float, config: LegitimacyConfig) -> bool:
    """§7.2: strict `<` -- with recall_floor: 0.0 and update_legitimacy's
    [0,1] clamp, this provably never fires (the isolation switch the
    headline "flat at m" test uses to separate that claim from recall)."""
    return legitimacy < config.recall_floor
