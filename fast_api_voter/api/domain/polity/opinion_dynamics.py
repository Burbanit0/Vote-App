"""S4.3 (docs/adr/ADR-012-dynamic-citizens.md): citizens' views move between ticks.

Friedkin-Johnsen with bounded confidence, on the two latent factors a factor_structure
population's issue positions are built from (citizen.LatentStructure). One update, for
every citizen i with factors f_i, initial factors a_i and social-graph neighbours N(i):

    B_i  = { j in N(i) : |f_j - f_i| <= confidence_bound }
    m_i  = mean of f_j over B_i, or f_i when B_i is empty
    f_i' = (1 - susceptibility) a_i + susceptibility (f_i + influence_step (m_i - f_i))
           + drift_std e_i,   e_i ~ N(0, I)

then every issue position is recomputed from the factors, loadings and residuals, so the
issues keep the correlation they were drawn with. With susceptibility 1, influence_step 0
and drift_std 0 the factors do not move at all (property-tested): the neutral settings.
The innovation is drawn on every update whatever drift_std is, so the stream's position
never depends on the settings.

`update_latent_factors` is pure; `apply_dynamics` reads the factors off the citizens and
writes the moved factors and positions back.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from api.domain.polity.citizen import Citizen, LatentStructure
from api.domain.polity.config import DynamicsConfig
from api.domain.polity.social_graph import SocialGraph


@dataclass(frozen=True)
class NeighbourEdges:
    """The social graph as arrays of directed edges, each tie in both directions."""

    source: np.ndarray
    target: np.ndarray

    @classmethod
    def from_graph(cls, graph: SocialGraph | None) -> NeighbourEdges:
        pairs = sorted((cid, neighbour) for cid, neighbours in (graph.neighbors.items() if graph else ()) for neighbour in neighbours)
        edges = np.array(pairs, dtype=np.int64).reshape(-1, 2)
        return cls(source=edges[:, 0], target=edges[:, 1])


@dataclass(frozen=True)
class DynamicsStep:
    factors: np.ndarray
    """The moved factors, (population_size, 2)."""
    mean_shift: float
    """Mean distance a citizen's factors moved."""
    max_shift: float
    influenced: int
    """Citizens with at least one neighbour within the confidence bound."""


def update_latent_factors(
    factors: np.ndarray, anchors: np.ndarray, edges: NeighbourEdges, config: DynamicsConfig, rng: np.random.Generator,
) -> DynamicsStep:
    """One Friedkin-Johnsen update with bounded confidence (see the module docstring)."""
    innovation = rng.normal(0.0, 1.0, size=factors.shape)
    toward = factors[edges.target] - factors[edges.source]
    within = np.linalg.norm(toward, axis=1) <= config.confidence_bound
    counts = np.bincount(edges.source[within], minlength=len(factors))
    sums = np.zeros_like(factors)
    np.add.at(sums, edges.source[within], toward[within])
    pull = sums / np.maximum(counts, 1)[:, None]  # m_i - f_i; zero where nobody is within the bound
    s = config.susceptibility
    moved = (1.0 - s) * anchors + s * (factors + config.influence_step * pull) + config.drift_std * innovation
    shifts = np.linalg.norm(moved - factors, axis=1)
    return DynamicsStep(
        factors=moved, mean_shift=float(shifts.mean()) if len(shifts) else 0.0,
        max_shift=float(shifts.max()) if len(shifts) else 0.0, influenced=int((counts > 0).sum()),
    )


def current_factors(citizens: Sequence[Citizen], structure: LatentStructure) -> np.ndarray:
    """Every citizen's factors, row i for citizen_id i: where they have moved to, or their
    initial factors before the first update."""
    return np.array([
        citizen.latent_factors if citizen.latent_factors is not None else structure.anchors[citizen.citizen_id]
        for citizen in citizens
    ], dtype=float).reshape(-1, structure.anchors.shape[1])


def apply_dynamics(
    citizens: Sequence[Citizen], structure: LatentStructure, edges: NeighbourEdges, config: DynamicsConfig,
    rng: np.random.Generator,
) -> DynamicsStep:
    """Move every citizen's factors one update and recompute their issue positions."""
    if [c.citizen_id for c in citizens] != list(range(len(citizens))):
        raise ValueError("apply_dynamics needs the whole population, ordered by citizen_id")
    step = update_latent_factors(current_factors(citizens, structure), structure.anchors, edges, config, rng)
    positions = structure.positions(step.factors)
    for citizen, factors, issue_positions in zip(citizens, step.factors, positions):
        citizen.latent_factors = tuple(float(x) for x in factors)
        citizen.issue_positions = tuple(float(x) for x in issue_positions)
    return step
