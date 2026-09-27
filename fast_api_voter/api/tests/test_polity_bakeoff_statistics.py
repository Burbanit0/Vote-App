"""Bake-off statistics (S2.2). See api/domain/polity/bakeoff_statistics.py."""
from __future__ import annotations

import pytest

from api.domain.polity.bakeoff_statistics import cochrans_q, holm_adjust, mcnemar_exact, separation, spread, wilson_interval


def test_the_wilson_interval_matches_its_closed_form_and_stays_inside_zero_and_one() -> None:
    assert wilson_interval(318, 500) == pytest.approx((0.59294, 0.67699), abs=1e-5)
    assert wilson_interval(0, 10) == pytest.approx((0.0, 0.27753), abs=1e-5)
    assert wilson_interval(10, 10) == pytest.approx((0.72247, 1.0), abs=1e-5)
    assert wilson_interval(0, 0) is None


def test_mcnemar_is_the_exact_binomial_test_on_discordant_pairs() -> None:
    first = [True] * 10 + [False] * 2 + [True] * 5
    second = [False] * 10 + [True] * 2 + [True] * 5
    result = mcnemar_exact(first, second)
    assert (result.first_only, result.second_only) == (10, 2)
    assert result.p_value == pytest.approx(0.03857421875)  # 2 * P(X <= 2), X ~ Binomial(12, 1/2)
    assert mcnemar_exact([True, False], [True, False]).p_value == 1.0
    with pytest.raises(ValueError, match="differ in length"):
        mcnemar_exact([True], [True, False])


def test_cochrans_q_reproduces_the_textbook_example() -> None:
    rows = [(1, 1, 0), (1, 1, 1), (0, 0, 0), (1, 1, 0), (1, 0, 0), (1, 1, 1),
            (1, 1, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (1, 1, 1), (1, 1, 0)]
    models = [[bool(row[m]) for row in rows] for m in range(3)]
    result = cochrans_q(models)
    assert result is not None
    assert (result.q, result.degrees_of_freedom) == (10.75, 2)
    assert result.p_value == pytest.approx(0.0046309, rel=1e-4)


def test_cochrans_q_edge_cases() -> None:
    assert cochrans_q([[True, False]]) is None
    same = cochrans_q([[True, True], [True, True]])
    assert same is not None and (same.q, same.p_value) == (0.0, 1.0)
    with pytest.raises(ValueError, match="every unit"):
        cochrans_q([[True, False], [True]])


def test_holm_steps_down_and_never_lets_an_adjusted_p_fall() -> None:
    assert holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": 0.03, "c": 0.06, "b": 0.06}
    assert holm_adjust({"x": 0.6, "y": 0.9}) == {"x": 1.0, "y": 1.0}
    assert holm_adjust({}) == {}


def test_separation_and_spread() -> None:
    assert separation({0.0: 0.9, 0.5: 0.2, 1.0: 0.95}) == pytest.approx(0.05)
    assert separation({0.0: 0.9}) is None
    assert spread([0.9, 0.2, 0.95]) == pytest.approx(0.75)
    assert spread([]) is None
