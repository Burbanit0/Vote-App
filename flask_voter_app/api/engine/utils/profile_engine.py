"""
profile_engine — the social-choice primitive (Lab reshape Phase P1).

The rigorous core of the playground: every method consumes a **preference profile**
(a utility matrix `voter_id -> {candidate_name: utility}`), and the *source* of that
profile is a swappable, user-configured generator. The 2D spatial map is just ONE
generator; statistical cultures and a hand-crafted matrix are equally first-class.

Nothing is hidden: dims, valence, the generation model and its parameters, and the
voter behaviour are all knobs set by the caller, never smuggled in.

Pure functions only (no FastAPI / no I/O). Fed to `compare_all_methods(...,
override_utilities=matrix)`, which is the existing profile-as-interface hook.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

UtilityMatrix = Dict[int, Dict[str, float]]

# Axis order for spatial coordinates (x, y, z) sliced to `dims`.
_AXES = ("x", "y", "z")


# ── Ordinal → cardinal helper ───────────────────────────────────────────────


def _utils_from_rankings(rankings: List[List[str]], names: List[str]) -> UtilityMatrix:
    """Map each voter's strict ranking (best→worst) to utilities in [0, 1] by rank
    position. m candidates → top gets 1.0, bottom 0.0 (Borda-normalised)."""
    m = len(names)
    matrix: UtilityMatrix = {}
    for i, ranking in enumerate(rankings):
        pos = {name: r for r, name in enumerate(ranking)}
        if m > 1:
            matrix[i] = {name: float((m - 1 - pos[name]) / (m - 1)) for name in names}
        else:
            matrix[i] = {names[0]: 1.0}
    return matrix


# ── Generators ──────────────────────────────────────────────────────────────


def spatial_profile(
    candidates: List[Dict[str, Any]],
    num_voters: int,
    dims: int,
    valence: bool,
    seed: int,
) -> Tuple[UtilityMatrix, np.ndarray, np.ndarray, List[str]]:
    """Voters & candidates as vectors in ℝ^dims; utility = -distance (+ valence).

    Returns (matrix, voter_points, candidate_points, names). Points are real
    coordinates used directly as the display embedding for the spatial source.
    """
    rng = np.random.default_rng(seed)
    names = [str(c["name"]) for c in candidates]
    axes = _AXES[:dims]
    cand_pts = np.array(
        [[float(c.get(ax, 0.0)) for ax in axes] for c in candidates], dtype=float
    )
    voter_pts = np.clip(rng.normal(0.0, 0.4, size=(num_voters, dims)), -1.0, 1.0)
    valences = (
        np.array([float(c.get("valence", 0.0)) for c in candidates], dtype=float)
        if valence
        else np.zeros(len(names), dtype=float)
    )
    matrix: UtilityMatrix = {}
    for i in range(num_voters):
        dist = np.linalg.norm(cand_pts - voter_pts[i], axis=1)
        util = -dist + valences
        matrix[i] = {names[j]: float(util[j]) for j in range(len(names))}
    return matrix, voter_pts, cand_pts, names


def impartial_culture_profile(
    names: List[str], num_voters: int, seed: int
) -> UtilityMatrix:
    """Impartial Culture: each voter draws a uniformly-random strict ranking."""
    rng = np.random.default_rng(seed)
    rankings = [list(rng.permutation(names)) for _ in range(num_voters)]
    return _utils_from_rankings(rankings, names)


def mallows_profile(
    names: List[str], num_voters: int, phi: float, seed: int
) -> UtilityMatrix:
    """Mallows model via the Repeated Insertion Model (exact sampler).

    `phi` ∈ (0, 1] is the dispersion: phi→0 concentrates on the reference ranking
    (high consensus), phi=1 is Impartial Culture (no consensus). The reference is
    the given `names` order.
    """
    rng = np.random.default_rng(seed)
    phi = min(max(phi, 1e-6), 1.0)
    rankings: List[List[str]] = []
    for _ in range(num_voters):
        order: List[str] = []
        for i, item in enumerate(names):
            # Insert `item` into one of i+1 positions; prob(position j) ∝ phi^(i-j).
            weights = np.array([phi ** (i - j) for j in range(i + 1)], dtype=float)
            weights /= weights.sum()
            j = int(rng.choice(i + 1, p=weights))
            order.insert(j, item)
        rankings.append(order)
    return _utils_from_rankings(rankings, names)


def polya_urn_profile(
    names: List[str], num_voters: int, alpha: float, seed: int
) -> UtilityMatrix:
    """Pólya-Eggenberger urn: correlated rankings. Each voter copies a previously
    drawn ranking with probability drawn/(drawn+alpha), else draws fresh. Small
    `alpha` → strong correlation (herding); large `alpha` → Impartial Culture."""
    rng = np.random.default_rng(seed)
    alpha = max(alpha, 1e-6)
    drawn: List[List[str]] = []
    rankings: List[List[str]] = []
    for _ in range(num_voters):
        if drawn and rng.random() < len(drawn) / (len(drawn) + alpha):
            rankings.append(list(drawn[int(rng.integers(len(drawn)))]))
        else:
            fresh = list(rng.permutation(names))
            drawn.append(fresh)
            rankings.append(fresh)
    return _utils_from_rankings(rankings, names)


def handcrafted_profile(matrix_in: List[List[float]], names: List[str]) -> UtilityMatrix:
    """Accept a directly-supplied utility matrix (rows = voters, cols = candidates,
    aligned with `names`). Builds exact paradoxes by hand."""
    matrix: UtilityMatrix = {}
    for i, row in enumerate(matrix_in):
        matrix[i] = {names[j]: float(row[j]) for j in range(len(names))}
    return matrix


# ── Ballot projection (frontier FA-1) ────────────────────────────────────────
#
# The BALLOT (how a voter may express) is half the design space, separate from
# the counting rule. project_ballot() converts each voter's underlying utility
# vector into the ballot the rule actually sees — information is LOST on
# purpose, and that loss can flip winners at equal counting rule.
#
# Stated conventions:
#  · per-voter utilities are min-max normalised to [0,1] before projection;
#  · approve marks candidates at ≥ 0.5;
#  · rank_truncated keeps the top-k (top = 1.0 … k-th = 1/k), the rest at 0 —
#    methods needing a total order break those ties in stable name order
#    (an artifact of truncation itself, stated, not hidden);
#  · score/grade quantise to L levels; cumulative spreads a 10-point budget
#    proportionally to positive utilities.

BALLOT_TYPES = (
    "full", "choose_one", "approve", "rank_full", "rank_truncated",
    "score", "grade", "cumulative",
)

# Method slugs (compare_all_methods keys) that need CARDINAL intensity.
_CARDINAL_METHODS = {
    "evaluative", "majority_judgment", "mean_median_hybrid", "median_voting",
    "quadratic", "simple_score", "star_voting", "variance_based",
}
_ORDINAL_METHODS = {
    "baldwin", "borda", "bucklin", "coombs", "copeland", "irv", "kemeny_young",
    "minimax", "nanson", "plurality", "schulze", "two_round",
}
_ALL_METHODS = _CARDINAL_METHODS | _ORDINAL_METHODS | {"approval"}


def compatible_methods(ballot_type: str) -> set:
    """Which counting rules can HONESTLY run on this ballot's information."""
    if ballot_type in ("full", "score", "grade", "cumulative"):
        return set(_ALL_METHODS)
    if ballot_type in ("rank_full", "rank_truncated"):
        return set(_ORDINAL_METHODS)
    if ballot_type == "approve":
        return {"approval"}
    if ballot_type == "choose_one":
        return {"plurality", "two_round"}
    return set(_ALL_METHODS)


