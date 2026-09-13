"""Where a polity run's LLM time went: seconds and tokens per decision type, split
into first attempt, retry, rejected, truncation, failed, budget probe and warm-up.
Reads the run's llm_calls.jsonl (S0.5); see api/domain/polity/llm_time_attribution.py
for how calls are categorised.

Usage (from fast_api_voter/):
    python scripts/attribute_llm_time.py scripts/flagship_runs/<run>/run/<run>
    python scripts/attribute_llm_time.py <run_dir> --json
    python scripts/attribute_llm_time.py <run_dir> --by-tick     # S1.1: each tick's wall-clock, inside and outside the model
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, read_calls  # noqa: E402
from api.domain.polity.llm_time_attribution import CATEGORIES, attribute_run, by_tick  # noqa: E402


def _row(label: str, bucket: dict[str, float]) -> str:
    return (
        f"| {label} | {int(bucket['calls'])} | {bucket['seconds']:.1f} | {int(bucket['prompt_tokens'])} "
        f"| {int(bucket['completion_tokens'])} | {int(bucket['reasoning_tokens'])} | {int(bucket['cached_tokens'])} |"
    )


def render(report: dict[str, object], run_dir: Path) -> str:
    lines = [f"# LLM time attribution: {run_dir.name}", ""]
    coverage = report["coverage"]
    lines.append(
        f"{report['calls']} calls; latency sum {report['latency_seconds_sum']:.1f} s; "
        f"covered {report['covered_seconds']:.1f} s of {report['wall_clock_seconds']} s wall-clock"
        + (f" ({100 * float(coverage):.1f}%)" if coverage is not None else "")  # type: ignore[arg-type]
    )
    header = ["", "| category | calls | seconds | prompt tok | completion tok | reasoning tok | cached tok |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    lines += header
    by_category = report["by_category"]
    assert isinstance(by_category, dict)
    lines += [_row(category, by_category[category]) for category in CATEGORIES if by_category[category]["calls"]]
    by_type = report["by_decision_type"]
    assert isinstance(by_type, dict)
    for decision_type, categories in by_type.items():
        lines += ["", f"## {decision_type}", *header[1:]]
        lines += [_row(category, categories[category]) for category in CATEGORIES if category in categories]
    return "\n".join(lines)


def render_by_tick(rows: list[dict[str, object]], run_dir: Path) -> str:
    lines = [f"# LLM time by tick: {run_dir.name}", "",
             "| tick | calls | span s | model s | outside model s | top decision types (s) | categories (s) |",
             "|---:|---:|---:|---:|---:|---|---|"]
    for row in rows:
        types = row["by_decision_type"]
        categories = row["by_category"]
        assert isinstance(types, dict) and isinstance(categories, dict)
        top = ", ".join(f"{name} {seconds:.0f}" for name, seconds in list(types.items())[:3])
        split = ", ".join(f"{name} {seconds:.0f}" for name, seconds in categories.items())
        lines.append(f"| {row['tick']} | {row['calls']} | {row['span_seconds']:.0f} | {row['model_seconds']:.0f} "
                     f"| {row['outside_model_seconds']:.0f} | {top} | {split} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help="the directory holding events.jsonl and llm_calls.jsonl")
    parser.add_argument("--json", action="store_true", help="print the raw report as JSON")
    parser.add_argument("--by-tick", action="store_true", help="each tick's wall-clock, inside and outside the model")
    args = parser.parse_args(argv)
    if not (args.run_dir / "llm_calls.jsonl").exists():
        print(f"no llm_calls.jsonl in {args.run_dir}", file=sys.stderr)
        return 1
    if args.by_tick:
        rows = by_tick(read_calls(args.run_dir / CALL_LOG_FILENAME))
        print(json.dumps(rows, indent=2) if args.json else render_by_tick(rows, args.run_dir))
        return 0
    report = attribute_run(args.run_dir)
    print(json.dumps(report, indent=2) if args.json else render(report, args.run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
