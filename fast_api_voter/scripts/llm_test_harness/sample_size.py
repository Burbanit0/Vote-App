"""
fast_api_voter/scripts/llm_test_harness/sample_size.py

Sample-size calculation for a single binomial proportion, using the
standard normal-approximation (Wald) formula: n = ceil(z^2 * p*(1-p) / e^2).
Deliberately not sophisticated (no Wilson-score correction, no continuity
correction) -- per the harness's own design brief, this exists to catch a
manifestly-too-small pre-registered n before a GPU-hours investigation
starts, not to be a publishable-grade statistics library. Known limitation,
left undone on purpose: the Wald approximation is inaccurate for p near 0
or 1, or for small n -- a Wilson-score interval would be the natural
upgrade if this ever needs to be trustworthy at the extremes.
"""
from __future__ import annotations

import math

# z-scores for the confidence levels this project is likely to ever ask
# for. Not a general inverse-normal-CDF implementation (would need scipy,
# a dependency this stdlib-only module deliberately avoids) -- a small
# fixed table covering the conventional levels, extended if a genuinely
# new confidence level is ever needed.
_Z_SCORES: dict[float, float] = {
    0.80: 1.2816,
    0.90: 1.6449,
    0.95: 1.9600,
    0.98: 2.3263,
    0.99: 2.5758,
}


def z_score(confidence: float) -> float:
    """Looks up the z-score for a confidence level from a small fixed
    table (see module docstring). Raises ValueError naming the supported
    levels for anything not in the table, rather than interpolating or
    silently picking the nearest one."""
    try:
        return _Z_SCORES[confidence]
    except KeyError:
        supported = ", ".join(str(c) for c in sorted(_Z_SCORES))
        raise ValueError(
            f"unsupported confidence level {confidence!r} -- supported: {supported}"
        ) from None


def required_sample_size(
    expected_effect_rate: float,
    *,
    confidence: float = 0.95,
    margin_of_error: float | None = None,
    decision_threshold: float | None = None,
) -> int:
    """Minimum n to estimate a binomial proportion within +/- margin_of_error
    at the given confidence level: n = ceil(z^2 * p*(1-p) / e^2).

    Exactly one of `margin_of_error` or `decision_threshold` must be given.
    `margin_of_error` is the direct, standard parameterization.
    `decision_threshold` is a convenience for this project's own recurring
    question ("is the true rate above or below X?"): margin_of_error
    defaults to half the distance between expected_effect_rate and the
    threshold -- close enough to resolve which side of the threshold the
    true rate falls on, not an arbitrary precision target.

    Raises ValueError if both or neither sizing argument is given, if
    margin_of_error ends up non-positive, or if expected_effect_rate is
    outside (0, 1) -- a rate of exactly 0 or 1 makes p*(1-p)=0, producing a
    nonsensical n=0; real experiments always carry some uncertainty about
    the true rate, even when the hypothesis is "this should always
    succeed"."""
    if not 0.0 < expected_effect_rate < 1.0:
        raise ValueError(f"expected_effect_rate must be in (0, 1), got {expected_effect_rate!r}")
    if (margin_of_error is None) == (decision_threshold is None):
        raise ValueError("pass exactly one of margin_of_error or decision_threshold")
    if margin_of_error is None:
        assert decision_threshold is not None
        margin_of_error = abs(decision_threshold - expected_effect_rate) / 2
    if margin_of_error <= 0.0:
        raise ValueError(f"margin_of_error must be positive, got {margin_of_error!r}")

    z = z_score(confidence)
    p = expected_effect_rate
    n = (z**2 * p * (1 - p)) / (margin_of_error**2)
    return math.ceil(n)


def exhaustion_probability(per_attempt_success_rate: float, n_attempts: int) -> float:
    """P(all n_attempts fail), given independent per-attempt trials at a
    fixed success rate -- the exact 0.5**6-style arithmetic used
    informally throughout this project's own GPU reliability
    investigation, made a named, tested function instead of an ad hoc
    inline calculation. Does NOT itself validate the independence
    assumption -- that is an empirical question for the experiment's own
    trial data (see report.py's own stationarity-aware framing), not
    something this pure function can check."""
    if not 0.0 <= per_attempt_success_rate <= 1.0:
        raise ValueError(
            f"per_attempt_success_rate must be in [0, 1], got {per_attempt_success_rate!r}"
        )
    if n_attempts < 0:
        raise ValueError(f"n_attempts must be non-negative, got {n_attempts!r}")
    return (1.0 - per_attempt_success_rate) ** n_attempts
