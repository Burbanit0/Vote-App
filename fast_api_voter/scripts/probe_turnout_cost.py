"""ADR-039's table: `vote.turnout_cost` from 0 to 0.06 on the catalogue's own points (the first --points of
`catalogue.sample(1000, 1)`, run seed 100,000 + index, 15 years, 100 citizens, the rule-only scenario twin, everything
else at the profile), with the mean turnout, the share of runs whose mean turnout is inside the plausibility band and
above it, and what the cost does to legislative volatility and re-election. It prints no archetypes: ADR-039's rule
picks the cost from turnout alone.

Usage (from fast_api_voter/):
    python scripts/probe_turnout_cost.py --points 60 --out /tmp/turnout

A reading, not a pre-registered experiment: one run per point. The runs are probe_economic_voting.py's.
"""
from __future__ import annotations

import argparse
import multiprocessing
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.trajectory import PLAUSIBILITY_BAND  # noqa: E402
from probe_economic_voting import run_all  # noqa: E402

COSTS = (0.0, 0.01, 0.02, 0.03, 0.04, 0.06)


def line(cost: float, runs: list[dict[str, Any]]) -> str:
    low, high = PLAUSIBILITY_BAND["turnout"]
    vlow, vhigh = PLAUSIBILITY_BAND["volatility"]
    turnout = [statistics.mean(r["turnout"]) for r in runs]
    volatility = [v for r in runs for v in r["volatility"]]
    volatile_in_band = sum(vlow <= statistics.mean(r["volatility"]) <= vhigh for r in runs if r["volatility"]) / len(runs)
    reelected = sum(r["reelections"] for r in runs) / max(1, sum(r["terms"] - 1 for r in runs))
    return (
        f"| {cost} | {statistics.mean(turnout):.3f} | {sum(low <= t <= high for t in turnout) / len(runs):.0%} | "
        f"{sum(t > high for t in turnout) / len(runs):.0%} | {statistics.mean(volatility):.3f} | {volatile_in_band:.0%} | {reelected:.2f} |"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--points", type=int, default=60)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    args = parser.parse_args(argv)
    arms = {str(cost): {"vote": {"turnout_cost": cost}} for cost in COSTS}
    print("| turnout_cost | mean turnout | runs with mean turnout in band | above the band | mean volatility | volatility in band | re-election share |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for cost, runs in zip(COSTS, run_all(arms, args.points, args.out, args.workers).values()):
        print(line(cost, runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
