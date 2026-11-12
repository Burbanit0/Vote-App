"""Group runs by the story they tell (S5.3): each run's institutional arc as a sequence,
runs with the same sequence together. See timeline_claims.story_skeleton.

Usage (from fast_api_voter/):
    python scripts/story_skeletons.py scripts/seed_sweep_runs
    python scripts/story_skeletons.py scripts/seed_sweep_runs --grain terms
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.run_registry import discover_runs  # noqa: E402
from api.domain.polity.timeline_claims import group_by_skeleton, story_skeleton  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", type=Path, nargs="+", help="directories to scan for runs")
    parser.add_argument("--grain", choices=("full", "terms"), default="full")
    args = parser.parse_args(argv)
    skeletons = {}
    for run_dir in discover_runs(args.roots):
        with (run_dir / "events.jsonl").open(encoding="utf-8") as handle:
            events = (json.loads(line) for line in handle if line.strip())
            skeletons[run_dir.name] = story_skeleton(events, grain=args.grain)
    for skeleton, runs in group_by_skeleton(skeletons):
        print(f"## {len(runs)} run(s): {', '.join(runs)}\n{' > '.join(skeleton) or '(no institutional events)'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
