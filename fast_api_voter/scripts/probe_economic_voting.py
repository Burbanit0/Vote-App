"""ADR-038's two tables, on the catalogue's own points (the first --points of `catalogue.sample(1000, 1)`, run seed
100,000 + index, 15 years, 100 citizens, the rule-only scenario twin):

  ablate   one setting changed at a time against the profile (with --base-economic-voting, against the profile at
           that weight: ADR-038's cause was measured against ADR-034's 1.0), and the mean legislative volatility
           (Pedersen, between consecutive legislative elections): what drives it;
  weights  vote.economic_voting from 0 to 1, with the mean volatility, the share of runs whose mean is inside the band,
           the presidential re-election share and the mean turnout: what ADR-038's rule picks from.

Usage (from fast_api_voter/):
    python scripts/probe_economic_voting.py ablate  --points 40 --out /tmp/ev --base-economic-voting 1.0
    python scripts/probe_economic_voting.py weights --points 60 --out /tmp/ev

A reading, not a pre-registered experiment: one run per point.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import multiprocessing
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.catalogue import apply_point, sample  # noqa: E402
from api.domain.polity.run_digest import build_digest  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.trajectory import PLAUSIBILITY_BAND, _votes, pedersen_volatility  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

ARMS: dict[str, dict[str, dict[str, float]]] = {
    "profile": {}, "economic_voting=0": {"vote": {"economic_voting": 0.0}}, "approval=0": {"vote": {"approval": 0.0}},
    "strategic_margin=0": {"vote": {"strategic_margin": 0.0}}, "partisanship=0.03": {"vote": {"partisanship": 0.03}},
    "partisanship=0.05": {"vote": {"partisanship": 0.05}}, "drift_std=0.02": {"dynamics": {"drift_std": 0.02}},
}
WEIGHTS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)


def run_one(job: tuple[int, dict[str, Any], str, dict[str, dict[str, float]], str]) -> dict[str, Any]:
    """One point under one arm's overrides: its legislative volatilities, re-elections, terms and turnouts."""
    index, point, arm, overrides, out = job
    config = _flagship_config(
        engine="deterministic", years=15, population=100, seats=14, seed=100_000 + index, output_dir=Path(out) / arm / str(index),
        max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    config = apply_point(config, point)
    for section, fields in overrides.items():
        config = dataclasses.replace(config, **{section: dataclasses.replace(getattr(config, section), **fields)})
    journal = run_simulation(config, run_id="probe")
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    results = [e for e in events if e["event_type"] == "legislative_result"]
    trajectory = build_digest(journal, config, run_id="probe", outcome="completed", resume=False)["trajectory"]
    return {
        "arm": arm, "volatility": [pedersen_volatility(_votes(a), _votes(b)) for a, b in zip(results, results[1:])],
        "reelections": trajectory["office"]["reelections"], "terms": trajectory["office"]["terms"],
        "turnout": [e["turnout"] for e in trajectory["elections"]],
    }


def run_all(arms: dict[str, dict[str, dict[str, float]]], points: int, out: Path, workers: int) -> dict[str, list[dict[str, Any]]]:
    jobs = [(i, p, arm, overrides, str(out)) for arm, overrides in arms.items() for i, p in enumerate(sample(1000, 1)[:points])]
    with concurrent.futures.ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("fork")) as pool:
        rows = list(pool.map(run_one, jobs))
    return {arm: [r for r in rows if r["arm"] == arm] for arm in arms}


def line(arm: str, runs: list[dict[str, Any]]) -> str:
    low, high = PLAUSIBILITY_BAND["volatility"]
    volatilities = [v for r in runs for v in r["volatility"]]
    in_band = sum(low <= statistics.mean(r["volatility"]) <= high for r in runs if r["volatility"]) / len(runs)
    reelected = sum(r["reelections"] for r in runs) / max(1, sum(r["terms"] - 1 for r in runs))
    turnout = statistics.mean(t for r in runs for t in r["turnout"])
    return f"| {arm} | {statistics.mean(volatilities):.3f} | {in_band:.0%} | {reelected:.2f} | {turnout:.2f} |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("table", choices=("ablate", "weights"))
    parser.add_argument("--points", type=int, default=40)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-economic-voting", type=float, default=None, help="ablate against the profile at this weight")
    parser.add_argument("--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    args = parser.parse_args(argv)
    if args.table == "ablate":
        base = {} if args.base_economic_voting is None else {"economic_voting": args.base_economic_voting}
        arms = {arm: {"vote": base | o.get("vote", {}), **{k: v for k, v in o.items() if k != "vote"}} for arm, o in ARMS.items()}
    else:
        arms = {f"economic_voting={w}": {"vote": {"economic_voting": w}} for w in WEIGHTS}
    print("| arm | mean volatility | runs with their mean in band | re-election share | mean turnout |")
    print("|---|---:|---:|---:|---:|")
    for arm, runs in run_all(arms, args.points, args.out, args.workers).items():
        print(line(arm, runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
