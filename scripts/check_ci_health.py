#!/usr/bin/env python3
"""check_ci_health.py — catch a non-required CI workflow rotting silently.

Origin: mutmut crashed on every run for 17 days (2026-08-29 -> 2026-09-13)
before this script existed. Nobody noticed, because `mutation-testing.yml`
is deliberately not a required check (it never runs on `pull_request`, and a
required check on a workflow that never triggers on a PR blocks that PR
forever -- see scripts/setup-branch-protection.sh's own comment). The same
session also found `develop`'s branch protection had silently drifted from
what scripts/setup-branch-protection.sh documents. Both are the same
disease: state that only a human remembering to look would catch.

This script has two modes that only trust each other, never a human's
memory:

  --update   Queries the real GitHub Actions run history for each watched
             workflow (never-PR-gated: mutation-testing.yml,
             schemathesis.yml, atheris-fuzzing.yml, flaky-check-backend.yml,
             dast.yml, scorecard.yml) plus develop's live branch-protection
             settings, and writes a snapshot to .github/ci-health.json.
             Run on a schedule (see ci-health.yml), never on a PR -- it's
             the thing being watched, not the watcher.

  --verify   Reads that snapshot (not live GitHub state -- cheap, no API
             calls, safe to run on every PR) and fails if:
               (a) the snapshot itself is stale (the scheduled --update
                   run has gone quiet -- the watcher dying is exactly the
                   failure mode this exists to catch, so its own silence
                   must be loud), or
               (b) any watched workflow is unhealthy/inert/never-run, or
               (c) develop's branch protection has drifted from the setup
                   script,
             unless a live, unexpired entry in .github/ci-health-snoozes.json
             covers it.

Per-workflow expected cadence is derived from each workflow file's own
`schedule: cron` line, not hand-copied here -- a single day-of-week field
(not `*`) means weekly, otherwise daily. One source of truth, same
reasoning as .mergify.yml's comment on not duplicating branch-protection's
required-contexts list.

Usage:
    python scripts/check_ci_health.py --update
    python scripts/check_ci_health.py --verify
    python scripts/check_ci_health.py --verify --snapshot path/to/fixture.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
SNAPSHOT_PATH = REPO_ROOT / ".github" / "ci-health.json"
SNOOZES_PATH = REPO_ROOT / ".github" / "ci-health-snoozes.json"
SETUP_BRANCH_PROTECTION = REPO_ROOT / "scripts" / "setup-branch-protection.sh"

OWNER_REPO = "Burbanit0/Vote-App"
BRANCH = "develop"

# Deliberate curation, not auto-discovery: these are the workflows that
# never run on pull_request (so a red run gates nobody, and rot is
# invisible by construction) but that this repo's plan explicitly built for
# their own signal (mutation score, contract fuzzing, coverage-guided
# fuzzing, flake hunting, DAST, supply-chain scorecard). Required-check
# workflows (Backend CI, Frontend CI, E2E, ...) self-heal: a human is
# blocked until they're green, so they don't belong on this list.
WATCHED_WORKFLOWS = [
    "mutation-testing.yml",
    "schemathesis.yml",
    "atheris-fuzzing.yml",
    "flaky-check-backend.yml",
    "dast.yml",
    "scorecard.yml",
]

# How many of the most recent *completed, non-cancelled* runs to look at
# when deciding whether a workflow is failing consistently rather than
# flaking once.
CONSECUTIVE_FAILURE_THRESHOLD = 2

# A workflow whose last real run is older than (expected cadence * this
# multiplier) is "inert" -- the exact failure mode of a cron that silently
# stopped firing (confirmed real for mutmut: 215+ commits of nothing).
INERT_MULTIPLIER = 1.5

# The scheduled --update run's own heartbeat. Independent of any single
# watched workflow's cadence -- this is "is the watcher itself alive",
# checked against how often ci-health.yml's own audit job is scheduled to
# run (daily). 1.5x gives one missed day of slack before blocking PRs.
AUDIT_EXPECTED_HOURS = 24
AUDIT_STALE_HOURS = AUDIT_EXPECTED_HOURS * INERT_MULTIPLIER


def _run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def derive_expected_hours(workflow_file: str) -> int:
    """Weekly (a specific day-of-week in the cron) -> 168h; anything else
    with a schedule (daily, `*` day-of-week) -> 24h. Falls back to 24h if
    no schedule is found at all (conservative: flags sooner, not later)."""
    text = (WORKFLOWS_DIR / workflow_file).read_text(encoding="utf-8")
    match = re.search(r"cron:\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        return AUDIT_EXPECTED_HOURS
    fields = match.group(1).split()
    if len(fields) != 5:
        return AUDIT_EXPECTED_HOURS
    day_of_week = fields[4]
    return 24 if day_of_week == "*" else 24 * 7


def workflow_display_name(workflow_file: str) -> str:
    text = (WORKFLOWS_DIR / workflow_file).read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else workflow_file


def query_workflow_health(workflow_file: str) -> dict[str, Any]:
    expected_hours = derive_expected_hours(workflow_file)
    runs = _run_gh_json(
        [
            "run",
            "list",
            f"--workflow={workflow_file}",
            f"--branch={BRANCH}",
            "--limit=8",
            "--json=databaseId,status,conclusion,createdAt,event",
        ]
    )
    display_name = workflow_display_name(workflow_file)

    if not runs:
        return {
            "display_name": display_name,
            "expected_cadence_hours": expected_hours,
            "last_run_at": None,
            "recent_conclusions": [],
            "consecutive_failures": 0,
            "status": "never_run",
            "detail": "no run found on this branch, ever",
        }

    last_run_at = _parse_iso(max(r["createdAt"] for r in runs))
    age_hours = (_now() - last_run_at).total_seconds() / 3600

    completed = [r for r in runs if r["status"] == "completed" and r["conclusion"] != "cancelled"]
    completed.sort(key=lambda r: r["createdAt"], reverse=True)
    recent_conclusions = [r["conclusion"] for r in completed[:5]]

    consecutive_failures = 0
    for conclusion in recent_conclusions:
        if conclusion == "failure":
            consecutive_failures += 1
        else:
            break

    if age_hours > expected_hours * INERT_MULTIPLIER:
        status = "inert"
        detail = f"last run {age_hours:.0f}h ago, expected every ~{expected_hours}h"
    elif consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
        status = "unhealthy"
        detail = f"last {consecutive_failures} completed runs all failed"
    else:
        status = "healthy"
        detail = "ok"

    return {
        "display_name": display_name,
        "expected_cadence_hours": expected_hours,
        "last_run_at": last_run_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recent_conclusions": recent_conclusions,
        "consecutive_failures": consecutive_failures,
        "status": status,
        "detail": detail,
    }


def parse_setup_script_expectations() -> tuple[list[str], bool]:
    """Extract develop's expected required-contexts list and strict flag
    from setup-branch-protection.sh -- the authoritative source, not a
    second hand-copied list that could itself drift (same reasoning as
    .mergify.yml's comment on branch-protection duplication)."""
    text = SETUP_BRANCH_PROTECTION.read_text(encoding="utf-8")

    contexts_match = re.search(r"REQUIRED_CONTEXTS='(\[.*?\])'", text, re.DOTALL)
    required_contexts = json.loads(contexts_match.group(1)) if contexts_match else []

    develop_fn_match = re.search(
        r"protect_develop\(\)\s*\{(.*?)\n\}", text, re.DOTALL
    )
    develop_fn_body = develop_fn_match.group(1) if develop_fn_match else ""
    # The JSON is embedded in a bash double-quoted string, so its own quotes
    # are backslash-escaped in the raw file text (\"strict\": true) -- match
    # loosely rather than requiring literal unescaped quotes.
    expected_strict = bool(re.search(r'\\?"strict\\?"\s*:\s*true', develop_fn_body))

    return required_contexts, expected_strict


def check_branch_protection_drift() -> dict[str, Any]:
    expected_contexts, expected_strict = parse_setup_script_expectations()
    try:
        live = _run_gh_json(
            ["api", f"repos/{OWNER_REPO}/branches/{BRANCH}/protection"]
        )
    except subprocess.CalledProcessError as exc:
        return {
            "status": "unhealthy",
            "detail": f"could not read live branch protection: {exc.stderr.strip()}",
        }

    live_strict = bool(live.get("required_status_checks", {}).get("strict", False))
    live_contexts = sorted(
        c["context"] for c in live.get("required_status_checks", {}).get("checks", [])
    )
    expected_sorted = sorted(expected_contexts)

    problems = []
    if live_strict != expected_strict:
        problems.append(
            f"strict is {live_strict} live, {expected_strict} in setup-branch-protection.sh"
        )
    missing = set(expected_sorted) - set(live_contexts)
    extra = set(live_contexts) - set(expected_sorted)
    if missing:
        problems.append(f"missing live required contexts: {sorted(missing)}")
    if extra:
        problems.append(f"unexpected live required contexts: {sorted(extra)}")

    if problems:
        return {"status": "drifted", "detail": "; ".join(problems)}
    return {"status": "healthy", "detail": "matches setup-branch-protection.sh"}


def cmd_update(_: argparse.Namespace) -> int:
    workflows = {wf: query_workflow_health(wf) for wf in WATCHED_WORKFLOWS}
    branch_protection = check_branch_protection_drift()

    snapshot = {
        "generated_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflows": workflows,
        "branch_protection": branch_protection,
    }
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    unhealthy = [
        f"{wf} ({info['status']}: {info['detail']})"
        for wf, info in workflows.items()
        if info["status"] != "healthy"
    ]
    if branch_protection["status"] != "healthy":
        unhealthy.append(f"branch-protection ({branch_protection['detail']})")

    print(f"Wrote {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
    if unhealthy:
        print("Unhealthy:")
        for line in unhealthy:
            print(f"  - {line}")
    else:
        print("All watched workflows and branch protection: healthy.")
    return 0


def _load_snoozes(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _is_snoozed(key: str, snoozes: dict[str, dict[str, str]]) -> tuple[bool, str]:
    entry = snoozes.get(key)
    if not entry:
        return False, ""
    until = datetime.strptime(entry["until"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if _now() < until + timedelta(days=1):
        return True, f"snoozed until {entry['until']} ({entry.get('reason', 'no reason given')})"
    return False, f"snooze for this expired on {entry['until']} -- no longer honored"


def cmd_verify(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot) if args.snapshot else SNAPSHOT_PATH
    if not snapshot_path.exists():
        print(f"🔴 No snapshot at {snapshot_path} -- has ci-health.yml's audit job ever run?")
        return 1

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snoozes_path = Path(args.snoozes) if args.snoozes else SNOOZES_PATH
    snoozes = _load_snoozes(snoozes_path)
    problems: list[str] = []
    notes: list[str] = []

    generated_at = _parse_iso(snapshot["generated_at"])
    age_hours = (_now() - generated_at).total_seconds() / 3600
    if age_hours > AUDIT_STALE_HOURS:
        problems.append(
            f"the ci-health snapshot itself is {age_hours:.0f}h old (expected every "
            f"~{AUDIT_EXPECTED_HOURS}h) -- the watchdog's scheduled audit has gone "
            "quiet, which is exactly the failure mode it exists to catch"
        )

    for wf, info in snapshot.get("workflows", {}).items():
        if info["status"] == "healthy":
            continue
        snoozed, why = _is_snoozed(wf, snoozes)
        line = f"{info.get('display_name', wf)} ({wf}): {info['status']} -- {info['detail']}"
        if snoozed:
            notes.append(f"{line} [{why}]")
        else:
            problems.append(f"{line}{f' [{why}]' if why else ''}")

    bp = snapshot.get("branch_protection", {})
    if bp.get("status") != "healthy":
        snoozed, why = _is_snoozed("branch-protection", snoozes)
        line = f"branch protection on {BRANCH}: {bp.get('status')} -- {bp.get('detail')}"
        if snoozed:
            notes.append(f"{line} [{why}]")
        else:
            problems.append(f"{line}{f' [{why}]' if why else ''}")

    print(f"ci-health snapshot generated_at={snapshot['generated_at']} ({age_hours:.1f}h ago)")
    for note in notes:
        print(f"🟡 {note}")

    if problems:
        print("🔴 CI health check failed:")
        for problem in problems:
            print(f"  - {problem}")
        print()
        print(
            "If this is real: fix it, or if a fix genuinely needs time, add a dated "
            "entry to .github/ci-health-snoozes.json with a reason and an `until` "
            "date -- never an open-ended one."
        )
        return 1

    print("✅ CI health: all watched workflows and branch protection are healthy (or validly snoozed).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--update", action="store_true", help="query live GitHub state, write the snapshot")
    mode.add_argument("--verify", action="store_true", help="read the snapshot, exit non-zero if unhealthy/stale")
    parser.add_argument("--snapshot", help="path to a snapshot file to verify instead of the real one (testing)")
    parser.add_argument("--snoozes", help="path to a snoozes file to use instead of the real one (testing)")
    args = parser.parse_args()

    if args.update:
        return cmd_update(args)
    return cmd_verify(args)


if __name__ == "__main__":
    sys.exit(main())
