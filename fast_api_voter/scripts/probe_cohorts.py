"""ADR-035's table: for each (replacement per year, newcomer spread) arm, ten seeds of the rule-only scenario twin over
a long run, and what the digest and the census say about them: how much of the population is a newcomer, whether the
spread of views holds across generations (the newcomer noise's job), panel stability among the people who stayed, the
population's mean shift, the archetypes and the divergence test.

Usage (from fast_api_voter/):
    python scripts/probe_cohorts.py --output-dir /tmp/probe
    python scripts/probe_cohorts.py --output-dir /tmp/probe --years 30 --arm 0.03,0.5 --arm 0,0.5

An arm is `rate,spread`. With no --arm, ADR-035's. A reading, not a pre-registered experiment: one population size,
one seed set.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.checkpoint import load_checkpoint  # noqa: E402
from api.domain.polity.run_digest import build_digest, read_journal_tolerant  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import divergence_by_year, divergence_verdict, diversity, pairwise_distances  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

ADR_ARMS = ((0.0, 0.5), (0.03, 0.2), (0.03, 0.35), (0.03, 0.5), (0.03, 0.8), (0.06, 0.5))
SEEDS = range(1, 11)


def spread_kept(snapshots: list[dict[str, Any]]) -> float | None:
    """The standard deviation of each latent factor at the last census over its value at year 1, averaged over the
    factors; None without two censuses that carry them."""
    by_year: dict[int, list[list[float]]] = {}
    for row in sorted(snapshots, key=lambda r: (r["year"], r["citizen_id"])):
        if row.get("latent_factors") is not None:
            by_year.setdefault(int(row["year"]), []).append(row["latent_factors"])
    if 1 not in by_year or max(by_year) == 1:
        return None
    return float(np.mean(np.array(by_year[max(by_year)]).std(axis=0) / np.array(by_year[1]).std(axis=0)))


def run_arm(rate: float, spread: float, years: int, output_dir: Path) -> dict[str, Any]:
    series, labels, in_band = {}, {}, 0
    failed: collections.Counter[str] = collections.Counter()
    stability: list[float] = []
    spreads: list[float] = []
    shifts: list[float] = []
    newcomers: list[float] = []
    for seed in SEEDS:
        config = _flagship_config(
            engine="deterministic", years=years, population=100, seats=15, seed=seed, output_dir=output_dir / f"{rate}-{spread}" / str(seed),
            max_batch_replays=0, provider=None, workers=1, profile="scenario",
        )
        config = dataclasses.replace(config, citizens=dataclasses.replace(
            config.citizens, static_population=rate == 0, replacement_per_year=rate, newcomer_spread=spread,
        ))
        journal = run_simulation(config, run_id="probe")
        trajectory = build_digest(journal, config, run_id="probe", outcome="completed", resume=False)["trajectory"]
        snapshots, _ = read_journal_tolerant(journal.parent / "snapshots.jsonl")
        citizens = load_checkpoint(journal.parent / "checkpoint.json").state.citizens
        series[f"seed {seed}"], labels[f"seed {seed}"] = trajectory["yearly"], trajectory["archetype"]
        in_band += not trajectory["plausibility_failed"]
        failed.update(trajectory["plausibility_failed"])
        if trajectory["panel_stability"] is not None:
            stability.append(trajectory["panel_stability"])
        kept = spread_kept(snapshots)
        if kept is not None:
            spreads.append(kept)
        shifts.append(trajectory["polarization"][-1]["mean_shift"])
        newcomers.append(sum(c.anchor_factors is not None for c in citizens) / len(citizens))
    ensemble, by_year = diversity(labels, pairwise_distances(series)), divergence_by_year(series)
    return {
        "newcomers": statistics.mean(newcomers), "D1": _mean(stability), "D2": _mean(spreads), "shift": statistics.mean(shifts),
        "archetypes": ensemble["archetypes"], "entropy": ensemble["archetype_entropy_bits"], "distance": (by_year[0], by_year[-1]),
        "in_band": in_band, "failed": dict(failed), "verdict": divergence_verdict(by_year, ensemble, in_band / len(SEEDS)),
    }


def _mean(values: list[float]) -> float:
    """NaN when no seed produced the reading (a run too short for a four-year panel), not a crash after hours of runs."""
    return statistics.mean(values) if values else float("nan")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--years", type=int, default=30)
    parser.add_argument("--arm", action="append", default=[], help="rate,spread (repeatable)")
    args = parser.parse_args(argv)
    arms = [tuple(float(x) for x in a.split(",")) for a in args.arm] or list(ADR_ARMS)
    for rate, spread in arms:
        r = run_arm(rate, spread, args.years, args.output_dir)
        print(f"rate {rate} spread {spread} ({args.years}y): newcomers at the end {r['newcomers']:.0%} D1 {r['D1']:.3f} D2 {r['D2']:.2f} "
              f"shift {r['shift']:.3f} {r['archetypes']} {r['entropy']:.2f} bits distance {r['distance'][0]:.2f}->{r['distance'][1]:.2f} "
              f"in band {r['in_band']}/10 (failed checks {r['failed']}) {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
