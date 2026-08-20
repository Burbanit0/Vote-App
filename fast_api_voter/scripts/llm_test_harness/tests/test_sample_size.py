from __future__ import annotations

import pytest

from llm_test_harness import sample_size


def test_z_score_known_values():
    assert sample_size.z_score(0.95) == pytest.approx(1.9600, abs=1e-4)
    assert sample_size.z_score(0.99) == pytest.approx(2.5758, abs=1e-4)


def test_z_score_unsupported_confidence_raises():
    with pytest.raises(ValueError, match="unsupported confidence level"):
        sample_size.z_score(0.93)


def test_required_sample_size_hand_computed():
    # z=1.96, p=0.5, e=0.1 -> n = ceil(1.96^2 * 0.25 / 0.01) = ceil(96.04) = 97
    n = sample_size.required_sample_size(0.5, confidence=0.95, margin_of_error=0.1)
    assert n == 97


def test_required_sample_size_via_decision_threshold():
    # margin defaults to |threshold - p| / 2 = |0.1 - 0.5| / 2 = 0.2
    # z=1.96, p=0.5, e=0.2 -> n = ceil(1.96^2*0.25/0.04) = ceil(24.01) = 25
    n = sample_size.required_sample_size(0.5, confidence=0.95, decision_threshold=0.1)
    assert n == 25


def test_required_sample_size_rejects_extreme_rates():
    with pytest.raises(ValueError, match=r"must be in \(0, 1\)"):
        sample_size.required_sample_size(0.0, margin_of_error=0.1)
    with pytest.raises(ValueError, match=r"must be in \(0, 1\)"):
        sample_size.required_sample_size(1.0, margin_of_error=0.1)


def test_required_sample_size_requires_exactly_one_of_margin_or_threshold():
    with pytest.raises(ValueError, match="exactly one"):
        sample_size.required_sample_size(0.5)
    with pytest.raises(ValueError, match="exactly one"):
        sample_size.required_sample_size(0.5, margin_of_error=0.1, decision_threshold=0.2)


def test_required_sample_size_rejects_nonpositive_margin():
    with pytest.raises(ValueError, match="must be positive"):
        sample_size.required_sample_size(0.5, margin_of_error=0.0)


def test_exhaustion_probability_matches_the_sessions_own_arithmetic():
    # the exact 0.5^6 figure used informally throughout this project's own
    # GPU investigation.
    assert sample_size.exhaustion_probability(0.5, 6) == pytest.approx(0.015625)


def test_exhaustion_probability_zero_attempts_is_certain_exhaustion():
    assert sample_size.exhaustion_probability(0.9, 0) == 1.0


def test_exhaustion_probability_perfect_success_rate_is_never_exhausted():
    assert sample_size.exhaustion_probability(1.0, 100) == 0.0


def test_exhaustion_probability_rejects_out_of_range_rate():
    with pytest.raises(ValueError, match=r"must be in \[0, 1\]"):
        sample_size.exhaustion_probability(1.5, 3)


def test_exhaustion_probability_rejects_negative_attempts():
    with pytest.raises(ValueError, match="must be non-negative"):
        sample_size.exhaustion_probability(0.5, -1)
