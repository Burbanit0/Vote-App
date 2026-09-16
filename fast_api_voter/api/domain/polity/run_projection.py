"""Where each citizen, pledge and party sits on a run's two-dimensional map (the run
explorer's population view, design doc §14.2).

A factor_structure population was drawn from two latent factors
(citizen.latent_structure), so the map uses those factors directly: a citizen sits at
their factors, redrawn from the run's seed and checked against the tick-0 census before
being trusted. A point that is not a citizen's own view -- a pledge, a drifted
officeholder, a party platform -- is placed by least squares in logit space against the
same loadings: an officeholder at their own factors plus the projected drift, a party
platform at its fitted factors. A uniform population, or one whose redrawn structure does
not reproduce the census, falls back to the census's first two principal components.

With opinion dynamics on (S4.3) the factors move every tick but only the yearly census
records them, so citizens move once a year on the map (`positions` "yearly").
"""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import numpy as np

from api.domain.polity.citizen import LatentStructure, latent_structure
from api.domain.polity.config import CitizensConfig, load_config

TOP_ISSUES = 3
_LOGIT_EPS = 1e-6
_CENSUS_TOLERANCE = 1e-9


@dataclass(frozen=True)
class IssueWeight:
    issue: int
    weight: float


@dataclass(frozen=True)
class Projection:
    method: Literal["latent", "pca"]
    positions: Literal["static", "yearly"]
    axes: tuple[tuple[IssueWeight, ...], tuple[IssueWeight, ...]]
    """The issues loading most on each axis, strongest first, with their signed weight."""
    citizen_xy: Mapping[int, np.ndarray]
    """year -> (population, 2); a static run has year 0 only."""
    issue_positions: Mapping[int, np.ndarray]
    """year -> (population, issue_count), the census the map was read from."""
    loadings: np.ndarray | None = None
    mean_residual: np.ndarray | None = None
    mean: np.ndarray | None = None
    components: np.ndarray | None = None

    def census_year(self, year: int) -> int:
        """The latest census year at or before `year` (a run can outlive its last census)."""
        return max((y for y in self.citizen_xy if y <= year), default=min(self.citizen_xy))

    def citizens_at(self, year: int) -> np.ndarray:
        return self.citizen_xy[self.census_year(year)]

    def holder_xy(self, citizen_id: int, year: int, position: Sequence[float] | np.ndarray) -> tuple[float, float]:
        """A citizen's pledge or revealed position: on the latent map, their own factors
        plus the drift from their own view; on the PCA map, the position projected."""
        census = self.census_year(year)
        if self.loadings is None:
            return self.point_xy(position)
        own = self.issue_positions[census][citizen_id]
        drift = _fit_factors(self.loadings, _logit(np.asarray(position)) - _logit(own))
        x, y = self.citizen_xy[census][citizen_id] + drift
        return float(x), float(y)

    def point_xy(self, position: Sequence[float] | np.ndarray) -> tuple[float, float]:
        """A position that belongs to no citizen, such as a party platform."""
        point = np.asarray(position, dtype=float)
        if self.loadings is not None and self.mean_residual is not None:
            x, y = _fit_factors(self.loadings, _logit(point) - self.mean_residual)
        else:
            assert self.mean is not None and self.components is not None
            x, y = (point - self.mean) @ self.components.T
        return float(x), float(y)


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, _LOGIT_EPS, 1.0 - _LOGIT_EPS)
    result: np.ndarray = np.log(clipped / (1.0 - clipped))
    return result


def _fit_factors(loadings: np.ndarray, target: np.ndarray) -> np.ndarray:
    solution: np.ndarray = np.linalg.lstsq(loadings, target, rcond=None)[0]
    return solution


def _top_issues(weights: np.ndarray) -> tuple[IssueWeight, ...]:
    order = np.argsort(-np.abs(weights), kind="stable")[:TOP_ISSUES]
    return tuple(IssueWeight(issue=int(j), weight=float(weights[j])) for j in order)


@lru_cache(maxsize=1)
def _shipped_citizens() -> CitizensConfig:
    return load_config().citizens


def _redrawn_structure(config: Mapping[str, Any], year_zero: np.ndarray) -> LatentStructure | None:
    """The run's latent structure, when its population was drawn from one and redrawing it
    from the seed reproduces the tick-0 census exactly."""
    citizens = config.get("citizens") or {}
    if citizens.get("position_dist") != "factor_structure":
        return None
    run = config["run"]
    citizens_config = dataclasses.replace(
        _shipped_citizens(), position_dist="factor_structure", issue_count=int(citizens["issue_count"]),
    )
    structure = latent_structure(citizens_config, int(run["population_size"]), int(run["seed"]))
    redrawn = structure.positions(structure.anchors)
    if redrawn.shape != year_zero.shape or not np.allclose(redrawn, year_zero, rtol=0.0, atol=_CENSUS_TOLERANCE):
        return None
    return structure


def _pca(year_zero: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mean and the first two principal directions, each signed so its largest weight is
    positive -- a stable orientation from one run to the next."""
    mean = year_zero.mean(axis=0)
    _, _, vt = np.linalg.svd(year_zero - mean, full_matrices=False)
    components = vt[:2].copy()
    if components.shape[0] < 2:
        components = np.vstack([components, np.zeros((2 - components.shape[0], year_zero.shape[1]))])
    for row in components:
        if row[np.argmax(np.abs(row))] < 0:
            row *= -1.0
    return mean, components


def build_projection(config: Mapping[str, Any], census: Mapping[int, Sequence[Mapping[str, Any]]]) -> Projection:
    """The map for a run, from its config.json mapping and its census rows by year (each
    year's rows ordered by citizen_id)."""
    issue_positions = {year: np.array([row["issue_positions"] for row in rows], dtype=float) for year, rows in census.items()}
    year_zero = issue_positions[0]
    structure = _redrawn_structure(config, year_zero)
    if structure is None:
        mean, components = _pca(year_zero)
        return Projection(
            method="pca", positions="static", axes=(_top_issues(components[0]), _top_issues(components[1])),
            citizen_xy={0: (year_zero - mean) @ components.T}, issue_positions={0: year_zero},
            mean=mean, components=components,
        )
    dynamic = bool((config.get("dynamics") or {}).get("enabled"))
    if dynamic:
        # A citizen's factors are recorded once they first move, so the year-0 census has none.
        citizen_xy = {
            year: np.array([row.get("latent_factors", structure.anchors[i]) for i, row in enumerate(rows)], dtype=float)
            for year, rows in census.items()
        }
        positions = issue_positions
    else:
        citizen_xy, positions = {0: structure.anchors}, {0: year_zero}
    return Projection(
        method="latent", positions="yearly" if dynamic else "static",
        axes=(_top_issues(structure.loadings[:, 0]), _top_issues(structure.loadings[:, 1])),
        citizen_xy=citizen_xy, issue_positions=positions,
        loadings=structure.loadings, mean_residual=structure.residuals.mean(axis=0),
    )

