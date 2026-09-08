#!/usr/bin/env python3
"""Per-commit capture for the Vote-App-polity worktree — Lot 0.5, tier 1.

Appends one JSON line per commit to docs/journal/commits.jsonl: an
LLM-free, exhaustive, append-only trace. It exists so /log-session and a
future automatic-gotcha-memory pass (tiers 2 and 3 of Lot 0.5 — see
PLAN_SOLIDITE_TECHNIQUE.md) have real per-commit signal to work from,
instead of reconstructing what happened from memory at the end of a
session. See docs/README.md for how this surface relates to the others.

Worktree guard (read this before touching WORKTREE_NAME): git hooks live
under `.git/hooks/`, which is the *main* repository's directory — every
worktree shares the same one (`git rev-parse --git-path hooks` from inside
Vote-App-polity resolves to Vote-App/.git/hooks, not a worktree-local
directory). So this script runs on every commit in every worktree unless it
self-excludes, and it does: it is a strict no-op anywhere but the polity
worktree. Matching on the worktree's top-level directory name is simple and
debuggable; update WORKTREE_NAME below if that worktree is ever renamed.

Never blocks a commit: every failure path prints a warning to stderr and
returns success. A capture script that can fail a commit is worse than no
capture script.

Does not commit anything itself (recursive-hook and commit-storm territory
on a repo already producing ~360 commits/month — see Lot 0.5 in the plan).
It appends and `git add`s the journal file; the update rides along with
whatever the next real commit happens to be. If nothing follows soon, the
update sits staged-but-uncommitted, which is fine — the file is a trace,
not something that needs to be perfectly in sync commit-by-commit.

Installed via the repo's existing pre-commit framework
(`pre-commit install --hook-type post-commit` — see .pre-commit-config.yaml),
not a hand-written .git/hooks/post-commit file, so `pre-commit uninstall`
and the rest of the existing hook tooling keep working normally.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKTREE_NAME = "Vote-App-polity"
JOURNAL_RELATIVE = Path("docs/journal/commits.jsonl")

# Best-effort cross-reference against the polity worktree's own Claude Code
# memory namespace (not this repo's — a sibling directory keyed by the
# worktree's absolute path). Read-only, and entirely optional: a missing or
# unreadable memory directory just means this signal is empty, never an
# error.
POLITY_MEMORY_DIR = Path(
    "/home/burbanit0/.claude/projects/-home-burbanit0-Vote-App-polity/memory"
)

FIX_REVERT_RE = re.compile(r"\b(fix|revert|retry|workaround)\b", re.IGNORECASE)
GIT_REVERT_SUBJECT_RE = re.compile(r'^Revert "')
ACCEPTANCE_PATH_RE = re.compile(r"fast_api_voter/scripts/.*(_results\.md$|_runs/)")
POLITY_CONFIG_RE = re.compile(r"fast_api_voter/api/domain/polity/.*\.ya?ml$")

# A file touched this many times (or more) within OSCILLATION_WINDOW_DAYS of
# the current commit, including the current one, is flagged as oscillating —
# a signature of trial-and-error on the same parameter rather than a single
# deliberate change. Both numbers are deliberately low: better to over-flag
# early (a human/agent glancing at the signal costs little) than to miss the
# pattern the plan actually cares about.
OSCILLATION_THRESHOLD = 3
OSCILLATION_WINDOW_DAYS = 14


def toplevel() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip())
    except Exception:
        return None


def commit_meta(top: Path) -> tuple[str, str, str, str]:
    out = subprocess.run(
        ["git", "show", "-s", "--format=%H%x1f%aI%x1f%s", "HEAD"],
        cwd=top,
        capture_output=True,
        text=True,
        check=True,
    )
    sha, iso_date, subject = out.stdout.strip().split("\x1f")
    branch_out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=top,
        capture_output=True,
        text=True,
        check=True,
    )
    return sha, iso_date, branch_out.stdout.strip(), subject


def diff_stat(top: Path) -> tuple[list[str], int, int]:
    # --format= : no commit header, just the numstat body. Works uniformly
    # for the repo's very first commit too (no HEAD~1 to diff against).
    out = subprocess.run(
        ["git", "show", "--numstat", "--format=", "HEAD"],
        cwd=top,
        capture_output=True,
        text=True,
        check=True,
    )
    files: list[str] = []
    insertions = deletions = 0
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        files.append(path)
        if added.isdigit():
            insertions += int(added)
        if removed.isdigit():
            deletions += int(removed)
    return files, insertions, deletions


def load_recent_entries(journal: Path, since: datetime) -> list[dict[str, Any]]:
    if not journal.exists():
        return []
    entries = []
    with journal.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry_date = datetime.fromisoformat(entry["date"])
            except Exception:
                continue
            if entry_date >= since:
                entries.append(entry)
    return entries


def oscillating_files(
    journal: Path, files: list[str], now: datetime
) -> list[str]:
    since = now - timedelta(days=OSCILLATION_WINDOW_DAYS)
    recent = load_recent_entries(journal, since)
    counts: dict[str, int] = {f: 1 for f in files}  # count the current commit
    for entry in recent:
        for f in entry.get("files", []):
            if f in counts:
                counts[f] += 1
    return sorted(f for f, n in counts.items() if n >= OSCILLATION_THRESHOLD)


def flagged_by_memory(files: list[str]) -> list[dict[str, str]]:
    if not POLITY_MEMORY_DIR.is_dir():
        return []
    hits: list[dict[str, str]] = []
    try:
        memory_files = sorted(POLITY_MEMORY_DIR.glob("*.md"))
    except Exception:
        return []
    for mem_path in memory_files:
        try:
            text = mem_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for f in files:
            # Match on the file's basename, not the full path: memories
            # written in prose reference `run_polity_simulation.py`, not the
            # full repo-relative path.
            basename = f.rsplit("/", 1)[-1]
            if basename and basename in text:
                hits.append({"file": f, "memory": mem_path.name})
    return hits


def compute_signals(
    top: Path, journal: Path, files: list[str], subject: str, now: datetime
) -> dict[str, Any]:
    return {
        "is_fix_or_revert": bool(
            FIX_REVERT_RE.search(subject) or GIT_REVERT_SUBJECT_RE.match(subject)
        ),
        "touches_acceptance_results": any(
            ACCEPTANCE_PATH_RE.search(f) for f in files
        ),
        "touches_polity_config": [f for f in files if POLITY_CONFIG_RE.search(f)],
        "oscillating_files": oscillating_files(journal, files, now),
        "flagged_by_memory": flagged_by_memory(files),
    }


def capture(top: Path) -> None:
    sha, iso_date, branch, subject = commit_meta(top)
    files, insertions, deletions = diff_stat(top)
    journal = top / JOURNAL_RELATIVE
    now = datetime.fromisoformat(iso_date)
    signals = compute_signals(top, journal, files, subject, now)

    entry = {
        "sha": sha,
        "date": iso_date,
        "branch": branch,
        "subject": subject,
        "files": files,
        "insertions": insertions,
        "deletions": deletions,
        "signals": signals,
    }

    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Stage only the journal file — never commit. See module docstring for
    # why this rides along with the next real commit instead of creating
    # its own.
    subprocess.run(
        ["git", "add", "--", str(JOURNAL_RELATIVE)],
        cwd=top,
        check=False,
    )


def main() -> int:
    top = toplevel()
    if top is None:
        return 0
    if top.name != WORKTREE_NAME:
        return 0
    try:
        capture(top)
    except Exception as exc:  # never block a commit over this
        print(f"[git_commit_capture] non-fatal: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
