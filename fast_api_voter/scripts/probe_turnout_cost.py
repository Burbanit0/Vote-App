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
from probe_economic_voting import read, run_all, summary  # noqa: E402

COSTS = (0.0, 0.01, 0.02, 0.03, 0.04, 0.06)


def line(cost: str, runs: list[dict[str, Any]]) -> str:
    ran, note = read(runs)
    low, high = PLAUSIBILITY_BAND["turnout"]
    turnout = [statistics.mean(r["turnout"]) for r in ran if r["turnout"]]
    s = summary(ran)
    in_band, above = (sum(low <= t <= high for t in turnout) / len(turnout), sum(t > high for t in turnout) / len(turnout)) if turnout else (float("nan"),) * 2
    return f"| {cost}{note} | {s['turnout']:.3f} | {in_band:.0%} | {above:.0%} | {s['volatility']:.3f} | {s['volatility_in_band']:.0%} | {s['reelected']:.2f} |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--points", type=int, default=60)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, (multiprocessing.cpu_count() or 2) - 2))
    args = parser.parse_args(argv)
    arms = {str(cost): {"vote": {"turnout_cost": cost}} for cost in COSTS}
    print("| turnout_cost | mean turnout | runs with mean turnout in band | above the band | mean volatility | volatility in band | re-election share |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for cost, runs in run_all(arms, args.points, args.out, args.workers).items():
        print(line(cost, runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
