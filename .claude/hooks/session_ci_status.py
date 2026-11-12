#!/usr/bin/env python3
"""SessionStart hook (CI hardening plan, phase 4): say whether polity is green.

polity sat red for two days (2026-09-30 to 10-02) with nobody noticing. This
puts the tip's CI state in front of every session: one line when green, the
failing workflows and their run links when not. It reads GitHub's public API
(the repo is public; GH_TOKEN is used when set), never blocks and never fails a
session: any error means silence.

Also the backend of /ci-status (`--verbose`: every workflow on the tip).
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request

REPO = "Burbanit0/Vote-App"
BRANCH = "polity"
TIMEOUT_S = 5


def get(path: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "vote-app-ci-status"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    cafile = next((p for p in (os.environ.get("SSL_CERT_FILE"), "/root/.ccr/ca-bundle.crt") if p and os.path.isfile(p)), None)
    ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
        return json.load(resp)


def fetch() -> tuple[str, list[dict]]:
    """The branch's real tip, and the push runs for exactly that commit.

    The tip comes from the branches endpoint, not from the newest run in a list:
    a list ordered by run creation can lead with an older commit (a re-run), and
    that reported a stale "green" for a red tip.
    """
    tip = get(f"branches/{BRANCH}")["commit"]["sha"]
    runs = get(f"actions/runs?head_sha={tip}&event=push&per_page=50").get("workflow_runs", [])
    return tip, runs


def summarize(tip: str, runs: list[dict], verbose: bool) -> str:
    head = f"polity tip {tip[:7]}"
    if not runs:
        return f"{head}: no CI runs yet for this commit."
    runs = sorted(runs, key=lambda r: (r.get("run_attempt") or 1, r.get("created_at") or ""), reverse=True)
    latest: dict[str, dict] = {}
    for r in runs:
        latest.setdefault(r["name"], r)  # latest attempt per workflow
    failed = [r for r in latest.values() if r.get("conclusion") in {"failure", "timed_out", "startup_failure"}]
    running = [r for r in latest.values() if r.get("status") != "completed"]
    head += f" ({runs[0].get('display_title', '')[:60]})"
    if failed:
        lines = [f"{head}: RED. Failing on push:"]
        lines += [f"  - {r['name']}: {r['html_url']}" for r in failed]
        lines.append("Diagnose with the voter-ci skill (real log, not the job name) before building on this branch.")
    elif running:
        lines = [f"{head}: CI still running ({', '.join(sorted(r['name'] for r in running))})."]
    else:
        lines = [f"{head}: green ({len(latest)} workflows)."]
    if verbose:
        lines += [f"  {r.get('conclusion') or r.get('status'):>10}  {name}" for name, r in sorted(latest.items())]
    return "\n".join(lines)


def main() -> None:
    verbose = "--verbose" in sys.argv
    if not verbose:
        try:
            json.load(sys.stdin)  # consume the hook payload; unused
        except Exception:  # noqa: BLE001
            pass
    try:
        text = summarize(*fetch(), verbose)
    except Exception as e:  # noqa: BLE001 -- never fail a session over a status line
        if verbose:
            print(f"Could not read CI status from GitHub: {e}")
        return
    if text:
        print(text)


if __name__ == "__main__":
    main()
