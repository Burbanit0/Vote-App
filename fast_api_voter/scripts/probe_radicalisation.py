"""ADR-033's table: for each (drift, push, narrowing) arm, ten seeds of the rule-only scenario twin, and what the
digest says about them (panel stability D1, the spread of views kept D2, the population's mean shift, how many
citizens were pushed per update, the archetypes and the divergence test, the seeds inside the plausibility band).

Usage (from fast_api_voter/):
    python scripts/probe_radicalisation.py --output-dir /tmp/probe
    python scripts/probe_radicalisation.py --output-dir /tmp/probe --arm 0.18,0.5,0.3 --arm 0.02,0,0

With no --arm, ADR-033's eight arms. A reading, not a pre-registered experiment: one population size, one seed set.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.run_digest import build_digest, read_journal_tolerant  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import divergence_by_year, divergence_verdict, diversity, pairwise_distances  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

ADR_ARMS = ((0.02, 0.0, 0.0), (0.20, 0.0, 0.0), (0.02, 1.0, 0.5), (0.15, 1.0, 0.5), (0.15, 2.0, 0.5),
            (0.15, 0.5, 0.5), (0.15, 0.5, 0.0), (0.18, 0.5, 0.3))
SEEDS = range(1, 11)


def spread_kept(snapshots: list[dict[str, Any]]) -> float | None:
    """D2: each latent factor's standard deviation at the last census over its value at year 1 (the year-0 census
    carries no factors), averaged over the factors; None without two censuses that carry them."""
    by_year: dict[int, list[list[float]]] = {}
    for row in sorted(snapshots, key=lambda r: (r["year"], r["citizen_id"])):
        if row.get("latent_factors") is not None:
            by_year.setdefault(int(row["year"]), []).append(row["latent_factors"])
    if 1 not in by_year or max(by_year) == 1:
        return None
    return float(np.mean(np.array(by_year[max(by_year)]).std(axis=0) / np.array(by_year[1]).std(axis=0)))


def run_arm(drift: float, push: float, narrowing: float, output_dir: Path) -> dict[str, Any]:
    series, labels, in_band, shifts, stability, spreads, pushed = {}, {}, 0, [], [], [], []
    for seed in SEEDS:
        config = _flagship_config(
            engine="deterministic", years=8, population=100, seats=15, seed=seed, output_dir=output_dir / f"{drift}-{push}-{narrowing}" / str(seed),
            max_batch_replays=0, provider=None, workers=1, profile="scenario",
        )
        config = dataclasses.replace(config, dynamics=dataclasses.replace(config.dynamics, drift_std=drift, radical_step=push, anger_narrows_bound=narrowing))
        journal = run_simulation(config, run_id="probe")
        trajectory = build_digest(journal, config, run_id="probe", outcome="completed", resume=False)["trajectory"]
        snapshots, _ = read_journal_tolerant(journal.parent / "snapshots.jsonl")
        events, _ = read_journal_tolerant(journal)
        series[f"seed {seed}"], labels[f"seed {seed}"] = trajectory["yearly"], trajectory["archetype"]
        in_band += not trajectory["plausibility_failed"]
        shifts.append(trajectory["polarization"][-1]["mean_shift"])
        stability.append(trajectory["panel_stability"])
        spreads.append(spread_kept(snapshots))
        pushed.append(statistics.mean(e["payload"].get("radicalised", 0) for e in events if e["event_type"] == "opinion_dynamics_step"))
    ensemble, by_year = diversity(labels, pairwise_distances(series)), divergence_by_year(series)
    return {
        "arm": (drift, push, narrowing), "D1": statistics.mean(stability), "D2": statistics.mean(s for s in spreads if s is not None),
        "shift": statistics.mean(shifts), "pushed": statistics.mean(pushed), "archetypes": ensemble["archetypes"],
        "entropy": ensemble["archetype_entropy_bits"], "distance": (by_year[0], by_year[-1]), "in_band": in_band,
        "verdict": divergence_verdict(by_year, ensemble, in_band / len(SEEDS)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--arm", action="append", default=[], help="drift,push,narrowing (repeatable)")
    args = parser.parse_args(argv)
    arms = [tuple(float(x) for x in a.split(",")) for a in args.arm] or list(ADR_ARMS)
    for drift, push, narrowing in arms:
        r = run_arm(drift, push, narrowing, args.output_dir)
        print(json.dumps({**r, "verdict": r["verdict"]}, default=str))
        print(f"drift {drift} push {push} narrowing {narrowing}: D1 {r['D1']:.3f} D2 {r['D2']:.2f} shift {r['shift']:.3f} "
              f"pushed/update {r['pushed']:.1f} {r['archetypes']} {r['entropy']:.2f} bits distance {r['distance'][0]:.2f}->{r['distance'][1]:.2f} in band {r['in_band']}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
