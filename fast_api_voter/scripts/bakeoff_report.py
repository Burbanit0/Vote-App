"""Score every bake-off session in a directory (S2.2): scorecard.json and scorecard.md.

Usage (from fast_api_voter/):
    python scripts/bakeoff_report.py scripts/bakeoff_runs --control qwen3-8b-awq

The control model is the one every other is tested against (S2.4: Qwen3-8B-AWQ in every
session), and the one S2.2's acceptance checks are read on.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_bank import read_bank  # noqa: E402
from api.domain.polity.bakeoff_report import render_markdown  # noqa: E402
from api.domain.polity.bakeoff_scorecard import discover_sessions, scorecard  # noqa: E402
from bakeoff_cases import DEFAULT_BANK  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", type=Path, help="the directory holding one sub-directory per session")
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--control", default=None, help="the control session's label (default: the first by name)")
    args = parser.parse_args(argv)

    sessions = discover_sessions(args.runs)
    if not sessions:
        print(f"no sessions under {args.runs}")
        return 1
    card = scorecard(read_bank(args.bank), sessions, control=args.control)
    (args.runs / "scorecard.json").write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.runs / "scorecard.md").write_text(render_markdown(card), encoding="utf-8")
    print(f"{len(sessions)} session(s) scored: {args.runs / 'scorecard.md'}")
    for check in card["acceptance"]:
        print(f"  {check['check']}: expected {check['expected']}, observed {json.dumps(check['observed'])} -> {check['passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
