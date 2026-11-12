#!/usr/bin/env python3
"""Collect CI run history for the dashboard (ci-dashboard.yml).

Appends every completed workflow run to a JSON-lines history (one record per
run attempt, so a re-run is its own row), and for each failed run reads the
failed job's log tail once, picks the error lines and sorts the failure into a
category:

  code         a real failure: an assertion, a type or lint error, a build error
  test-flaky   failed, then passed on a re-run of the same commit
  advisory     a dependency advisory (npm audit, pip-audit, trivy, dependency review)
  infra        the runner, the network or a service, not the code
  timeout      a job or step cancelled for running too long
  unknown      the log could not be read (expired or unreachable)

Then writes summary.json for the page: each branch's tip, a workflow x day
grid, failure groups, speed and the quality baselines.

stdlib only; talks to GitHub through `gh api` (GH_TOKEN in the environment).

Usage:
  python3 scripts/ci_dashboard/collect.py --data DIR [--days 30] [--repo OWNER/REPO]
DIR holds runs.jsonl (read, then appended) and receives summary.json.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRANCHES = ("polity", "develop", "main")
BASELINES = {
    "mutation": ".github/mutation-baseline.json",
    "quality": ".github/quality-baseline.json",
    "ci_health": ".github/ci-health.json",
}
MAX_LOG_FETCHES = 40  # per collection: failures are rare, this bounds a backlog
ERROR_LINES = 6

# First match wins; ordered from most to least specific.
CATEGORIES: list[tuple[str, re.Pattern[str]]] = [
    ("timeout", re.compile(r"exceeded the maximum execution time|has timed out|timeout-minutes|"
                           r"The operation was canceled", re.IGNORECASE)),
    ("infra", re.compile(r"runner (has received a shutdown|lost communication)|"
                         r"No space left on device|ECONNRESET|ETIMEDOUT|503 Service Unavailable|"
                         r"rate limit exceeded|Could not resolve host|Connection reset by peer|"
                         r"failed to (download|fetch) action", re.IGNORECASE)),
    ("advisory", re.compile(r"npm audit|audit:gate|GHSA-[0-9a-z]{4}-|pip-audit|"
                            r"vulnerabilit(y|ies) found|Dependency review detected|CVE-\d{4}-", re.IGNORECASE)),
]
ERROR_RE = re.compile(
    r"##\[error\]|(^|\s)(FAILED|ERROR|Error:|error:|AssertionError|Traceback|✗|×|::error::|"
    r"error TS\d+|E\s{3}|FAIL\s|npm (ERR!|error)|Process completed with exit code [1-9])")
GENERIC = re.compile(r"Process completed with exit code")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s?")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
NOISE = re.compile(r"[0-9a-f]{7,40}|\d+(\.\d+)?(ms|s)?|/tmp/\S+|line \d+")


def gh_json(path: str) -> Any:
    res = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"gh api {path}: {res.stderr.strip()}")
    return json.loads(res.stdout)


def gh_text(path: str) -> tuple[str, str]:
    """(body, error): a job log is not JSON and may not be valid UTF-8, and it is
    full of colour codes, which gh refuses to output unless told to."""
    res = subprocess.run(["gh", "api", "--allow-escape-sequences", path], capture_output=True, check=False)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace").strip().splitlines()
        return "", (err[-1] if err else f"gh exited {res.returncode}")[:300]
    return res.stdout.decode("utf-8", "replace"), ""


def iso(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


# ── Runs ───────────────────────────────────────────────────────────────────

def record(run: dict) -> dict:
    started, ended = iso(run.get("run_started_at")), iso(run.get("updated_at"))
    created = iso(run.get("created_at"))
    return {
        "id": run["id"],
        "attempt": run.get("run_attempt", 1),
        "workflow": run.get("name"),
        "path": (run.get("path") or "").split("@")[0],
        "branch": run.get("head_branch"),
        "event": run.get("event"),
        "sha": run.get("head_sha"),
        "pr": [p.get("number") for p in run.get("pull_requests") or []],
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "duration_s": int((ended - started).total_seconds()) if started and ended else None,
        # A re-run restarts run_started_at but keeps created_at: only the first
        # attempt's gap is time spent queued.
        "queue_s": (int((started - created).total_seconds())
                    if started and created and run.get("run_attempt", 1) == 1 else None),
        "url": run.get("html_url"),
    }


def own_superseded(run: dict) -> bool:
    """A dashboard run cancelled by its own concurrency group: every CI completion
    starts one, so a burst leaves dozens of these. They say nothing about CI; the
    dashboard's own successes and failures are kept."""
    path = (run.get("path") or "").split("@")[0]
    return path.endswith("/ci-dashboard.yml") and run.get("conclusion") == "cancelled"


