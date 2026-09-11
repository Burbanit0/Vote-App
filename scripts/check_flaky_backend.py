#!/usr/bin/env python3
"""check_flaky_backend.py — fail if any backend test's outcome differs across
independent runs.

The e2e suite already has this discipline (voter-app/scripts/check-flaky.mjs,
via Playwright's built-in retry+flaky reporting). The backend had nothing
equivalent (Lot 5, PLAN_SOLIDITE_TECHNIQUE.md — "Chasse au flake nocturne").

Runs the backend suite N times (default 3), each a genuinely independent
pytest-randomly ordering (a fresh process, fresh random seed — not an
in-process retry of just the failures, which wouldn't catch order-dependent
coupling the way a full re-collection does), and diffs each test's outcome
across all N JUnit XML reports. A test that passes in one run and fails in
another is flaky by definition, regardless of which run "looked" green.

Runs with xdist (-n auto), same as the normal suite, to keep a nightly pass
at minutes rather than tens of minutes (measured directly: ~80s/run
parallel vs. ~1000s/run sequential for the same ~2000 tests). Trade-off
worth naming: a coupling that only manifests when two tests share the same
WORKER PROCESS can, with xdist's own scheduling, end up in different
workers on every run and therefore fail (or pass) consistently instead of
varying run-to-run -- this script won't flag that as flaky, but a
consistent failure is already caught by the normal test suite on every PR,
so it doesn't stay silently hidden either way.

Usage:
    python scripts/check_flaky_backend.py [--runs N] [--path TEST_PATH]

Exits 1 and names every unstable test if any is found; exits 0 (printing the
seeds used, for reproducibility) otherwise.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "fast_api_voter"


def _run_once(run_index: int, test_path: str, xml_path: Path) -> tuple[dict[str, str], int | None]:
    """Run the suite once; return {testcase_id: outcome} and the seed pytest-randomly used."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            test_path,
            # -o addopts= drops pyproject.toml's coverage gate (irrelevant here,
            # and --cov-fail-under would abort a run early) but ALSO its
            # --ignore of the slow Schemathesis contract-fuzzing file and its
            # `-n auto` xdist parallelization -- both restored explicitly
            # below, or 3 runs of the full suite take ~3x as long as they
            # need to (each ~1000s sequential-with-Schemathesis instead of
            # ~80s parallel-without-it, measured directly before fixing this).
            "-o",
            "addopts=",
            "--ignore=api/tests/test_schema_contract.py",
            "-n",
            "auto",
            f"--junit-xml={xml_path}",
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    # -q (quiet) suppresses pytest-randomly's seed banner; default verbosity
    # prints it, so this deliberately doesn't pass -q.
    seed_match = re.search(r"Using --randomly-seed=(\d+)", proc.stdout + proc.stderr)
    seed = int(seed_match.group(1)) if seed_match else None

    tree = ET.parse(xml_path)
    outcomes: dict[str, str] = {}
    for testcase in tree.getroot().iter("testcase"):
        test_id = f"{testcase.get('classname')}::{testcase.get('name')}"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            outcomes[test_id] = "failed"
        elif testcase.find("skipped") is not None:
            outcomes[test_id] = "skipped"
        else:
            outcomes[test_id] = "passed"

    summary_lines = [
        line for line in proc.stdout.splitlines() if re.search(r"\d+ (passed|failed|error)", line)
    ]
    summary = summary_lines[-1].strip() if summary_lines else "(no summary line found)"
    print(f"  run {run_index}: seed={seed} -> {summary}")
    return outcomes, seed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Number of independent runs (default: 3)")
    parser.add_argument(
        "--path",
        default="api/tests",
        help="Test path relative to fast_api_voter/ (default: api/tests, excludes the slow "
        "Schemathesis file via pyproject's own --ignore since addopts= only strips OTHER flags)",
    )
    args = parser.parse_args()

    print(f"Running the backend suite {args.runs} times, comparing outcomes across runs...")
    all_outcomes: list[dict[str, str]] = []
    seeds: list[int | None] = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, args.runs + 1):
            xml_path = Path(tmp) / f"run-{i}.xml"
            outcomes, seed = _run_once(i, args.path, xml_path)
            all_outcomes.append(outcomes)
            seeds.append(seed)

    all_test_ids = set()
    for outcomes in all_outcomes:
        all_test_ids.update(outcomes.keys())

    flaky = []
    for test_id in sorted(all_test_ids):
        results = [outcomes.get(test_id, "MISSING") for outcomes in all_outcomes]
        if len(set(results)) > 1:
            flaky.append((test_id, results))

    if not flaky:
        print(f"\n✅ No flaky test across {args.runs} independent runs (seeds: {seeds}).")
        print("Every test had the same outcome regardless of execution order.")
        return 0

    print(f"\n🔴 {len(flaky)} flaky test(s) — outcome depends on execution order (seeds: {seeds}):\n")
    for test_id, results in flaky:
        print(f"   • {test_id}  ({' -> '.join(results)})")
    print(
        "\n   A test whose outcome depends on run order shares mutable state with\n"
        "   another test (module-level state, a shared fixture, an external\n"
        "   resource) — fix the coupling, don't just rerun until it's green.\n"
        f"   Reproduce with: PYTHONHASHSEED=0 pytest --randomly-seed=<seed above> {args.path}\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
