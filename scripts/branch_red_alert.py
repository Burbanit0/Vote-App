#!/usr/bin/env python3
"""Keep one open issue listing what is red on polity, the working branch.

polity once stayed red for three days with nobody noticing: a red push run
on a branch notifies no one but its pusher, and a scheduled deep test (fuzz,
mutation, DAST, flaky hunt) notifies no one at all. branch-red-alert.yml runs
this whenever a watched workflow completes.

Each run rebuilds the whole list from the latest relevant run of every
watched workflow, rather than applying the one event that triggered it, so a
run GitHub drops from the concurrency queue loses nothing:

  - a workflow whose latest run failed gets one line in the open `polity-red`
    issue (the issue is opened if there is none);
  - a workflow whose latest run passed has no line, and the issue is closed
    once no line is left;
  - cancelled and skipped runs are passed over (they say nothing about the code).

"Relevant" means a push or a manual dispatch on polity, and for the deep tests
also their scheduled runs: those fire from develop's copy of the workflow but
check out polity.

Usage (from the workflow; GH_TOKEN and GITHUB_REPOSITORY in the environment):
  python3 scripts/branch_red_alert.py
  python3 scripts/branch_red_alert.py --dry-run   # print the body, change nothing
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

BRANCH = "polity"
LABEL = "polity-red"
TITLE = "polity is red"
# Workflow file → whether its scheduled runs test polity (the deep tests).
WATCHED = {
    "backend-ci-cd-pipeline.yml": False,
    "frontend-ci-cd-pipeline.yml": False,
    "e2e.yml": False,
    "openapi-contract.yml": False,
    "audit.yml": False,  # its scheduled run checks out develop for most jobs
    "mutation-testing.yml": True,
    "schemathesis.yml": True,
    "atheris-fuzzing.yml": True,
    "flaky-check-backend.yml": True,
    "dast.yml": True,
    "workflow-lint.yml": False,
    "zizmor-online.yml": True,  # weekly, audits polity
}
RED = {"failure", "timed_out", "startup_failure"}
NO_VERDICT = {"cancelled", "skipped", "neutral", "stale", "action_required", None}
HEADER = (
    "Workflows whose latest run on `polity` failed. This list is rebuilt after every"
    " watched run: a line goes away when its workflow passes again, and the issue"
    " closes when none is left (`.github/workflows/branch-red-alert.yml`).\n"
)


def relevant(run: dict, deep: bool) -> bool:
    if run.get("event") in ("push", "workflow_dispatch"):
        return run.get("head_branch") == BRANCH
    return deep and run.get("event") == "schedule"


def latest_verdict(runs: list[dict], deep: bool) -> dict | None:
    """The newest relevant run that passed or failed (runs come newest first)."""
    for run in runs:
        if relevant(run, deep) and run.get("conclusion") not in NO_VERDICT:
            return run
    return None


def line(run: dict) -> str:
    when = "scheduled run" if run.get("event") == "schedule" else f"`{run.get('head_sha', '')[:7]}`"
    return f"- [ ] **{run.get('name')}**: {run.get('conclusion')} on {when}, [run]({run.get('html_url')})"


def render(red_runs: list[dict]) -> str:
    return HEADER + "\n" + "".join(line(r) + "\n" for r in sorted(red_runs, key=lambda r: r.get("name", "")))


def gh(*args: str, data: dict | None = None) -> str:
    res = subprocess.run(["gh", "api", *args] + (["--input", "-"] if data is not None else []),
                         input=json.dumps(data) if data is not None else None,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def fetch_runs(repo: str, wf: str, deep: bool) -> list[dict]:
    """The workflow's completed runs that can speak for polity, newest first.

    Filtered server-side: on a busy workflow, PR and develop runs would push
    polity's latest run out of an unfiltered page. Scheduled runs report
    develop as their branch, so the deep tests' are fetched on their own.
    """
    base = f"repos/{repo}/actions/workflows/{wf}/runs?status=completed&per_page=30"
    runs = json.loads(gh(f"{base}&branch={BRANCH}")).get("workflow_runs", [])
    if deep:
        runs += json.loads(gh(f"{base}&event=schedule")).get("workflow_runs", [])
    return sorted(runs, key=lambda r: r.get("created_at", ""), reverse=True)


def collect(repo: str) -> list[dict]:
    red = []
    for wf, deep in WATCHED.items():
        run = latest_verdict(fetch_runs(repo, wf, deep), deep)
        if run and run.get("conclusion") in RED:
            red.append(run)
    return red


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    repo = os.environ["GITHUB_REPOSITORY"]

    red = collect(repo)
    body = render(red)
    if args.dry_run:
        print(body)
        return 0
    found = json.loads(gh(f"repos/{repo}/issues?labels={LABEL}&state=open&per_page=1"))
    issue = found[0] if found else None
    if issue is None:
        if not red:
            print(f"{BRANCH} is green; no {LABEL} issue open")
            return 0
        created = json.loads(gh(f"repos/{repo}/issues", data={"title": TITLE, "body": body, "labels": [LABEL]}))
        print(f"opened {created['html_url']}")
        return 0
    if not red:
        gh("-X", "PATCH", f"repos/{repo}/issues/{issue['number']}",
           data={"body": body, "state": "closed", "state_reason": "completed"})
        print(f"{BRANCH} is green again: closed {issue['html_url']}")
    elif issue.get("body") != body:
        gh("-X", "PATCH", f"repos/{repo}/issues/{issue['number']}", data={"body": body})
        print(f"updated {issue['html_url']}")
    else:
        print(f"unchanged {issue['html_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
