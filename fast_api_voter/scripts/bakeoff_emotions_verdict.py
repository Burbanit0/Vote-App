"""Read ADR-012's prerequisite from a bake-off session on the emotions bank.

Pre-registered in plan-polity-build-order.md ("ADR-012's prerequisite, pre-registered before its
session"); the reading is api/domain/polity/bakeoff_emotions.py.

Usage (from fast_api_voter/):
    python scripts/bakeoff_emotions_verdict.py scripts/bakeoff_runs/<session>
        # writes scripts/bakeoff_emotions_prerequisite_results.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_bank import read_bank  # noqa: E402
from api.domain.polity.bakeoff_emotions import read_verdict, verdict_markdown  # noqa: E402
from api.domain.polity.bakeoff_scorecard import load_session  # noqa: E402

EMOTIONS_BANK = Path(__file__).resolve().parent / "bakeoff" / "case_bank_emotions.jsonl"
RESULTS = Path(__file__).resolve().parent / "bakeoff_emotions_prerequisite_results.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("session", type=Path)
    parser.add_argument("--bank", type=Path, default=EMOTIONS_BANK)
    args = parser.parse_args(argv)
    session = load_session(args.session)
    verdict = read_verdict(read_bank(args.bank).cases, session.by_case("main"))
    RESULTS.write_text(verdict_markdown(verdict, session.label), encoding="utf-8")
    print(f"{'ACCEPTED' if verdict.accepted else 'NOT ACCEPTED'}: valid {verdict.valid_plain} -> {verdict.valid_felt}, "
          f"correct {verdict.correct_plain} -> {verdict.correct_felt} of {verdict.paired_citizens}; wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