def _normalise_row(utils: Dict[str, float]) -> Dict[str, float]:
    vals = list(utils.values())
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    return {n: (u - lo) / span for n, u in utils.items()}


def project_ballot(
    matrix: UtilityMatrix,
    names: List[str],
    ballot_type: str,
    truncate_at: Optional[int] = None,
    score_levels: int = 6,
) -> UtilityMatrix:
    """Project true utilities onto the expressed ballot (as an effective
    utility matrix consumable by compare_all_methods unchanged)."""
    if ballot_type == "full":
        return matrix
    k = max(1, min(len(names), truncate_at or 3))
    levels = max(2, min(10, score_levels))
    out: UtilityMatrix = {}
    for vid, utils in matrix.items():
        norm = _normalise_row(utils)
        ranked = sorted(names, key=lambda n: -norm[n])
        if ballot_type == "choose_one":
            out[vid] = {n: (1.0 if n == ranked[0] else 0.0) for n in names}
        elif ballot_type == "approve":
            out[vid] = {n: (1.0 if norm[n] >= 0.5 else 0.0) for n in names}
        elif ballot_type == "rank_full":
            m = len(names)
            pos = {n: i for i, n in enumerate(ranked)}
            out[vid] = {n: (m - 1 - pos[n]) / max(1, m - 1) for n in names}
        elif ballot_type == "rank_truncated":
            top = ranked[:k]
            out[vid] = {
                n: ((k - top.index(n)) / k if n in top else 0.0) for n in names
            }
        elif ballot_type in ("score", "grade"):
            lv = 7 if ballot_type == "grade" else levels
            out[vid] = {n: round(norm[n] * (lv - 1)) / (lv - 1) for n in names}
        elif ballot_type == "cumulative":
            budget = 10.0
            total = sum(norm.values()) or 1.0
            out[vid] = {n: round(budget * norm[n] / total) / budget for n in names}
        else:
            raise ValueError(f"unknown ballot type: {ballot_type}")
    return out