def fetch_runs(repo: str, since: datetime, now: datetime) -> list[dict]:
    """Completed runs created since `since`, one day per query: a filtered
    listing stops at 1000 results, so a busy window queried at once loses runs."""
    out: list[dict] = []
    day = since.date()
    while day <= now.date():
        page = 1
        while True:
            data = gh_json(f"repos/{repo}/actions/runs?status=completed&per_page=100&page={page}"
                           f"&created={day.isoformat()}")
            runs = data.get("workflow_runs", [])
            # "dynamic" runs are GitHub's own (Dependabot graph updates, Pages
            # builds), each instance under its own name: not this repo's CI.
            out += [record(r) for r in runs if r.get("event") != "dynamic" and not own_superseded(r)]
            if len(runs) < 100:
                break
            page += 1
        day += timedelta(days=1)
    return out


def earlier_attempts(repo: str, fresh: list[dict], seen: set) -> list[dict]:
    """The listing only returns a run's latest attempt: a failure re-run before
    the next collection would never be recorded (nor counted as flaky)."""
    out = []
    for r in fresh:
        for n in range(1, r["attempt"]):
            if (r["id"], n) in seen:
                continue
            try:
                out.append(record(gh_json(f"repos/{repo}/actions/runs/{r['id']}/attempts/{n}")))
            except RuntimeError as exc:
                print(f"collect: {exc}", file=sys.stderr)
    return out


# ── Failures ───────────────────────────────────────────────────────────────

def error_lines(log: str) -> list[str]:
    lines = [TIMESTAMP.sub("", ANSI.sub("", ln)).rstrip() for ln in log.splitlines()]
    hits = [ln for ln in lines if ERROR_RE.search(ln) and "##[group]" not in ln]
    if hits and all(GENERIC.search(h) for h in hits):
        # Only the runner's closing exit-code line matched: keep what the failing
        # command printed just before it, which is where the cause is.
        end = next(i for i, ln in enumerate(lines) if GENERIC.search(ln))
        context = [ln for ln in lines[:end] if ln.strip() and not ln.startswith(("##[", "[command]"))]
        return (context[-(ERROR_LINES - 1):] + [lines[end]])
    if len(hits) > ERROR_LINES:
        # Head and tail: the cause is usually stated first (npm's ERESOLVE, the
        # first FAILED test), the tally last.
        half = ERROR_LINES // 2
        hits = hits[:half] + hits[-half:]
    return (hits or [ln for ln in lines if ln.strip()])[-ERROR_LINES:]


def categorize(lines: list[str]) -> str:
    text = "\n".join(lines)
    for name, pattern in CATEGORIES:
        if pattern.search(text):
            return name
    return "code"


TALLY = re.compile(r"fixable with the `--fix` option|^Found \d+ errors?|problems? \(\d+ errors?|"
                   r"For a full report see|A complete log of this run|/\.npm/_logs/")


def informative(line: str) -> bool:
    """Enough words to name a cause once the runner's markers are dropped."""
    words = re.sub(r"##\[error\]|::error::|npm (ERR!|error)|[^A-Za-z]+", " ", line).split()
    return len("".join(words)) >= 12 and not TALLY.search(line) and not GENERIC.search(line)


def signature(category: str, lines: list[str]) -> str:
    """A stable key for grouping the same failure across runs."""
    # The runner's closing "Process completed with exit code N" says nothing about
    # the cause and would lump every failure together: prefer the line before it.
    hits = [ln for ln in lines if ERROR_RE.search(ln)]
    specific = [ln for ln in hits if not GENERIC.search(ln)]
    context = [ln for ln in lines if not GENERIC.search(ln)]
    # A bare "npm error", a "-----" rule or a linter's "N fixable" tally names
    # nothing: prefer a line that says what went wrong.
    telling = [ln for ln in specific + context[::-1] if informative(ln)]
    first = (telling or specific or context[-1:] or hits or [""])[0]
    return f"{category}: {NOISE.sub('#', first).strip()[:140]}"


