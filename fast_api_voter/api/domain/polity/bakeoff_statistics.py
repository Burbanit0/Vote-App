"""Statistics for the model bake-off (S2.2): interval estimates for one model, paired
tests between models on the same cases, and a family-wise correction across them.

Every model in a bake-off answers the same frozen cases, so comparisons are paired:
McNemar's exact test for two models, Cochran's Q for all of them at once, and Holm's
step-down correction over every test a scorecard reports.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scipy import stats


def wilson_interval(successes: int, trials: int, *, confidence: float = 0.95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; None with no trials. Unlike the
    normal approximation it stays inside [0, 1] and behaves at 0 and n successes."""
    if trials == 0:
        return None
    z = float(stats.norm.ppf(1 - (1 - confidence) / 2))
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


@dataclass(frozen=True)
class McNemarResult:
    first_only: int
    """Pairs the first model got right and the second wrong."""
    second_only: int
    p_value: float


def mcnemar_exact(first: Sequence[bool], second: Sequence[bool]) -> McNemarResult:
    """Exact McNemar test: under the null, each discordant pair is equally likely to
    favour either model, so the smaller count is binomial(discordant, 1/2)."""
    if len(first) != len(second):
        raise ValueError(f"paired outcomes differ in length: {len(first)} vs {len(second)}")
    first_only = sum(1 for a, b in zip(first, second) if a and not b)
    second_only = sum(1 for a, b in zip(first, second) if b and not a)
    discordant = first_only + second_only
    if discordant == 0:
        return McNemarResult(first_only, second_only, 1.0)
    p_value = float(stats.binomtest(min(first_only, second_only), discordant, 0.5).pvalue)
    return McNemarResult(first_only, second_only, min(1.0, p_value))


@dataclass(frozen=True)
class CochranResult:
    q: float
    degrees_of_freedom: int
    p_value: float


def cochrans_q(outcomes: Sequence[Sequence[bool]]) -> CochranResult | None:
    """Cochran's Q over k models' binary outcomes on the same n units (`outcomes[model][unit]`).
    None with fewer than two models."""
    k = len(outcomes)
    if k < 2:
        return None
    n = len(outcomes[0])
    if any(len(model) != n for model in outcomes):
        raise ValueError("every model must have an outcome for every unit")
    model_totals = [sum(model) for model in outcomes]
    unit_totals = [sum(model[i] for model in outcomes) for i in range(n)]
    grand = sum(model_totals)
    denominator = k * grand - sum(t * t for t in unit_totals)
    if denominator == 0:
        return CochranResult(0.0, k - 1, 1.0)
    q = (k - 1) * (k * sum(t * t for t in model_totals) - grand * grand) / denominator
    return CochranResult(q, k - 1, float(stats.chi2.sf(q, k - 1)))


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm's step-down adjusted p-values, which control the family-wise error rate
    over every test named."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * p_value))
        adjusted[name] = running
    return adjusted


def separation(probability_by_t: Mapping[float, float]) -> float | None:
    """P at the highest contrast level minus P at the lowest: the sign says which way the
    answer moves as the input moves from one pole to the other. None with fewer than two levels."""
    if len(probability_by_t) < 2:
        return None
    return probability_by_t[max(probability_by_t)] - probability_by_t[min(probability_by_t)]


def spread(values: Sequence[float]) -> float | None:
    return max(values) - min(values) if values else None
