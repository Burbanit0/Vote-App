"""
fast_api_voter/scripts/llm_test_harness/cli.py

CLI dispatcher for `register` and `report`. There is no `run` subcommand:
every LLM protocol this project has needed so far has had a genuinely
different call shape (chunking, schema, endpoint) -- the harness doesn't
know how to call an LLM and isn't meant to. Running an experiment is a
Python script that loops over trial.record_trial(...), passing its own
run_call; see example_experiment.py and this package's own README for the
worked example.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import registration, report


def _cmd_register(args: argparse.Namespace) -> int:
    experiment = registration.register(
        hypothesis=args.hypothesis,
        decision_criterion=args.decision_criterion,
        planned_n=args.planned_n,
        budget_description=args.budget,
        expected_effect_rate=args.expected_effect_rate,
        confidence=args.confidence,
        decision_threshold_for_sizing=args.decision_threshold_for_sizing,
        threshold=args.threshold,
        comparison=args.comparison,
        metric=args.metric,
    )
    print(f"Registered experiment {experiment.experiment_id}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        text = report.generate_report(args.experiment_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm_harness", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_register = sub.add_parser("register", help="pre-register an experiment before running any trial")
    p_register.add_argument("--hypothesis", required=True)
    p_register.add_argument("--decision-criterion", required=True)
    p_register.add_argument("--planned-n", type=int, required=True)
    p_register.add_argument("--budget", required=True, help="human-readable time/GPU budget")
    p_register.add_argument("--expected-effect-rate", type=float, default=None)
    p_register.add_argument("--confidence", type=float, default=0.95)
    p_register.add_argument("--decision-threshold-for-sizing", type=float, default=None)
    p_register.add_argument("--threshold", type=float, default=None)
    p_register.add_argument("--comparison", choices=["gt", "lt", "ge", "le"], default=None)
    p_register.add_argument("--metric", choices=["failure_rate", "success_rate"], default=None)
    p_register.set_defaults(func=_cmd_register)

    p_report = sub.add_parser("report", help="render a markdown report for a registered experiment")
    p_report.add_argument("experiment_id")
    p_report.add_argument("--out", type=Path, default=None)
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