def failure_detail(repo: str, run: dict) -> dict:
    jobs = gh_json(f"repos/{repo}/actions/runs/{run['id']}/attempts/{run['attempt']}/jobs").get("jobs", [])
    failed = [j for j in jobs if j.get("conclusion") in ("failure", "timed_out")]
    if not failed:
        return {"category": "infra", "job": None, "step": None, "lines": [], "signature": "infra: no failed job"}
    job = failed[0]
    step = next((s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"), None)
    log, error = gh_text(f"repos/{repo}/actions/jobs/{job['id']}/logs")
    if not log.strip():  # expired (90 days) or unreachable: say why, group by where it failed
        print(f"collect: log of job {job['id']} unavailable: {error or 'empty'}", file=sys.stderr)
        return {"category": "unknown", "job": job.get("name"), "step": step, "lines": [],
                "log_error": error or "empty log",
                "signature": f"unknown: {job.get('name')} / {step or '?'} (log unavailable)"}
    lines = error_lines(log[-200_000:])
    category = "timeout" if job.get("conclusion") == "timed_out" else categorize(lines)
    return {"category": category, "job": job.get("name"), "step": step,
            "lines": lines, "signature": signature(category, lines)}


LOG_RETRIES = 3
LOG_MAX_AGE = timedelta(days=85)  # GitHub keeps job logs 90 days


def needs_log(r: dict, now: datetime) -> bool:
    """Unread, or unreadable or reduced to the runner's bare exit line last time
    (a few retries while GitHub still has the log)."""
    f = r.get("failure")
    if f is None:
        return True
    created = iso(r["created_at"])
    vague = f.get("category") == "unknown" or (
        bool(f.get("lines")) and not any(informative(ln) for ln in f["lines"]))
    return (vague and r.get("log_tries", 1) < LOG_RETRIES
            and created is not None and now - created < LOG_MAX_AGE)


def mark_flaky(records: list[dict]) -> None:
    """A failure followed by a success of the same workflow on the same commit."""
    passed = {(r["workflow"], r["sha"]) for r in records if r["conclusion"] == "success"}
    for r in records:
        f = r.get("failure")
        if f and (r["workflow"], r["sha"]) in passed and f["category"] == "code":
            f["category"] = "test-flaky"
            f["signature"] = "test-flaky: " + f["signature"].split(": ", 1)[-1]


# ── History ────────────────────────────────────────────────────────────────

def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def merge(history: list[dict], fresh: list[dict], since: datetime) -> list[dict]:
    """History plus the new attempts, deduplicated, trimmed to the window."""
    by_key = {(r["id"], r["attempt"]): r for r in history}
    for r in fresh:
        by_key.setdefault((r["id"], r["attempt"]), r)
    keep = [r for r in by_key.values()
            if (iso(r["created_at"]) or since) >= since and not own_superseded(r)]
    return sorted(keep, key=lambda r: (r["created_at"], r["id"], r["attempt"]))


# ── Summary ────────────────────────────────────────────────────────────────

def pct(values: list[int], q: float) -> int | None:
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, round(q * (len(values) - 1)))]


