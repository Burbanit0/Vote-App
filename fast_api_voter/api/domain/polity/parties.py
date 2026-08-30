"""
api.domain.polity.parties — initial party platforms (Lot 3).

Resolves audit blocker A2 ("rien ne dit d'où viennent les partis"): N fixed
parties, platforms initialized by k-means on citizen issue positions. No
birth/death in v0 (parties.birth_enabled/death_enabled are both false —
that's a v1+ palier). Party splitting (Points ouverts #4) was closed
2026-08-29 with no code ever written: no research motivation was ever
named anywhere in the design doc for it, unlike every other Points
ouverts item this project has resolved -- see
polity-simulation-design-v2.md's own entry for the closure reasoning.
parties.split_enabled existed only as an unconsumed config flag (same
class of dead config as candidacy.independent_signature_ratio,
ADR-003) and was deleted, not merely left reserved.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from api.domain.polity.citizen import Citizen

_MAX_KMEANS_ITER = 100


@dataclass(frozen=True)
class Party:
    party_id: int
    platform: tuple[float, ...]


def _kmeans(points: np.ndarray, k: int, seed: int) -> np.ndarray:
    """Deterministic Lloyd's-algorithm k-means: same (points, k, seed) always
    converges to the same centroids. A cluster left empty after an assignment
    step keeps its previous centroid unchanged rather than being
    reseeded — a fixed, deterministic rule, not a data-dependent retry."""
    rng = np.random.default_rng(seed)
    n = points.shape[0]
    centroids = points[rng.choice(n, size=k, replace=False)].copy()

    for _ in range(_MAX_KMEANS_ITER):
        distances = np.linalg.norm(points[:, None, :] - centroids[None, :, :], axis=2)
        assignments = np.argmin(distances, axis=1)
        new_centroids = centroids.copy()
        changed = False
        for cluster in range(k):
            members = points[assignments == cluster]
            if len(members) == 0:
                continue
            candidate = members.mean(axis=0)
            if not np.array_equal(candidate, new_centroids[cluster]):
                changed = True
            new_centroids[cluster] = candidate
        centroids = new_centroids
        if not changed:
            break

    return centroids


def initialize_parties(citizens: list[Citizen], initial_count: int, seed: int) -> list[Party]:
    """Party platforms via k-means on citizen positions (A2). Deterministic:
    the same (citizens, initial_count, seed) always yields the same parties."""
    if initial_count <= 0:
        raise ValueError("initial_count must be positive")
    if len(citizens) < initial_count:
        raise ValueError(f"cannot form {initial_count} parties from {len(citizens)} citizens")

    points = np.array([c.issue_positions for c in citizens], dtype=float)
    centroids = _kmeans(points, initial_count, seed)

    return [
        Party(party_id=i, platform=tuple(float(x) for x in centroids[i]))
        for i in range(initial_count)
    ]
