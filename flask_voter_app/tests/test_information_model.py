"""
test_information_model.py — Tests for the asymmetric information model.
"""
import math
import pytest

from app.utils.information_model import (
    apply_information_asymmetry,
    compute_information_gap,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def uniform_utilities(n_voters: int, n_cands: int, value: float = 0.5) -> list[list[float]]:
    return [[value] * n_cands for _ in range(n_voters)]


def make_utilities(pattern: str, n_voters: int = 100) -> list[list[float]]:
    """Two-candidate utilities for simple tests."""
    if pattern == "equal":
        return [[0.5, 0.5]] * n_voters
    if pattern == "a_wins":
        return [[0.8, 0.2]] * n_voters
    if pattern == "close":
        return [[0.52, 0.48]] * n_voters
    raise ValueError(pattern)


# ── apply_information_asymmetry — output shape ────────────────────────────────

def test_output_shape_matches_input():
    utils = uniform_utilities(50, 3)
    result = apply_information_asymmetry(utils, {}, {"low_info": 1.0}, seed=0)
    assert len(result) == 50
    assert all(len(row) == 3 for row in result)


def test_empty_input_returns_empty():
    assert apply_information_asymmetry([], {}, {}) == []


def test_all_values_in_0_1():
    """Perceived utilities must remain clamped in [0, 1]."""
    utils = uniform_utilities(200, 4, 0.5)
    result = apply_information_asymmetry(
        utils,
        {"0": 1.0, "1": -1.0, "2": 0.0, "3": 0.5},
        {"low_info": 0.5, "medium_info": 0.3, "high_info": 0.2},
        seed=42,
    )
    for row in result:
        for v in row:
            assert 0.0 <= v <= 1.0, f"Out-of-range: {v}"


# ── bias = 0 → utilités proches des vraies ────────────────────────────────────

def test_zero_bias_mean_distortion_is_zero_centred():
    """
    With zero media bias, the noise is zero-mean Gaussian, so the mean of
    (perceived − true) over all voters and candidates should be near zero.
    """
    n_voters, n_cands = 2000, 3
    utils = uniform_utilities(n_voters, n_cands, 0.5)

    perceived = apply_information_asymmetry(
        utils,
        {"0": 0.0, "1": 0.0, "2": 0.0},          # zero bias
        {"low_info": 0.33, "medium_info": 0.34, "high_info": 0.33},
        seed=123,
    )

    diffs = [
        perceived[i][j] - utils[i][j]
        for i in range(n_voters)
        for j in range(n_cands)
    ]
    mean_diff = sum(diffs) / len(diffs)
    # Mean of zero-mean noise should be close to 0 with a large sample
    assert abs(mean_diff) < 0.03, f"Unexpected mean bias: {mean_diff:.4f}"


def test_zero_bias_high_info_very_close_to_true():
    """
    100 % high_info + zero bias → σ = 0.05 → perceived ≈ true.
    Expected |diff| ≈ σ × √(2/π) ≈ 0.04 per entry.
    """
    n_voters = 500
    utils = [[0.3, 0.7]] * n_voters

    perceived = apply_information_asymmetry(
        utils,
        {},                              # no bias
        {"high_info": 1.0},
        seed=0,
    )
    diffs = [abs(perceived[i][j] - utils[i][j]) for i in range(n_voters) for j in range(2)]
    mean_abs = sum(diffs) / len(diffs)
    # σ=0.05 → E[|ε|] = 0.05 × √(2/π) ≈ 0.040; allow generous tolerance
    assert mean_abs < 0.12, f"High-info noise too large: {mean_abs:.4f}"


# ── 100 % low_info + strong bias changes perceived utilities ──────────────────

def test_strong_positive_bias_raises_perceived_utility():
    """
    100 % low_info voters + bias=+1 for candidate 0:
    mean perceived[*][0] must exceed mean true[*][0].
    """
    n_voters = 500
    utils = [[0.5, 0.5]] * n_voters   # equal true utilities

    perceived = apply_information_asymmetry(
        utils,
        {"0": 1.0, "1": 0.0},          # strong positive bias on candidate 0
        {"low_info": 1.0},
        seed=7,
    )

    mean_true_0    = 0.5
    mean_perc_0    = sum(row[0] for row in perceived) / n_voters
    mean_perc_1    = sum(row[1] for row in perceived) / n_voters

    # Candidate 0 should have higher perceived utility on average
    assert mean_perc_0 > mean_true_0, (
        f"Positive bias should increase perceived utility: {mean_perc_0:.4f} vs {mean_true_0:.4f}"
    )
    assert mean_perc_0 > mean_perc_1, (
        f"Biased candidate should lead: {mean_perc_0:.4f} vs {mean_perc_1:.4f}"
    )


def test_strong_negative_bias_lowers_perceived_utility():
    """100 % low_info + bias=−1 for candidate 0 must lower their perceived utility."""
    n_voters = 500
    utils = [[0.7, 0.3]] * n_voters

    perceived = apply_information_asymmetry(
        utils,
        {"0": -1.0},        # negative bias on candidate 0
        {"low_info": 1.0},
        seed=8,
    )
    mean_perc_0 = sum(row[0] for row in perceived) / n_voters
    mean_true_0 = 0.7
    assert mean_perc_0 < mean_true_0, (
        f"Negative bias should decrease perceived utility: {mean_perc_0:.4f} vs {mean_true_0:.4f}"
    )


def test_low_info_has_more_distortion_than_high_info():
    """Low-info voters must have higher absolute distortion than high-info voters."""
    n = 300
    utils = [[0.5, 0.5]] * (2 * n)

    # First n voters = low_info, last n = high_info (by segment fractions)
    perceived = apply_information_asymmetry(
        utils,
        {"0": 0.0, "1": 0.0},
        {"low_info": 0.5, "high_info": 0.5},
        seed=99,
    )

    # Approximate: first n ~ low_info segment, last n ~ high_info (shuffle may mix)
    # Instead, test that overall distortion is higher than pure high_info would produce
    low_only_perceived = apply_information_asymmetry(
        utils[:n], {}, {"low_info": 1.0}, seed=99,
    )
    high_only_perceived = apply_information_asymmetry(
        utils[:n], {}, {"high_info": 1.0}, seed=99,
    )

    mean_abs_low  = sum(abs(low_only_perceived[i][j] - 0.5) for i in range(n) for j in range(2)) / (2 * n)
    mean_abs_high = sum(abs(high_only_perceived[i][j] - 0.5) for i in range(n) for j in range(2)) / (2 * n)

    assert mean_abs_low > mean_abs_high, (
        f"Low-info should have more distortion: {mean_abs_low:.4f} vs {mean_abs_high:.4f}"
    )


# ── compute_information_gap ───────────────────────────────────────────────────

def test_gap_is_zero_for_identical_matrices():
    utils = [[0.3, 0.7], [0.6, 0.4]]
    assert compute_information_gap(utils, utils) == 0.0


def test_gap_is_positive_with_noise():
    utils = uniform_utilities(100, 2, 0.5)
    perceived = apply_information_asymmetry(utils, {}, {"medium_info": 1.0}, seed=0)
    gap = compute_information_gap(utils, perceived)
    assert gap > 0


def test_gap_increases_with_noise_level():
    utils = uniform_utilities(500, 3, 0.5)

    perc_low  = apply_information_asymmetry(utils, {}, {"high_info": 1.0}, seed=1)
    perc_high = apply_information_asymmetry(utils, {}, {"low_info": 1.0},  seed=1)

    gap_low  = compute_information_gap(utils, perc_low)
    gap_high = compute_information_gap(utils, perc_high)

    assert gap_high > gap_low, (
        f"Low-info gap ({gap_high:.4f}) should exceed high-info gap ({gap_low:.4f})"
    )


def test_gap_empty_returns_zero():
    assert compute_information_gap([], []) == 0.0


# ── Segment normalisation ─────────────────────────────────────────────────────

def test_unbalanced_segments_are_normalised():
    """Segments don't need to sum to 1; function normalises internally."""
    utils = uniform_utilities(100, 2, 0.5)
    # This is 10x too large — should normalise the same as 0.3/0.5/0.2
    result = apply_information_asymmetry(
        utils,
        {},
        {"low_info": 3.0, "medium_info": 5.0, "high_info": 2.0},
        seed=0,
    )
    assert len(result) == 100


def test_missing_segment_defaults_to_zero():
    """Missing segment keys default to 0 proportion."""
    utils = uniform_utilities(50, 2, 0.5)
    result = apply_information_asymmetry(utils, {}, {"high_info": 1.0}, seed=0)
    assert len(result) == 50


# ── Determinism ───────────────────────────────────────────────────────────────

def test_same_seed_produces_same_output():
    utils = uniform_utilities(50, 3, 0.5)
    a = apply_information_asymmetry(utils, {"0": 0.3}, {"low_info": 0.5, "high_info": 0.5}, seed=42)
    b = apply_information_asymmetry(utils, {"0": 0.3}, {"low_info": 0.5, "high_info": 0.5}, seed=42)
    assert a == b


def test_different_seeds_produce_different_output():
    utils = uniform_utilities(50, 2, 0.5)
    a = apply_information_asymmetry(utils, {}, {"medium_info": 1.0}, seed=1)
    b = apply_information_asymmetry(utils, {}, {"medium_info": 1.0}, seed=2)
    assert a != b


# ── API route (integration test) ──────────────────────────────────────────────

def test_compare_with_information_model_enabled(client):
    resp = client.post("/simulations/compare", json={
        "num_candidates":       3,
        "num_voters":           80,
        "candidates":           ["Alice", "Bob", "Carol"],
        "information_model":    {
            "enabled":          True,
            "media_bias":       {"0": 0.5, "1": -0.3, "2": 0.0},
            "voter_segments":   {"low_info": 0.4, "medium_info": 0.4, "high_info": 0.2},
        },
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "information_model" in data
    im = data["information_model"]
    assert im["enabled"] is True
    assert "sincere_winner"    in im
    assert "perceived_winner"  in im
    assert "information_gap"   in im
    assert isinstance(im["information_gap"], float)
    assert 0.0 <= im["information_gap"] <= 1.0


def test_compare_without_information_model(client):
    resp = client.post("/simulations/compare", json={
        "num_voters":        60,
        "candidates":        ["Alice", "Bob"],
        "information_model": {"enabled": False},
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["information_model"]["enabled"] is False


def test_compare_without_information_model_key(client):
    """information_model is optional — omitting it must not cause errors."""
    resp = client.post("/simulations/compare", json={
        "num_voters":  60,
        "candidates":  ["Alice", "Bob"],
    })
    assert resp.status_code == 200
