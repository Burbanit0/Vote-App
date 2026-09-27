"""Every polity run on disk as one DuckDB table (S5.1). See api/domain/polity/run_registry.py.

Usage (from fast_api_voter/):
    python scripts/run_registry.py                      # all scripts/*_runs, default columns
    python scripts/run_registry.py --root ../../Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs
    python scripts/run_registry.py --sql "SELECT run_id, fallbacks FROM runs WHERE engine = 'llm'"
    python scripts/run_registry.py --export scripts/runs.duckdb   # keep the table for later queries
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.run_registry import build_registry  # noqa: E402

DEFAULT_SQL = """
SELECT run_id, generation, outcome, engine, population, years, seed,
       ticks_reached || '/' || ticks_planned AS ticks,
       round(office_occupancy, 3) AS occupancy, fallbacks, round(elapsed_seconds / 3600, 2) AS hours
FROM runs ORDER BY run_dir
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, action="append", default=[], help="another directory to scan (repeatable)")
    parser.add_argument("--sql", default=DEFAULT_SQL, help="query over the `runs` table")
    parser.add_argument("--export", type=Path, default=None, help="write the table to this DuckDB file")
    args = parser.parse_args(argv)

    scripts_dir = Path(__file__).resolve().parent
    roots = sorted(scripts_dir.glob("*_runs")) + args.root
    connection = duckdb.connect(str(args.export)) if args.export else None
    con = build_registry(roots, connection)
    result = con.execute(args.sql)
    headers = [column[0] for column in result.description]
    rows = result.fetchall()
    print("| " + " | ".join(headers) + " |")
    print("|" + "---|" * len(headers))
    for row in rows:
        print("| " + " | ".join("" if value is None else str(value) for value in row) + " |")
    print(f"\n{len(rows)} rows" + (f"; table written to {args.export}" if args.export else ""), file=sys.stderr)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
