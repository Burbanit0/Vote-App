#!/usr/bin/env python3
"""Turn the open code-scanning alerts on develop into a few tracking issues.

190 open alerts is not 190 issues. Alerts are grouped, and each group gets one
issue whose body is a checklist of its alerts:

  - Trivy (`trivy`, `trivy-image`): one issue per scanned file, so the base-image
    OS packages (`library/votelab`) are one issue and `requirements.lock.txt` another;
  - every other tool (CodeQL, Semgrep...): one issue per rule.

Each run rebuilds every issue from the alerts open right now, so it is
idempotent: an issue is found again by a hidden marker in its body (never by its
title), refreshed when the group changed, and closed once the group has no open
alert left. A group that comes back later reopens its closed issue.

Only alerts on `develop` count (`ref=refs/heads/develop`): that is the branch the
Security tab's default view shows, and the one release syncs land on.

Usage (from the workflow; GH_TOKEN and GITHUB_REPOSITORY in the environment):
  python3 scripts/code_scanning_issues.py
  python3 scripts/code_scanning_issues.py --dry-run   # print the plan, change nothing
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REF = "refs/heads/develop"
LABEL = "code-scanning"
MARKER = "<!-- code-scanning-group: {key} -->"
MARKER_PREFIX = "<!-- code-scanning-group: "
SEVERITY_ORDER = ["critical", "high", "medium", "low", "warning", "note", "error", "none"]
MAX_LINES = 150  # a GitHub issue body holds 65536 characters
TRIVY_CATEGORIES = ("trivy", "trivy-image")


def severity(alert: dict) -> str:
    rule = alert.get("rule") or {}
    return (rule.get("security_severity_level") or rule.get("severity") or "none").lower()


def instance(alert: dict) -> dict:
    return alert.get("most_recent_instance") or {}


def path_of(alert: dict) -> str:
    return (instance(alert).get("location") or {}).get("path") or "unknown"


def group_key(alert: dict) -> str:
    tool = (alert.get("tool") or {}).get("name") or "unknown"
    category = (instance(alert).get("category") or "").removeprefix("/language:") or tool.lower()
    if category in TRIVY_CATEGORIES:
        return f"{category} · {path_of(alert)}"
    return f"{tool} · {(alert.get('rule') or {}).get('id') or 'unknown'}"


def group_alerts(alerts: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for alert in alerts:
        groups.setdefault(group_key(alert), []).append(alert)
    return groups


def sort_alerts(alerts: list[dict]) -> list[dict]:
    rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    return sorted(alerts, key=lambda a: (rank.get(severity(a), len(rank)), a.get("number", 0)))


def title(key: str) -> str:
    return f"Code scanning: {key}"


def alert_line(alert: dict) -> str:
    rule = alert.get("rule") or {}
    desc = (rule.get("description") or rule.get("name") or rule.get("id") or "").strip()
    return f"- [ ] [#{alert['number']}]({alert.get('html_url', '')}) **{severity(alert)}**: {desc}"


def render(key: str, alerts: list[dict]) -> str:
    ordered = sort_alerts(alerts)
    counts: dict[str, int] = {}
    for a in ordered:
        counts[severity(a)] = counts.get(severity(a), 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items(), key=lambda kv: SEVERITY_ORDER.index(kv[0]) if kv[0] in SEVERITY_ORDER else 99))
    lines = [alert_line(a) for a in ordered[:MAX_LINES]]
    if len(ordered) > MAX_LINES:
        lines.append(f"- … and {len(ordered) - MAX_LINES} more, see the Security tab")
    return (
        f"{MARKER.format(key=key)}\n"
        f"Open code-scanning alerts on `develop` for **{key}**: {len(ordered)} ({summary}).\n\n"
        "This list is rebuilt weekly from the Security tab"
        " (`.github/workflows/code-scanning-issues.yml`): an alert disappears from it"
        " when the scanner stops reporting it, and the issue closes when none is left."
        " Do not tick boxes by hand, they are overwritten.\n\n"
        + "\n".join(lines) + "\n"
    )


def marker_of(body: str | None) -> str | None:
    for line in (body or "").splitlines():
        if line.startswith(MARKER_PREFIX) and line.rstrip().endswith("-->"):
            return line[len(MARKER_PREFIX):].rstrip()[: -len("-->")].strip()
    return None


def plan(groups: dict[str, list[dict]], issues: list[dict]) -> list[tuple]:
    """Actions to take: ("create"|"update"|"reopen"|"close", key, issue-or-None, body)."""
    existing = {}
    for issue in issues:
        key = marker_of(issue.get("body"))
        if key is not None and key not in existing:
            existing[key] = issue
    actions: list[tuple] = []
    for key in sorted(groups):
        body = render(key, groups[key])
        issue = existing.get(key)
        if issue is None:
            actions.append(("create", key, None, body))
        elif issue.get("state") == "closed":
            actions.append(("reopen", key, issue, body))
        elif issue.get("body") != body:
            actions.append(("update", key, issue, body))
    for key in sorted(set(existing) - set(groups)):
        if existing[key].get("state") == "open":
            actions.append(("close", key, existing[key], existing[key].get("body") or ""))
    return actions


def gh(*args: str, data: dict | None = None) -> str:
    res = subprocess.run(["gh", "api", *args] + (["--input", "-"] if data is not None else []),
                         input=json.dumps(data) if data is not None else None,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def paged(path: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    sep = "&" if "?" in path else "?"
    while True:
        chunk = json.loads(gh(f"{path}{sep}per_page=100&page={page}"))
        items += chunk
        if len(chunk) < 100:
            return items
        page += 1


def fetch_alerts(repo: str) -> list[dict]:
    return paged(f"repos/{repo}/code-scanning/alerts?state=open&ref={REF}")


def fetch_issues(repo: str) -> list[dict]:
    items = paged(f"repos/{repo}/issues?labels={LABEL}&state=all")
    return [i for i in items if "pull_request" not in i]


def apply(repo: str, action: tuple) -> str:
    kind, key, issue, body = action
    if kind == "create":
        made = json.loads(gh(f"repos/{repo}/issues", data={"title": title(key), "body": body, "labels": [LABEL]}))
        return f"opened {made['html_url']}"
    number = issue["number"]
    if kind == "close":
        gh("-X", "PATCH", f"repos/{repo}/issues/{number}", data={"state": "closed", "state_reason": "completed"})
        return f"closed {issue['html_url']} (no open alert left)"
    patch = {"body": body, "title": title(key)}
    if kind == "reopen":
        patch.update(state="open", state_reason="reopened")
    gh("-X", "PATCH", f"repos/{repo}/issues/{number}", data=patch)
    return f"{'reopened' if kind == 'reopen' else 'updated'} {issue['html_url']}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    repo = os.environ["GITHUB_REPOSITORY"]

    alerts = fetch_alerts(repo)
    groups = group_alerts(alerts)
    actions = plan(groups, fetch_issues(repo))
    print(f"{len(alerts)} open alert(s) on develop in {len(groups)} group(s); {len(actions)} change(s)")
    for action in actions:
        if args.dry_run:
            print(f"would {action[0]}: {title(action[1])}")
        else:
            print(apply(repo, action))
    return 0


if __name__ == "__main__":
    sys.exit(main())