def ballot_metrics(
    ballot_type: str, m: int, truncate_at: Optional[int] = None, score_levels: int = 6
) -> Dict[str, float]:
    """Expressiveness (bits a ballot can carry) vs cognitive load (decisions it
    demands), both normalised to [0,1]. Stated conventions, not measurements."""
    k = max(1, min(m, truncate_at or 3))
    lv = 7 if ballot_type == "grade" else max(2, min(10, score_levels))
    log2 = math.log2

    def perm_bits(n: int, r: int) -> float:  # log2(n!/(n-r)!)
        return sum(log2(n - i) for i in range(r))

    bits = {
        "full":           m * log2(101),
        "choose_one":     log2(max(2, m)),
        "approve":        float(m),
        "rank_full":      perm_bits(m, m),
        "rank_truncated": perm_bits(m, k),
        "score":          m * log2(lv),
        "grade":          m * log2(7),
        "cumulative":     m * log2(11),
    }[ballot_type]
    load = {
        "full":           3.0 * m,
        "choose_one":     1.0 * m,        # scan for your favourite, one mark
        "approve":        2.0 * m,        # one threshold decision per candidate
        "rank_full":      m * max(1.0, log2(max(2, m))) + m,
        "rank_truncated": m + k * max(1.0, log2(max(2, k))),
        "score":          3.0 * m,        # calibrate each on the scale
        "grade":          3.0 * m,
        "cumulative":     4.0 * m,        # budget juggling on top
    }[ballot_type]
    return {
        "expressiveness": round(min(1.0, bits / (m * log2(101))), 4),
        "cognitive_load": round(min(1.0, load / (4.0 * m)), 4),
    }


# ── Behaviour transform ──────────────────────────────────────────────────────


def _frontrunners(matrix: UtilityMatrix, names: List[str]) -> Tuple[str, str]:
    """Top-2 candidates by mean utility (a Borda-ish proxy for 'who's viable')."""
    totals = {n: 0.0 for n in names}
    for utils in matrix.values():
        for n in names:
            totals[n] += utils[n]
    ordered = sorted(names, key=lambda n: -totals[n])
    return ordered[0], ordered[1]


def apply_behavior(
    matrix: UtilityMatrix, names: List[str], behavior: str, seed: int
) -> UtilityMatrix:
    """Transform sincere utilities by voter behaviour.

    - sincere: identity.
    - strategic: Duverger-style compression onto the two frontrunners — each voter
      pushes their preferred frontrunner to the top and the other to the bottom,
      modelling desertion of non-viable favourites. A transparent heuristic, not a
      method-specific Nash equilibrium.
    - mixed: apply the strategic transform to a random ~50% of voters.
    """
    if behavior == "sincere" or len(names) < 2:
        return matrix
    f1, f2 = _frontrunners(matrix, names)
    rng = np.random.default_rng(seed)
    out: UtilityMatrix = {}
    for vid, utils in matrix.items():
        act = behavior == "strategic" or (behavior == "mixed" and rng.random() < 0.5)
        if not act:
            out[vid] = utils
            continue
        new = dict(utils)
        hi, lo = max(utils.values()), min(utils.values())
        if utils[f1] >= utils[f2]:
            new[f1], new[f2] = hi, lo
        else:
            new[f2], new[f1] = hi, lo
        out[vid] = new
    return out


# ── Diagnostics ──────────────────────────────────────────────────────────────


def condorcet_winner(matrix: UtilityMatrix, names: List[str]) -> Optional[str]:
    """Return the Condorcet winner (beats every other in pairwise majority) or None
    if a cycle / tie leaves none."""
    n = len(names)
    voters = list(matrix.values())
    for a in names:
        wins_all = True
        for b in names:
            if a == b:
                continue
            a_better = sum(1 for u in voters if u[a] > u[b])
            b_better = sum(1 for u in voters if u[b] > u[a])
            if a_better <= b_better:
                wins_all = False
                break
        if wins_all:
            return a
    _ = n
    return None


