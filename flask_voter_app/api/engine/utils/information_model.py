"""
information_model.py — Asymmetric information in electoral simulations.

Concept
-------
Voters form *perceived* utilities from candidates based on two independent
sources of distortion:

1. **Epistemic noise** — voters don't know candidates' true positions.
   Low-information voters have high uncertainty (σ = 0.4); well-informed
   voters have very low uncertainty (σ = 0.05).

2. **Media bias** — exposure to biased media coverage shifts a voter's
   perception of a candidate's utility upward or downward.  The magnitude
   of the shift is modulated by the voter's information level: low-info
   voters are more susceptible to media framing.

Segment parameters
------------------
+---------------+----------+-------------+
| Segment       | σ (noise)| media_weight|
+---------------+----------+-------------+
| low_info      | 0.40     | 1.5         |
| medium_info   | 0.20     | 1.0         |
| high_info     | 0.05     | 0.3         |
+---------------+----------+-------------+

Media effect: perceived = clamp(true + noise + bias × weight × SCALE, 0, 1)
where SCALE = 0.15 ensures max bias (±1) produces at most ±0.225 (low_info)
or ±0.045 (high_info) shift on the perceived utility.
"""
from __future__ import annotations

import random
from typing import Any

# ── Segment configuration ────────────────────────────────────────────────────

_SEGMENT_PARAMS: dict[str, dict[str, float]] = {
    "low_info":    {"sigma": 0.40, "media_weight": 1.5},
    "medium_info": {"sigma": 0.20, "media_weight": 1.0},
    "high_info":   {"sigma": 0.05, "media_weight": 0.3},
}

_MEDIA_SCALE: float = 0.15   # max raw bias effect before media_weight scaling
_ALL_SEGMENTS: list[str] = ["low_info", "medium_info", "high_info"]


# ── Public API ────────────────────────────────────────────────────────────────

def apply_information_asymmetry(
    true_utilities: list[list[float]],
    media_bias: dict[str, float],
    voter_segments: dict[str, float],
    seed: int | None = None,
) -> list[list[float]]:
    """
    Apply media bias and epistemic noise to true utilities.

    Parameters
    ----------
    true_utilities : list[list[float]]
        ``true_utilities[voter_idx][candidate_idx]`` ∈ [0, 1].
    media_bias : dict[str, float]
        ``{str(candidate_idx): bias}`` where bias ∈ [−1, +1].
        Positive bias = favourable coverage, negative = unfavourable.
    voter_segments : dict[str, float]
        Proportions for each segment (need not sum to 1; normalised internally).
        Keys: ``"low_info"``, ``"medium_info"``, ``"high_info"``.
    seed : int | None
        Optional RNG seed for reproducible tests.

    Returns
    -------
    list[list[float]]
        Perceived utilities with the same shape as ``true_utilities``.
        All values are clamped to [0, 1].
    """
    n_voters = len(true_utilities)
    if n_voters == 0:
        return []

    n_candidates = len(true_utilities[0]) if true_utilities else 0
    rng = random.Random(seed)

    # ── Normalise segment fractions ───────────────────────────────────────
    raw = {k: max(0.0, float(voter_segments.get(k, 0.0))) for k in _ALL_SEGMENTS}
    total = sum(raw.values()) or 1.0
    fracs = {k: raw[k] / total for k in _ALL_SEGMENTS}

    # ── Assign voters to segments deterministically then shuffle ──────────
    low_n    = round(n_voters * fracs["low_info"])
    medium_n = round(n_voters * fracs["medium_info"])
    high_n   = max(0, n_voters - low_n - medium_n)

    segments: list[str] = (
        ["low_info"]    * low_n +
        ["medium_info"] * medium_n +
        ["high_info"]   * high_n
    )
    rng.shuffle(segments)

    # ── Parse and clamp media bias ────────────────────────────────────────
    bias: dict[int, float] = {}
    for k, v in media_bias.items():
        try:
            bias[int(k)] = max(-1.0, min(1.0, float(v)))
        except (ValueError, TypeError):
            pass

    # ── Apply noise + media effect per voter ──────────────────────────────
    perceived: list[list[float]] = []
    for voter_idx, segment in enumerate(segments):
        params      = _SEGMENT_PARAMS[segment]
        sigma       = params["sigma"]
        media_w     = params["media_weight"]
        voter_row: list[float] = []

        for cand_idx in range(n_candidates):
            true_u       = true_utilities[voter_idx][cand_idx]
            noise        = rng.gauss(0.0, sigma)
            b            = bias.get(cand_idx, 0.0)
            media_effect = b * media_w * _MEDIA_SCALE
            perc_u       = max(0.0, min(1.0, true_u + noise + media_effect))
            voter_row.append(perc_u)

        perceived.append(voter_row)

    return perceived


def compute_information_gap(
    true_utilities: list[list[float]],
    perceived_utilities: list[list[float]],
) -> float:
    """
    Mean absolute difference between true and perceived utilities.

    Returns a value in [0, 1]: 0 = perfect information, 1 = maximum distortion.
    """
    total = 0.0
    count = 0
    for true_row, perc_row in zip(true_utilities, perceived_utilities):
        for t, p in zip(true_row, perc_row):
            total += abs(t - p)
            count += 1
    return round(total / count, 4) if count > 0 else 0.0
