"""
api.domain.polity.catalogue -- plan-scenarios-v1 step 6, the catalogue of scenarios: the pieces that need no run.

A Latin hypercube over the institutional and environmental settings (`DIMENSIONS`), each point turned into a config
(`apply_point`), and PRIM (Friedman and Fisher 1999; the peeling half of what EMA Workbench ships) to find the box of
settings in which a given archetype is frequent. Running the points and reading the digests is
`scripts/run_polity_catalogue.py`; this module is pure and takes plain rows, so it is tested without a run.

PRIM here is peeling only, one dimension at a time: a numeric dimension loses its lowest or highest `alpha` share of the
points in the box, a categorical one loses a level, whichever leaves the highest share of the target class. It stops at
`min_support`. There is no pasting step, and no cross-validation of the box: the boxes are descriptions of a sample, to be
read with their coverage and density, not tests.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.stats import qmc

from api.domain.polity.config import PolityConfig

Value = float | str


@dataclass(frozen=True)
class Dimension:
    """One setting the catalogue varies: a dotted path into `PolityConfig`, and either a range or a set of levels."""

    name: str
    path: str
    low: float = 0.0
    high: float = 0.0
    levels: tuple[str, ...] = ()
    note: str = ""

    @property
    def categorical(self) -> bool:
        return bool(self.levels)


DIMENSIONS: tuple[Dimension, ...] = (
    Dimension("method", "institutions.presidential_method", levels=("plurality", "two_round", "irv", "borda", "copeland", "schulze")),
    Dimension("threshold", "institutions.electoral_threshold", 0.0, 0.10),
    Dimension("seat_rule", "institutions.seat_allocation", levels=("dhondt", "sainte_lague", "largest_remainder")),
    Dimension("recall_floor", "legitimacy.recall_floor", 0.1, 0.4),
    Dimension("petition_threshold", "petition.signature_threshold", 0.05, 0.40),
    Dimension("scandal_rate", "events.scandal_rate_per_tick", 0.0, 0.15),
    Dimension("economy_sigma", "events.economy_ar1_sigma", 0.05, 0.30),
    Dimension(
        "polarization_pressure", "dynamics.radical_step", 0.0, 1.0,
        note="no knob sets the electorate's initial spread: this is how hard angry citizens push away from the president (ADR-033)",
    ),
    Dimension("ambition", "citizens.ambition_dist", levels=("beta(2,8)", "beta(2,3)", "beta(1,1)")),
    Dimension(
        "amendment_threshold", "constitution.amendment_threshold", 0.5, 0.9,
        note="amendments are proposed by the model's agents: expected to be inert on the rule-only twin, so it is the negative control",
    ),
)


def sample(count: int, seed: int, dimensions: Sequence[Dimension] = DIMENSIONS) -> list[dict[str, Value]]:
    """A Latin hypercube of `count` points: each range is cut into `count` equal strata with one point in each, each
    set of levels is cut the same way and mapped onto the levels, so every level is met (nearly) equally often."""
    unit = qmc.LatinHypercube(d=len(dimensions), seed=seed).random(count)
    points: list[dict[str, Value]] = []
    for row in unit:
        point: dict[str, Value] = {}
        for dim, u in zip(dimensions, row):
            point[dim.name] = dim.levels[min(int(u * len(dim.levels)), len(dim.levels) - 1)] if dim.categorical else dim.low + float(u) * (dim.high - dim.low)
        points.append(point)
    return points


def _replace_path(obj: Any, parts: Sequence[str], value: Value) -> Any:
    if len(parts) == 1:
        return dataclasses.replace(obj, **{parts[0]: value})
    return dataclasses.replace(obj, **{parts[0]: _replace_path(getattr(obj, parts[0]), parts[1:], value)})


def apply_point(config: PolityConfig, point: Mapping[str, Value], dimensions: Sequence[Dimension] = DIMENSIONS) -> PolityConfig:
    """`config` with each dimension's setting replaced by the point's value."""
    for dim in dimensions:
        config = _replace_path(config, dim.path.split("."), point[dim.name])
    return config


@dataclass(frozen=True)
class Box:
    """A region of the settings in which the target is frequent: `restrictions` are the dimensions it cuts, as
    (low, high) for a range (-inf or inf on the side it leaves open) and as the levels kept for a categorical one."""

    restrictions: Mapping[str, tuple[float, float] | tuple[str, ...]]
    support: float
    """Share of all the points inside the box."""
    density: float
    """Share of the target class among the points inside."""
    coverage: float
    """Share of all the target points inside."""
    path: Sequence[tuple[float, float]] = field(default_factory=tuple, compare=False)
    """The peeling path as (support, density) at each step."""


def prim(
    points: Sequence[Mapping[str, Value]], target: Sequence[bool], dimensions: Sequence[Dimension] = DIMENSIONS,
    alpha: float = 0.1, min_support: float = 0.05, min_hits: int = 5,
) -> Box | None:
    """Peel the box down to `min_support` of the points, each step the cut that leaves the highest share of `target`,
    and return the box on the path with the highest density (the earliest on a tie, so the larger) among those holding
    at least `min_hits` target points (or all of them, if the class is smaller): a box of two lucky points is not a
    finding. A cut side that was never cut is open (-inf or inf). None when nothing is in the target class or the box
    could not be peeled at all."""
    hit = np.asarray(target, dtype=bool)
    total, positives = len(hit), int(hit.sum())
    if not total or not positives:
        return None
    columns = {
        dim.name: np.array([p[dim.name] for p in points], dtype=object if dim.categorical else float) for dim in dimensions
    }
    inside = np.ones(total, dtype=bool)
    bounds: dict[str, list[float]] = {d.name: [d.low, d.high] for d in dimensions if not d.categorical}
    kept: dict[str, set[str]] = {d.name: set(d.levels) for d in dimensions if d.categorical}
    needed = min(min_hits, positives)
    best, path = (1.0, positives / total, dict(bounds), {k: set(v) for k, v in kept.items()}), [(1.0, positives / total)]
    while inside.sum() / total > min_support:
        candidate = _best_cut(columns, dimensions, inside, hit, alpha)
        if candidate is None:
            break
        inside, name, cut = candidate
        if isinstance(cut, tuple):
            bounds[name] = [max(bounds[name][0], cut[0]), min(bounds[name][1], cut[1])]
        else:
            kept[name].discard(cut)
        support, density = float(inside.sum()) / total, float(hit[inside].mean())
        path.append((support, density))
        if support >= min_support and density > best[1] and int(hit[inside].sum()) >= needed:
            best = (support, density, {k: list(v) for k, v in bounds.items()}, {k: set(v) for k, v in kept.items()})
    support, density, final_bounds, final_kept = best
    if support == 1.0:
        return None
    restrictions: dict[str, tuple[float, float] | tuple[str, ...]] = {}
    for dim in dimensions:
        if dim.categorical and final_kept[dim.name] != set(dim.levels):
            restrictions[dim.name] = tuple(level for level in dim.levels if level in final_kept[dim.name])
        elif not dim.categorical and final_bounds[dim.name] != [dim.low, dim.high]:
            low, high = final_bounds[dim.name]
            restrictions[dim.name] = (float("-inf") if low == dim.low else float(low), float("inf") if high == dim.high else float(high))
    return Box(restrictions=restrictions, support=support, density=density, coverage=density * support * total / positives, path=tuple(path))


def _best_cut(
    columns: Mapping[str, np.ndarray], dimensions: Sequence[Dimension], inside: np.ndarray, hit: np.ndarray, alpha: float,
) -> tuple[np.ndarray, str, tuple[float, float] | str] | None:
    """The peel that leaves the highest share of the target (the larger remainder on a tie), among those that take
    at least one point out and leave at least one in."""
    best: tuple[float, int, np.ndarray, str, tuple[float, float] | str] | None = None
    for dim in dimensions:
        column = columns[dim.name]
        options: list[tuple[np.ndarray, tuple[float, float] | str]] = []
        if dim.categorical:
            options = [(inside & (column != level), level) for level in dim.levels if (inside & (column == level)).any()]
        else:
            low, high = float(np.quantile(column[inside], alpha)), float(np.quantile(column[inside], 1 - alpha))
            options = [(inside & (column >= low), (low, float("inf"))), (inside & (column <= high), (float("-inf"), high))]
        for remaining, cut in options:
            kept = int(remaining.sum())
            if kept == 0 or kept == int(inside.sum()):
                continue
            score = (float(hit[remaining].mean()), kept)
            if best is None or score > (best[0], best[1]):
                best = (score[0], kept, remaining, dim.name, cut)
    return None if best is None else (best[2], best[3], best[4])


def relabel(row: Mapping[str, Any], realignment_spreads: float, churn_volatility: float = 0.4, alternation_count: int = 2) -> str:
    """The archetype a catalogue row would read as at another realignment threshold. Only the four rules from realignment
    down are re-applied, so it is exact for a row those four label (the catalogue's runs never meet the earlier ones: a row
    labelled by one of those keeps its label)."""
    if row["archetype"] not in ("realignment", "churn", "alternation", "stasis"):
        return str(row["archetype"])
    if row["max_rel_shift"] >= realignment_spreads:
        return "realignment"
    if row["max_volatility"] >= churn_volatility:
        return "churn"
    return "alternation" if row["alternations"] >= alternation_count else "stasis"
