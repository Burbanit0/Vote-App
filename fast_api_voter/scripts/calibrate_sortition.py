"""
scripts/calibrate_sortition.py

v6b Lot 2's own pool-exhaustion finding, reproduced from a real run rather
than left as hand-derived arithmetic: under strict one-shot-ever eligibility
(`Citizen.sortition_terms_served == 0`), the shipped defaults
(`population_size=100`, `seats=30`, `term_years=1`) exhaust the never-served
pool by tick 12 and leave the chamber completely empty from tick 16 onward
if the pool is never relaxed. `select_sortition_chamber` (sortition_chamber
.py) relaxes eligibility to "not currently seated" once the strict pool
can't fill `seats` -- this script confirms that relaxation actually keeps
the chamber near-full for the rest of the run, the claim it exists to
verify, not assume. Same "sweep, run the real production path, report
realized rates in a committed markdown doc" convention as
calibrate_awakening.py/calibrate_events.py.

Fully deterministic -- no LLM, no Ollama required.

Usage:
    python fast_api_voter/scripts/calibrate_sortition.py \
        --results scripts/sortition_calibration_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def _sortition_config(output_dir: Path) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir), index_after_run=False),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )


def _events(journal_path: Path) -> list[dict]:
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def run_sortition_trace(output_dir: Path) -> list[dict]:
    config = _sortition_config(output_dir)
    journal_path = run_simulation(config, run_id="calibration")
    rotations = [e for e in _events(journal_path) if e["event_type"] == "sortition_rotation"]
    seats = config.sortition_chamber.seats
    return [
        {
            "tick": e["tick"],
            "seated": len(e["payload"]["seated"]),
            "vacated": len(e["payload"]["vacated"]),
            "pool_relaxed": bool(e["payload"]["pool_relaxed"]),
            "undersized": len(e["payload"]["seated"]) < seats,
        }
        for e in rotations
    ]


def _render(trace: list[dict], config: PolityConfig) -> str:
    lines = [
        "# Sortition chamber calibration — pool exhaustion (§6bis.3, v6b Lot 2)",
        "",
        f"Shipped defaults: `population_size={config.run.population_size}`, "
        f"`seats={config.sortition_chamber.seats}`, `term_years={config.sortition_chamber.term_years}` "
        f"=> rotation every {config.sortition_chamber.term_years * config.run.ticks_per_year} ticks, "
        f"over {config.run.total_ticks} total ticks.",
        "",
        "| tick | seated | vacated | pool_relaxed | undersized |",
        "|---|---|---|---|---|",
    ]
    for row in trace:
        lines.append(
            f"| {row['tick']} | {row['seated']} | {row['vacated']} | "
            f"{row['pool_relaxed']} | {row['undersized']} |"
        )
    first_relaxed = next((row["tick"] for row in trace if row["pool_relaxed"]), None)
    first_undersized = next((row["tick"] for row in trace if row["undersized"]), None)
    last_undersized = next((row["tick"] for row in reversed(trace) if row["undersized"]), None)
    post_relaxation_min_seated = min(
        (row["seated"] for row in trace if row["tick"] > (last_undersized or -1)), default=None
    )
    lines += [
        "",
        f"First relaxed draw: tick {first_relaxed}. "
        f"First undersized draw: tick {first_undersized}. "
        f"Last undersized draw: tick {last_undersized}. "
        f"Minimum chamber size after the last undersized draw: {post_relaxation_min_seated} "
        f"(of {config.sortition_chamber.seats} seats).",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/sortition_calibration_runs"))
    parser.add_argument("--results", type=Path, default=Path("scripts/sortition_calibration_results.md"))
    args = parser.parse_args()

    config = _sortition_config(args.output_dir)
    trace = run_sortition_trace(args.output_dir)
    report = _render(trace, config)
    print(report)
    args.results.write_text(report, encoding="utf-8")
    print(f"(full report written to {args.results})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