def summarize(records: list[dict], baselines: dict, now: datetime) -> dict:
    tips: dict[str, dict] = {}
    for branch in BRANCHES:
        pushes = [r for r in records if r["branch"] == branch and r["event"] in ("push", "workflow_dispatch")]
        if not pushes:
            continue
        sha = max(pushes, key=lambda r: r["created_at"])["sha"]
        # Each workflow's latest completed run: the newest commit's own runs may
        # still be in progress or path-filtered out, so a row can name an older one.
        latest: dict[str, dict] = {}
        for r in pushes:
            latest[r["workflow"]] = r  # records are oldest first
        tips[branch] = {"sha": sha, "workflows": {
            w: {"conclusion": r["conclusion"], "url": r["url"], "sha": r["sha"], "created_at": r["created_at"]}
            for w, r in sorted(latest.items())}}

    grid: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for r in records:
        if r["branch"] in ("polity", "develop") and r["event"] != "pull_request":
            grid[r["workflow"]][r["created_at"][:10]][r["conclusion"]] += 1

    groups: dict[str, dict] = {}
    for r in records:
        f = r.get("failure")
        if not f:
            continue
        g = groups.setdefault(f["signature"], {"signature": f["signature"], "category": f["category"],
                                               "count": 0, "branches": set(), "workflows": set(),
                                               "last_seen": "", "example": None})
        g["count"] += 1
        g["branches"].add(r["branch"])
        g["workflows"].add(r["workflow"])
        if r["created_at"] >= g["last_seen"]:
            g["last_seen"] = r["created_at"]
            g["example"] = {"url": r["url"], "job": f["job"], "step": f["step"], "lines": f["lines"],
                            "pr": r["pr"], "sha": r["sha"]}
    failure_groups = sorted(({**g, "branches": sorted(g["branches"]), "workflows": sorted(g["workflows"])}
                             for g in groups.values()), key=lambda g: (-g["count"], g["signature"]))

    speed = {}
    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["conclusion"] == "success" and r["duration_s"] is not None:
            by_wf[r["workflow"]].append(r)
    for wf, rs in sorted(by_wf.items()):
        durations = [r["duration_s"] for r in rs]
        queues = [r["queue_s"] for r in rs if r["queue_s"] is not None]
        speed[wf] = {"runs": len(rs), "p50_s": pct(durations, 0.5), "p95_s": pct(durations, 0.95),
                     "queue_p50_s": pct(queues, 0.5),
                     "daily_p50_s": {d: statistics.median([r["duration_s"] for r in rs if r["created_at"][:10] == d])
                                     for d in sorted({r["created_at"][:10] for r in rs})}}

    # Each workflow's latest run on the long-lived branches (deep-test staleness).
    latest_runs: dict[str, dict] = {}
    for r in records:
        if r["branch"] in ("polity", "develop") and r["event"] != "pull_request":
            latest_runs[r["workflow"]] = {"branch": r["branch"], "event": r["event"], "conclusion": r["conclusion"],
                                          "created_at": r["created_at"], "url": r["url"]}

    by_category = Counter(r["failure"]["category"] for r in records if r.get("failure"))
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": None,
        "runs": len(records),
        "tips": tips,
        "grid": {wf: {d: dict(c) for d, c in sorted(days.items())} for wf, days in sorted(grid.items())},
        "failures_by_category": dict(by_category),
        "failure_groups": failure_groups[:60],
        "speed": speed,
        "latest_runs": dict(sorted(latest_runs.items())),
        "baselines": baselines,
    }


def read_baselines(root: Path) -> dict:
    out = {}
    for key, rel in BASELINES.items():
        try:
            out[key] = json.loads((root / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[key] = None
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--repo", default="Burbanit0/Vote-App")
    args = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)

    args.data.mkdir(parents=True, exist_ok=True)
    history_path = args.data / "runs.jsonl"
    history = load(history_path)
    seen = {(r["id"], r["attempt"]) for r in history}
    fresh = [r for r in fetch_runs(args.repo, since, now) if (r["id"], r["attempt"]) not in seen]
    fresh += earlier_attempts(args.repo, fresh, seen)

    records = merge(history, fresh, since)
    # Never-read failures first, then retries of unreadable logs, newest first in
    # each; whatever the cap leaves is read next time.
    fetched = 0
    for r in sorted(records, key=lambda r: ("failure" not in r, r["created_at"]), reverse=True):
        if fetched >= MAX_LOG_FETCHES:
            break
        if r["conclusion"] in ("failure", "timed_out") and needs_log(r, now):
            r["log_tries"] = r.get("log_tries", 0) + 1
            try:
                r["failure"] = failure_detail(args.repo, r)
            except RuntimeError as exc:  # one unreadable run never stops the collection
                print(f"collect: {exc}", file=sys.stderr)
                r["failure"] = {"category": "unknown", "job": None, "step": None, "lines": [],
                                "signature": "unknown: run details unavailable"}
            fetched += 1
    # Re-key stored failures from their error lines, so a better signature rule
    # also regroups the history (mark_flaky then re-applies its own prefix).
    for r in records:
        f = r.get("failure")
        if f and f.get("lines") and f["category"] != "test-flaky":
            f["signature"] = signature(f["category"], f["lines"])
    mark_flaky(records)
    history_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    summary = summarize(records, read_baselines(ROOT), now)
    summary["window_days"] = args.days
    (args.data / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    print(f"collect: {len(fresh)} new run attempts, {fetched} failure logs read, {len(records)} in the window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
