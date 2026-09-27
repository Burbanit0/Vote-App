"""Property-based test — L(t) bounds (§7, legitimacy.py).

update_legitimacy clamps to [0, 1] by construction (legitimacy.py:78-81), so
this isn't hunting for a clamp bug — it's a regression guard that the
compose_ecart -> update_legitimacy pipeline, run over a long, randomly
generated sequence of ticks (varying strength/pressures/deviation and, per
example, a fixed but randomised config), never produces a NaN/inf or an
out-of-band value that the clamp itself would mask a bug behind. Bounds
mirror the domain: strength/pressures/deviation are fractions in [0, 1]
(mandate_strength's own return type), decay and the three ecart weights are
config-authored fractions in [0, 1].
"""
from hypothesis import given, settings, strategies as st

from api.domain.polity.config import LegitimacyConfig
from api.domain.polity.legitimacy import compose_ecart, update_legitimacy

_fraction = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

_configs = st.builds(
    lambda decay, recall_floor, passive_erosion_weight: LegitimacyConfig(
        enabled=True,
        decay=decay,
        recall_floor=recall_floor,
        recall_floor_indexed_on_l0=False,
        recall_cooldown_ticks=4,
        passive_erosion_weight=passive_erosion_weight,
    ),
    decay=_fraction,
    recall_floor=_fraction,
    passive_erosion_weight=_fraction,
)

_tick = st.tuples(_fraction, _fraction, _fraction, _fraction)  # strength, petition, street, deviation
_sequences = st.lists(_tick, min_size=1, max_size=50)


@settings(max_examples=200, deadline=None)
@given(config=_configs, petition_weight=_fraction, street_weight=_fraction, ticks=_sequences)
def test_legitimacy_stays_in_bounds_over_any_tick_sequence(
    config: LegitimacyConfig, petition_weight: float, street_weight: float, ticks: list[tuple[float, float, float, float]]
) -> None:
    legitimacy = 0.5  # arbitrary in-bounds L0 — initial_legitimacy(m) is always in [0, 1] anyway
    for strength, petition_pressure, street_pressure, deviation in ticks:
        ecart = compose_ecart(
            petition_pressure,
            street_pressure,
            deviation,
            petition_weight=petition_weight,
            street_weight=street_weight,
            passive_erosion_weight=config.passive_erosion_weight,
        )
        legitimacy = update_legitimacy(legitimacy, strength, ecart, config)
        assert 0.0 <= legitimacy <= 1.0
