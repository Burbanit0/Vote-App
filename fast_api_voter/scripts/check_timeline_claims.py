"""Check a run narrative's anchored claims against its journal (S5.3).
See api/domain/polity/timeline_claims.py for the anchor syntax.

Usage (from fast_api_voter/):
    python scripts/check_timeline_claims.py scripts/flagship_runs/<run>/run/<run>
    python scripts/check_timeline_claims.py <run_dir> --timeline draft.md   # check a draft before writing it

Exit 1 when an anchor is contradicted by the journal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES  # noqa: E402
from api.domain.polity.timeline_claims import check_timeline, read_events_by_id  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help="the directory holding events.jsonl")
    parser.add_argument("--timeline", type=Path, default=None, help="the narrative to check (default: run_dir/TIMELINE.md)")
    args = parser.parse_args(argv)
    timeline = args.timeline or args.run_dir / "TIMELINE.md"
    report = check_timeline(
        timeline.read_text(encoding="utf-8"), read_events_by_id(args.run_dir / "events.jsonl"), INSTITUTIONAL_EVENT_TYPES,
    )
    for problem in report.problems:
        print(problem)
    print(
        f"{report.anchors} anchors, {len(report.problems)} contradicted; "
        f"{report.institutional_anchored}/{report.institutional_events} institutional events anchored"
    )
    if report.anchors == 0:
        print("no anchors: nothing in this narrative is checked")
    return 1 if report.problems else 0


if __name__ == "__main__":
    sys.exit(main())
