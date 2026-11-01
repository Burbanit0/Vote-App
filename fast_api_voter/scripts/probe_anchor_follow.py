"""ADR-032 option D's table, on the CPU, without a model: forum shifts are emulated (the ADR's own prescription, since
the rule-only twin has no forum), and `dynamics.anchor_follow` is swept against the control (0), the same seeds in
every arm. Three of the ADR's pre-registered outcomes:

  (1) mean yearly displacement of the citizens' issue positions in years 5-8 (does opinion keep moving);
  (2) the share of a shift still there one year later, and after eight (a single shift to everyone, nothing else,
      measured along it);
  (3) the spread of positions per issue at year 8 over year 0 (ADR-012's D2: at least 0.8, no collapse).

Shifts: each tick each citizen shifts with chance --rate (0.01: the forum's ten speakers in a hundred, 4 to 14% of whose
turns changed a mind on the 8B), by 0.25 logit, toward the high pole 85% of the time, on issue 0 half the time and a
uniform issue otherwise (the 8B's shifts concentrate on one issue and one pole).

Usage (from fast_api_voter/):
    python scripts/probe_anchor_follow.py
    python scripts/probe_anchor_follow.py --follow 0 --follow 0.5 --rate 0.02

A reading, not the live check: the ADR's paired 8B runs are still to do, and the emulated rate, issue and pole are
the investigation's measurements, not a model's.
"""
from __future__ import annotations

import argparse
import dataclasses
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.citizen import Citizen, LatentStructure, generate_population, latent_structure  # noqa: E402
from api.domain.polity.config import DynamicsConfig  # noqa: E402
from api.domain.polity.opinion_dynamics import NeighbourEdges, apply_dynamics, current_factors, shift_stance  # noqa: E402
from api.domain.polity.social_graph import generate_social_graph  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

FOLLOWS = (0.0, 0.1, 0.25, 0.5, 1.0)
SEEDS = range(1, 11)
TICKS_PER_YEAR, YEARS, STEP, HIGH_POLE, ON_ISSUE_0 = 4, 8, 0.25, 0.85, 0.5


def _world(seed: int, population: int) -> tuple[list[Citizen], LatentStructure, NeighbourEdges, DynamicsConfig]:
    config = _flagship_config(
        engine="deterministic", years=YEARS, population=population, seats=15, seed=seed, output_dir=Path("/nonexistent"),
        max_batch_replays=0, provider=None, workers=1, profile="exploration",
    )
    citizens_config = dataclasses.replace(config.citizens, static_population=False)
    citizens = generate_population(citizens_config, population, seed)
    structure = latent_structure(citizens_config, population, seed)
    for c, row in zip(citizens, structure.anchors):
        c.latent_factors = tuple(float(x) for x in row)
    graph = generate_social_graph(dataclasses.replace(config.social_graph, enabled=True), population, seed)
    return citizens, structure, NeighbourEdges.from_graph(graph), dataclasses.replace(config.dynamics, enabled=True)


def _positions(citizens: Sequence[Citizen]) -> np.ndarray:
    return np.array([c.issue_positions for c in citizens])


def run_seed(seed: int, follow: float, rate: float, population: int) -> tuple[float, float]:
    """(displacement in years 5-8, spread ratio at year 8) with emulated shifts."""
    citizens, structure, edges, dynamics = _world(seed, population)
    shifts, dyn = np.random.default_rng([seed, 1]), np.random.default_rng([seed, 2])
    n_issues = len(citizens[0].issue_positions)
    start, year_marks = _positions(citizens), [_positions(citizens)]
    for tick in range(1, TICKS_PER_YEAR * YEARS + 1):
        for citizen in citizens:  # drawn for every citizen every tick, so the arms see the same shifts
            hit, on_zero, high, other = shifts.random(), shifts.random(), shifts.random(), int(shifts.integers(n_issues))
            if hit < rate:
                shift_stance(citizen, structure, 0 if on_zero < ON_ISSUE_0 else other, STEP if high < HIGH_POLE else -STEP, follow)
        apply_dynamics(citizens, structure, edges, dynamics, dyn)
        if tick % TICKS_PER_YEAR == 0:
            year_marks.append(_positions(citizens))
    moved = [float(np.linalg.norm(b - a, axis=1).mean()) for a, b in zip(year_marks[4:], year_marks[5:])]  # years 5-8
    return statistics.mean(moved), float((year_marks[-1].std(axis=0) / start.std(axis=0)).mean())


def kept_after(seed: int, follow: float, population: int, years: int) -> float:
    """One shift to everyone on issue 3 and nothing else: the share of it along its direction after `years` years."""
    citizens, structure, edges, dynamics = _world(seed, population)
    before = current_factors(citizens, structure)
    for citizen in citizens:
        shift_stance(citizen, structure, 3, STEP, follow)
    direction = (current_factors(citizens, structure) - before).mean(axis=0)
    dyn = np.random.default_rng([seed, 2])
    for _ in range(TICKS_PER_YEAR * years):
        apply_dynamics(citizens, structure, edges, dynamics, dyn)
    return float(((current_factors(citizens, structure) - before).mean(axis=0) @ direction) / (direction @ direction))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--follow", type=float, action="append", default=[], help="anchor_follow (repeatable); 0, the control, always runs first")
    parser.add_argument("--rate", type=float, default=0.01)
    parser.add_argument("--population", type=int, default=100)
    args = parser.parse_args(argv)
    follows = [0.0] + [f for f in (args.follow or FOLLOWS) if f != 0.0]  # the control is always the first arm
    control: list[float] = []
    for follow in follows:
        runs = [run_seed(seed, follow, args.rate, args.population) for seed in SEEDS]
        kept = [kept_after(seed, follow, args.population, 1) for seed in SEEDS]
        kept8 = [kept_after(seed, follow, args.population, YEARS) for seed in SEEDS]
        moved = [m for m, _ in runs]
        control = control or moved
        versus = "the control" if follow == 0 else f"above the control in {sum(m > c for m, c in zip(moved, control))}/{len(moved)} seeds"
        print(f"anchor_follow {follow}: displacement y5-8 {statistics.mean(moved):.4f} ({versus}) shift kept after a year {statistics.mean(kept):.2f}, "
              f"after {YEARS} years {statistics.mean(kept8):.2f}, spread ratio {statistics.mean(s for _, s in runs):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
