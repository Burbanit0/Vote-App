"""ADR-036's table: for each (rewire share per year, homophily) arm, ten seeds of the rule-only scenario twin over a long
run, and what the digest and the journal say about them: how far apart the views of two tied citizens are at the start
and at the end (the ties settling among like views), panel stability, the spread of views, the archetypes and the
divergence test. Arm `0,0` is the fixed graph; `share,0` rewires at random, the control for what the pull adds.

Usage (from fast_api_voter/):
    python scripts/probe_rewiring.py --output-dir /tmp/probe
    python scripts/probe_rewiring.py --output-dir /tmp/probe --years 30 --arm 0.2,2 --arm 0,0

An arm is `share,homophily`. With no --arm, ADR-036's. A reading, not a pre-registered experiment: one population size,
one seed set.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.run_digest import build_digest, read_journal_tolerant  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import divergence_by_year, divergence_verdict, diversity, pairwise_distances  # noqa: E402
from probe_cohorts import SEEDS, _mean, spread_kept  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

ADR_ARMS = ((0.0, 0.0), (0.2, 0.0), (0.2, 1.0), (0.2, 2.0), (0.2, 4.0), (0.5, 2.0))


def tie_gaps(journal: Path) -> tuple[float, float] | None:
    """The mean distance between tied citizens' views at the first and at the last rewiring; None for a fixed graph."""
    gaps = [json.loads(line)["payload"]["mean_gap"] for line in journal.read_text().splitlines() if '"ties_rewired"' in line]
    return (gaps[0], gaps[-1]) if gaps else None


def run_arm(share: float, homophily: float, years: int, output_dir: Path) -> dict[str, Any]:
    series, labels, in_band = {}, {}, 0
    failed: collections.Counter[str] = collections.Counter()
    stability: list[float] = []
    spreads: list[float] = []
    first: list[float] = []
    last: list[float] = []
    for seed in SEEDS:
        config = _flagship_config(
            engine="deterministic", years=years, population=100, seats=15, seed=seed, output_dir=output_dir / f"{share}-{homophily}" / str(seed),
            max_batch_replays=0, provider=None, workers=1, profile="scenario",
        )
        config = dataclasses.replace(config, social_graph=dataclasses.replace(
            config.social_graph, evolving=share > 0, rewire_per_year=share, homophily=homophily,
        ))
        journal = run_simulation(config, run_id="probe")
        trajectory = build_digest(journal, config, run_id="probe", outcome="completed", resume=False)["trajectory"]
        snapshots, _ = read_journal_tolerant(journal.parent / "snapshots.jsonl")
        series[f"seed {seed}"], labels[f"seed {seed}"] = trajectory["yearly"], trajectory["archetype"]
        in_band += not trajectory["plausibility_failed"]
        failed.update(trajectory["plausibility_failed"])
        if trajectory["panel_stability"] is not None:
            stability.append(trajectory["panel_stability"])
        kept = spread_kept(snapshots)
        if kept is not None:
            spreads.append(kept)
        if (gaps := tie_gaps(journal)) is not None:
            first.append(gaps[0])
            last.append(gaps[1])
    ensemble, by_year = diversity(labels, pairwise_distances(series)), divergence_by_year(series)
    return {
        "gap": (_mean(first), _mean(last)), "D1": _mean(stability), "D2": _mean(spreads),
        "archetypes": ensemble["archetypes"], "entropy": ensemble["archetype_entropy_bits"], "distance": (by_year[0], by_year[-1]),
        "in_band": in_band, "failed": dict(failed), "verdict": divergence_verdict(by_year, ensemble, in_band / len(SEEDS)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--years", type=int, default=30)
    parser.add_argument("--arm", action="append", default=[], help="share,homophily (repeatable)")
    args = parser.parse_args(argv)
    arms = [tuple(float(x) for x in a.split(",")) for a in args.arm] or list(ADR_ARMS)
    for share, homophily in arms:
        r = run_arm(share, homophily, args.years, args.output_dir)
        print(f"share {share} homophily {homophily} ({args.years}y): tie gap {r['gap'][0]:.2f}->{r['gap'][1]:.2f} D1 {r['D1']:.3f} "
              f"D2 {r['D2']:.2f} {r['archetypes']} {r['entropy']:.2f} bits distance {r['distance'][0]:.2f}->{r['distance'][1]:.2f} "
              f"in band {r['in_band']}/10 (failed checks {r['failed']}) {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
