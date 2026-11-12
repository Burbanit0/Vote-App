"""ADR-022: the president's extra-legal act. The model only asks; the kernel rolls."""

from __future__ import annotations

import math

import numpy as np

from api.domain.polity.config import RegimeConfig


def refusal_probability(approval: float, config: RegimeConfig) -> float:
    """logistic(support_weight * (approval - 0.5) + loyalty_weight * (1 - 2 * loyalty) - severity_weight * severity):
    support pulls toward success, the loyal share of the state's servants and the act's gravity push against."""
    x = (
        config.support_weight * (approval - 0.5)
        + config.loyalty_weight * (1 - 2 * config.loyalty)
        - config.severity_weight * config.severity
    )
    return 1 / (1 + math.exp(-x))


def refusal_succeeds(approval: float, config: RegimeConfig, rng: np.random.Generator) -> tuple[float, bool]:
    probability = refusal_probability(approval, config)
    return probability, bool(rng.random() < probability)
