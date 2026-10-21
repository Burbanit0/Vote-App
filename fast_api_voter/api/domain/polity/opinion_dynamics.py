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

from api.domain.polity.citizen import Citizen, LatentStructure, Office
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
    radicalised: int = 0
    """Citizens ADR-033's push moved this update."""


@dataclass(frozen=True)
class Mood:
    """What ADR-033 reads off the citizens: each one's anger and the salience a shock left them, in citizen
    order, and the factors of the president they are angry at (None: no president, nobody is pushed)."""

    anger: np.ndarray
    salience: np.ndarray
    president: np.ndarray | None


def update_latent_factors(
    factors: np.ndarray, anchors: np.ndarray, edges: NeighbourEdges, config: DynamicsConfig, rng: np.random.Generator,
    mood: Mood | None = None,
) -> DynamicsStep:
    """One Friedkin-Johnsen update with bounded confidence (see the module docstring), and with a `mood`
    ADR-033's two couplings: anger narrows a citizen's confidence bound, and an angry citizen the shock
    reached steps away from the president. With radical_step and anger_narrows_bound at 0 the mood is
    never read, so the neutral settings stay exactly neutral."""
    innovation = rng.normal(0.0, 1.0, size=factors.shape)
    toward = factors[edges.target] - factors[edges.source]
    bound = np.full(len(factors), config.confidence_bound)
    if mood is not None and config.anger_narrows_bound > 0:
        bound = bound * (1.0 - config.anger_narrows_bound * mood.anger)
    within = np.linalg.norm(toward, axis=1) <= bound[edges.source]
    counts = np.bincount(edges.source[within], minlength=len(factors))
    sums = np.zeros_like(factors)
    np.add.at(sums, edges.source[within], toward[within])
    pull = sums / np.maximum(counts, 1)[:, None]  # m_i - f_i; zero where nobody is within the bound
    step = config.influence_step * pull
    pushed = 0
    if mood is not None and mood.president is not None and config.radical_step > 0:
        away = factors - mood.president
        distance = np.linalg.norm(away, axis=1, keepdims=True)
        direction = np.divide(away, distance, out=np.zeros_like(away), where=distance > 0)
        push = config.radical_step * (mood.anger * mood.salience)[:, None] * direction
        step = step + push
        pushed = int((np.linalg.norm(push, axis=1) > 0).sum())
    s = config.susceptibility
    moved = (1.0 - s) * anchors + s * (factors + step) + config.drift_std * innovation
    shifts = np.linalg.norm(moved - factors, axis=1)
    return DynamicsStep(
        factors=moved, mean_shift=float(shifts.mean()) if len(shifts) else 0.0,
        max_shift=float(shifts.max()) if len(shifts) else 0.0, influenced=int((counts > 0).sum()), radicalised=pushed,
    )


def current_factors(citizens: Sequence[Citizen], structure: LatentStructure) -> np.ndarray:
    """Every citizen's factors, row i for citizen_id i: where they have moved to, or their
    initial factors before the first update."""
    return np.array([
        citizen.latent_factors if citizen.latent_factors is not None else structure.anchors[citizen.citizen_id]
        for citizen in citizens
    ], dtype=float).reshape(-1, structure.anchors.shape[1])


def shift_stance(citizen: Citizen, structure: LatentStructure, issue: int, logit: float) -> None:
    """ADR-017: move one citizen `logit` (signed, toward the issue's high pole) on one issue, along that
    issue's loading, so the issues that load with it move too; the dynamics then pull them back."""
    loading = structure.loadings[issue]
    factors = current_factors([citizen], structure) + logit * loading / float(loading @ loading)
    citizen.latent_factors = tuple(float(x) for x in factors[0])
    citizen.issue_positions = tuple(float(x) for x in structure.positions(factors, [citizen.citizen_id])[0])


def _mood(citizens: Sequence[Citizen], factors: np.ndarray) -> Mood:
    """Each citizen's anger (0 where untracked) and shock salience, and the sitting president's factors."""
    president = next((i for i, c in enumerate(citizens) if c.office == Office.PRESIDENT), None)
    return Mood(
        anger=np.array([c.anger or 0.0 for c in citizens], dtype=float),
        salience=np.array([c.event_salience for c in citizens], dtype=float),
        president=None if president is None else factors[president],
    )


def apply_dynamics(
    citizens: Sequence[Citizen], structure: LatentStructure, edges: NeighbourEdges, config: DynamicsConfig,
    rng: np.random.Generator,
) -> DynamicsStep:
    """Move every citizen's factors one update and recompute their issue positions."""
    if [c.citizen_id for c in citizens] != list(range(len(citizens))):
        raise ValueError("apply_dynamics needs the whole population, ordered by citizen_id")
    factors = current_factors(citizens, structure)
    step = update_latent_factors(factors, structure.anchors, edges, config, rng, mood=_mood(citizens, factors))
    positions = structure.positions(step.factors)
    for citizen, factors, issue_positions in zip(citizens, step.factors, positions):
        citizen.latent_factors = tuple(float(x) for x in factors)
        citizen.issue_positions = tuple(float(x) for x in issue_positions)
    return step
