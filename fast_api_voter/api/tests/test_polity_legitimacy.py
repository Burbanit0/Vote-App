"""v4 Lot 3 — legitimacy.py: L(t), mandate strength, the hard recall floor.
Deterministic enclave #2 (§7.2) — hand-built unit cases per function.
"""
import dataclasses

import pytest

from api.domain.polity.config import LegitimacyConfig
from api.domain.polity.legitimacy import (
    compose_ecart,
    crosses_floor,
    initial_legitimacy,
    mandate_strength,
    update_legitimacy,
)

_CONFIG = LegitimacyConfig(
    enabled=True,
    decay=0.9,
    recall_floor=0.2,
    recall_floor_indexed_on_l0=False,
    recall_cooldown_ticks=4,
    passive_erosion_weight=0.0,
)


# ── mandate_strength ──────────────────────────────────────────────────────

def test_mandate_strength_counts_ballots_ranking_winner_above_blank():
    ballots = [
        ["citizen_1", "Blank", "citizen_2"],  # above blank
        ["Blank", "citizen_1", "citizen_2"],  # below blank
        ["citizen_1", "citizen_2", "Blank"],  # above blank
        ["citizen_2", "Blank", "citizen_1"],  # below blank
    ]
    assert mandate_strength(ballots, "citizen_1") == 0.5


def test_mandate_strength_all_blank_ballots_is_zero():
    ballots = [["Blank"], ["Blank"], ["Blank"]]
    assert mandate_strength(ballots, "citizen_1") == 0.0


def test_mandate_strength_winner_absent_from_a_truncated_ranking_counts_as_not_above_blank():
    ballots = [
        ["citizen_2", "citizen_3", "citizen_4", "citizen_5", "citizen_6", "Blank"],
        ["citizen_1", "Blank"],
    ]
    assert mandate_strength(ballots, "citizen_1") == 0.5


def test_mandate_strength_mixed_three_of_four():
    ballots = [
        ["citizen_1", "Blank"],
        ["citizen_1", "Blank"],
        ["citizen_1", "Blank"],
        ["Blank", "citizen_1"],
    ]
    assert mandate_strength(ballots, "citizen_1") == 0.75


def test_mandate_strength_raises_on_empty_ballots():
    with pytest.raises(ValueError, match="at least one ballot"):
        mandate_strength([], "citizen_1")


def test_mandate_strength_ignores_order_after_blank():
    ballots_a = [["citizen_1", "Blank", "citizen_2"]]
    ballots_b = [["citizen_1", "citizen_2", "Blank"]]
    assert mandate_strength(ballots_a, "citizen_1") == mandate_strength(ballots_b, "citizen_1") == 1.0


# ── initial_legitimacy ────────────────────────────────────────────────────

def test_initial_legitimacy_is_the_identity():
    assert initial_legitimacy(0.37) == 0.37
    assert initial_legitimacy(0.0) == 0.0
    assert initial_legitimacy(1.0) == 1.0


# ── compose_ecart ─────────────────────────────────────────────────────────

def test_compose_ecart_all_zero_inputs_is_zero():
    assert compose_ecart(0.0, 0.0, 0.0, petition_weight=0.5, street_weight=0.5, passive_erosion_weight=0.0) == 0.0


def test_compose_ecart_zero_passive_weight_ignores_deviation():
    assert compose_ecart(0.0, 0.0, 0.9, petition_weight=0.5, street_weight=0.5, passive_erosion_weight=0.0) == 0.0


def test_compose_ecart_hand_computed_weights():
    result = compose_ecart(0.4, 0.2, 0.0, petition_weight=0.5, street_weight=0.5, passive_erosion_weight=0.0)
    assert result == pytest.approx(0.5 * 0.4 + 0.5 * 0.2)


def test_compose_ecart_passive_term_adds_linearly():
    base = compose_ecart(0.4, 0.2, 0.0, petition_weight=0.5, street_weight=0.5, passive_erosion_weight=0.1)
    with_deviation = compose_ecart(0.4, 0.2, 0.3, petition_weight=0.5, street_weight=0.5, passive_erosion_weight=0.1)
    assert with_deviation - base == pytest.approx(0.1 * 0.3)


# ── update_legitimacy ─────────────────────────────────────────────────────

def test_update_legitimacy_is_a_fixed_point_at_m_with_zero_ecart():
    assert update_legitimacy(0.51, 0.51, 0.0, _CONFIG) == pytest.approx(0.51)


def test_update_legitimacy_converges_monotonically_toward_m_from_zero():
    # decay=0.9 per tick -> geometric convergence, gap after n ticks is
    # 0.9**n * m; 300 ticks makes the remaining gap negligible (~1e-14).
    legitimacy = 0.0
    values = []
    for _ in range(300):
        legitimacy = update_legitimacy(legitimacy, 0.7, 0.0, _CONFIG)
        values.append(legitimacy)
    assert all(b >= a for a, b in zip(values, values[1:]))
    assert values[-1] == pytest.approx(0.7, abs=1e-3)


def test_update_legitimacy_clamps_at_zero_under_a_large_ecart():
    assert update_legitimacy(0.5, 0.5, 10.0, _CONFIG) == 0.0


def test_update_legitimacy_clamps_at_one():
    assert update_legitimacy(0.5, 0.5, -10.0, _CONFIG) == 1.0


def test_update_legitimacy_decay_one_freezes_l():
    config = dataclasses.replace(_CONFIG, decay=1.0)
    assert update_legitimacy(0.3, 0.9, 0.0, config) == pytest.approx(0.3)


# ── crosses_floor ─────────────────────────────────────────────────────────

def test_crosses_floor_strictly_below_is_true():
    assert crosses_floor(0.1, _CONFIG) is True


def test_crosses_floor_exactly_at_floor_is_false():
    assert crosses_floor(0.2, _CONFIG) is False


def test_crosses_floor_zero_floor_never_fires_after_clamp():
    config = dataclasses.replace(_CONFIG, recall_floor=0.0)
    assert crosses_floor(0.0, config) is False
    assert crosses_floor(update_legitimacy(0.0, 0.0, 100.0, config), config) is False
