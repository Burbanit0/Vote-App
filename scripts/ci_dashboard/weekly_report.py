#!/usr/bin/env python3
"""Write the "CI weekly report" issue body from the dashboard's data.

Reads runs.jsonl and summary.json (scripts/ci_dashboard/collect.py, kept on
the ci-data branch) and prints Markdown for the last 7 days:
failures by category with the trend against the week before, the top failure
groups, failures first seen this week, the slowest workflows, deep tests that
have gone stale, and the committed quality baselines.

Usage: python3 scripts/ci_dashboard/weekly_report.py --data DIR [--dashboard URL]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

STALE_DAYS = 8  # weekly deep tests count as stale past this
WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def scheduled_workflows(directory: Path) -> list[str]:
    """Names of the workflows that run on a schedule: each is expected to show up."""
    names = []
    for f in sorted(directory.glob("*.y*ml")):
        text = f.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE)
        if name and re.search(r"^\s+schedule:", text, re.MULTILINE):
            names.append(name.group(1))
    return names


FAILED = ("failure", "timed_out")


def category(r: dict) -> str:
    """A failure's category; one whose log the collector has not read yet is counted, not hidden."""
    return r["failure"]["category"] if r.get("failure") else "not yet read"


def iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def arrow(now: int, before: int) -> str:
    return "→" if now == before else ("▲" if now > before else "▼")


def dur(s: int | None) -> str:
    if s is None:
        return "–"
    return f"{s}s" if s < 90 else f"{round(s / 60)}m"


def report(records: list[dict], summary: dict, now: datetime, dashboard: str | None,
           scheduled: list[str] | None = None) -> str:
    week, prior = now - timedelta(days=7), now - timedelta(days=14)
    this = [r for r in records if iso(r["created_at"]) >= week]
    last = [r for r in records if prior <= iso(r["created_at"]) < week]
    failed = [r for r in this if r["conclusion"] in FAILED]
    cats_now = Counter(category(r) for r in failed)
    cats_before = Counter(category(r) for r in last if r["conclusion"] in FAILED)

    out = [f"# CI weekly report, week to {now:%Y-%m-%d}", ""]
    if dashboard:
        out += [f"Dashboard: {dashboard}", ""]
    out += [(f"{len(this)} runs, {len(failed)} failed "
             f"({len(last)} runs, {sum(cats_before.values())} failed the week before)."), ""]

    out += ["## Failures by category", "", "| Category | This week | Week before | |", "|---|---:|---:|---|"]
    for cat in sorted(set(cats_now) | set(cats_before), key=lambda c: -cats_now[c]):
        out.append(f"| {cat} | {cats_now[cat]} | {cats_before[cat]} | {arrow(cats_now[cat], cats_before[cat])} |")
    if not (cats_now or cats_before):
        out.append("| none | 0 | 0 | → |")

    groups: dict[str, dict] = {}
    for r in (r for r in failed if r.get("failure")):
        g = groups.setdefault(r["failure"]["signature"], {"count": 0, "url": r["url"], "workflows": set()})
        g["count"] += 1
        g["url"] = r["url"]  # records are oldest first: keep the latest
        g["workflows"].add(r["workflow"])
    seen_before = {r["failure"]["signature"] for r in records if r.get("failure") and iso(r["created_at"]) < week}
    out += ["", "## Top failure groups", ""]
    top = sorted(groups.items(), key=lambda kv: -kv[1]["count"])[:8]
    out += [(f"- **{g['count']}×** `{sig}` ({', '.join(sorted(g['workflows']))}, [latest]({g['url']}))"
             + (" **new**" if sig not in seen_before else "")) for sig, g in top] or ["- none"]

    flaky = sorted(sig for sig in groups if sig.startswith("test-flaky:") and sig not in seen_before)
    out += ["", "## New flaky tests", ""] + ([f"- `{s}`" for s in flaky] or ["- none"])

    out += ["", "## Slowest workflows (median of successful runs, 30 days)", ""]
    speed = sorted(summary.get("speed", {}).items(), key=lambda kv: -(kv[1].get("p50_s") or 0))[:5]
    out += [f"- {wf}: p50 {dur(v.get('p50_s'))}, p95 {dur(v.get('p95_s'))}" for wf, v in speed] or ["- no data"]

    stale = [(wf, r) for wf, r in summary.get("latest_runs", {}).items()
             if now - iso(r["created_at"]) > timedelta(days=STALE_DAYS)]
    out += ["", f"## Not run for over {STALE_DAYS} days", ""]
    window = summary.get("window_days", 30)
    # A scheduled workflow with no run at all in the collected window has stopped
    # for longer than the history reaches: the worst case, so it is listed first.
    missing = sorted(set(scheduled or []) - set(summary.get("latest_runs", {})))
    out += [f"- {wf}: **no run in the last {window} days**" for wf in missing]
    out += [f"- {wf}: last {r['conclusion']} on {r['created_at'][:10]} ([run]({r['url']}))" for wf, r in stale]
    if not (missing or stale):
        out.append("- none")

    base = summary.get("baselines") or {}
    out += ["", "## Quality baselines (committed ratchets)", ""]
    if base.get("mutation"):
        out.append(f"- mutation score: {base['mutation'].get('score')}%")
    for k, v in sorted((base.get("quality") or {}).items()):
        out.append(f"- {k.replace('_', ' ')}: {v}")
    out += ["", "_Rebuilt every Monday by `ci-dashboard.yml`; the issue is edited in place._"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--dashboard")
    args = ap.parse_args(argv)
    records = [json.loads(ln) for ln in (args.data / "runs.jsonl").read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    summary = json.loads((args.data / "summary.json").read_text(encoding="utf-8"))
    sys.stdout.write(report(records, summary, datetime.now(timezone.utc), args.dashboard,
                            scheduled_workflows(WORKFLOWS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