def cycle_rate(
    source: str,
    names: List[str],
    num_voters: int,
    source_params: Dict[str, float],
    seed: int,
    replications: int = 120,
) -> float:
    """Fraction of re-generated profiles with NO Condorcet winner — the
    paradox/cycle rate. The robustness read-out that separates a structural
    property from a hand-picked artifact. Spatial profiles need candidate points,
    so this only varies the statistical-culture sources (spatial cycle rate is
    reported as 0 for ≤3 candidates where the median makes cycles rare)."""
    if source == "handcrafted":
        return 0.0
    cycles = 0
    for r in range(replications):
        s = seed + r * 7919
        if source == "impartial":
            m = impartial_culture_profile(names, num_voters, s)
        elif source == "mallows":
            m = mallows_profile(names, num_voters, source_params.get("phi", 0.6), s)
        elif source == "urn":
            m = polya_urn_profile(names, num_voters, source_params.get("alpha", 1.0), s)
        else:
            return 0.0
        if condorcet_winner(m, names) is None:
            cycles += 1
    return round(cycles / replications, 4)


def pca_embed_2d(matrix: UtilityMatrix, num_points: int) -> np.ndarray:
    """Project per-voter utility vectors to 2D via PCA so non-spatial profiles can
    still render on the map. `num_points` voters returned as an (n, 2) array."""
    rows = np.array([list(matrix[i].values()) for i in range(num_points)], dtype=float)
    if rows.shape[0] < 2 or rows.shape[1] < 2:
        return np.zeros((num_points, 2), dtype=float)
    centered = rows - rows.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T
    # Normalise into roughly [-1, 1] for display.
    span = np.abs(coords).max() or 1.0
    return coords / span


def gallagher_index(vote_shares: List[float], seat_shares: List[float]) -> float:
    """Gallagher (least-squares) disproportionality index, in percent:
    sqrt( 0.5 * Σ (vᵢ − sᵢ)² ). Shares are fractions in [0, 1]. Pure math, reused by
    the assembly playground (P3)."""
    v = np.array(vote_shares, dtype=float) * 100.0
    s = np.array(seat_shares, dtype=float) * 100.0
    return round(float(np.sqrt(0.5 * np.sum((v - s) ** 2))), 4)


# ── Top-level builder ─────────────────────────────────────────────────────────


def build_profile(
    source: str,
    candidates: List[Dict[str, Any]],
    num_voters: int,
    dims: int,
    valence: bool,
    behavior: str,
    source_params: Dict[str, float],
    seed: int,
    handcrafted_matrix: Optional[List[List[float]]] = None,
) -> Dict[str, Any]:
    """Build a profile from the chosen source, apply the behaviour transform, and
    return the utility matrix plus a 2D display embedding and the candidate names.

    Returns: {matrix, names, display_points (n×2), candidate_points (m×2 | None)}.
    """
    candidate_points: Optional[List[List[float]]] = None

    if source == "spatial":
        matrix, voter_pts, cand_pts, names = spatial_profile(
            candidates, num_voters, dims, valence, seed
        )
        display = voter_pts[:, :2] if dims >= 2 else np.column_stack(
            [voter_pts[:, 0], np.zeros(num_voters)]
        )
        candidate_points = (
            cand_pts[:, :2].tolist()
            if dims >= 2
            else [[float(p[0]), 0.0] for p in cand_pts]
        )
    else:
        names = [str(c["name"]) for c in candidates]
        if source == "impartial":
            matrix = impartial_culture_profile(names, num_voters, seed)
        elif source == "mallows":
            matrix = mallows_profile(names, num_voters, source_params.get("phi", 0.6), seed)
        elif source == "urn":
            matrix = polya_urn_profile(names, num_voters, source_params.get("alpha", 1.0), seed)
        elif source == "handcrafted":
            if not handcrafted_matrix:
                raise ValueError("handcrafted source requires a non-empty matrix")
            matrix = handcrafted_profile(handcrafted_matrix, names)
            num_voters = len(handcrafted_matrix)
        else:
            raise ValueError(f"unknown preference source: {source}")
        display = pca_embed_2d(matrix, num_voters)

    matrix = apply_behavior(matrix, names, behavior, seed)

    return {
        "matrix": matrix,
        "names": names,
        "display_points": np.asarray(display, dtype=float).tolist(),
        "candidate_points": candidate_points,
    }
