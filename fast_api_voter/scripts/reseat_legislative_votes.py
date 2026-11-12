#!/usr/bin/env python3
"""Re-seat a finished run's legislative votes at another threshold (PLAN_BEYOND_CI W2.2 item 4).

    python scripts/reseat_legislative_votes.py <run dir>                 # self-check: must reproduce the record
    python scripts/reseat_legislative_votes.py <run dir> --threshold 0.07

<run dir> holds config.json and either events.jsonl beside it (run_simulation's layout) or
run/<run_id>/events.jsonl (the flagship runner's). A fixed --threshold is applied at every
election, overriding the run's own amendments to it (the output says so when there were any).
Exits 1 when, without --threshold, any election's seats differ from the record.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.reseat import reseat  # noqa: E402
from api.domain.polity.run_digest import read_journal_tolerant  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--threshold", type=float, help="the bar to re-seat at (default: the one in force)")
    args = parser.parse_args(argv)
    if args.threshold is not None and not 0 <= args.threshold < 1:
        parser.error(f"--threshold is a share of the vote: 0.07 for 7%, not {args.threshold}")

    founding = json.loads((args.run_dir / "config.json").read_text(encoding="utf-8"))
    beside = args.run_dir / "events.jsonl"
    journals = [beside] if beside.exists() else sorted(args.run_dir.glob("run/*/events.jsonl"))
    if len(journals) != 1:
        raise SystemExit(f"expected events.jsonl or one run/*/events.jsonl under {args.run_dir}, found {len(journals)}")
    events, skipped = read_journal_tolerant(journals[0])
    if skipped:
        print(f"note: {skipped} malformed journal line(s) skipped (a crashed run's last write)")
    rows = reseat(events, founding, threshold=args.threshold)

    print(f"{args.run_dir.name}: {len(rows)} legislative elections, re-seated at "
          f"{'the threshold in force' if args.threshold is None else f'{args.threshold:.1%}'}")
    print("  tick  in force  applied  ENP recorded -> re-seated  parties seated recorded -> re-seated")
    for row in rows:
        print(f"  {row['tick']:>4}  {row['threshold_in_force']:>8.1%}  {row['threshold_applied']:>7.1%}  "
              f"{row['recorded_enp']!s:>12} -> {row['reseated_enp']!s:<9}  "
              f"{row['recorded_parties_seated']:>14} -> {row['reseated_parties_seated']}")
    if args.threshold is not None and len({row["threshold_in_force"] for row in rows}) > 1:
        print("note: the run amended its threshold; the fixed bar above replaced every value in force")
    if args.threshold is None:
        differing = [row["tick"] for row in rows if row["recorded_seats"] != row["reseated_seats"]]
        print(f"self-check: {'every election reproduced' if not differing else f'seats differ at ticks {differing}'}")
        return 1 if differing else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
