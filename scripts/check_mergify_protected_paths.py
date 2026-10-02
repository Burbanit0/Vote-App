#!/usr/bin/env python3
"""Fail when a path pattern in .mergify.yml's high-risk merge protection stops
matching any tracked file.

The protection holds PRs that touch the voting engine, the CI safety net or a
test oracle until the owner reviews them. Its `files` patterns are anchored
paths, so a routine rename (eslint.config.js -> .mjs, a moved golden file)
would leave a pattern matching nothing and silently drop that file out of the
hold. Same idea as the e2e suite's "routes are data" rule: an entry with no
anchor in the tree fails the run.

Stdlib only (no PyYAML on a bare runner): the conditions are one per line,
`- files ~= <regex>` or `- files = <path>`, which this reads directly.

Usage: python3 scripts/check_mergify_protected_paths.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITION = re.compile(r"^\s*-\s*files\s*(~=|=)\s*(\S.*?)\s*$")


def conditions(text: str) -> list[tuple[str, str]]:
    found = []
    for line in text.splitlines():
        line = line.split(" #", 1)[0] if not line.lstrip().startswith("#") else ""
        m = CONDITION.match(line)
        if m:
            found.append((m.group(1), m.group(2)))
    return found


def main() -> int:
    text = (ROOT / ".mergify.yml").read_text(encoding="utf-8")
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    conds = conditions(text)
    if not conds:
        print("::error::no `files` conditions found in .mergify.yml -- this check needs updating")
        return 1
    dead = []
    for op, pattern in conds:
        if op == "=":
            hit = pattern in files
        else:
            regex = re.compile(pattern)
            hit = any(regex.search(f) for f in files)
        if not hit:
            dead.append(f"files {op} {pattern}")
    if dead:
        for d in dead:
            print(f"::error file=.mergify.yml::protected-path pattern matches no tracked file: {d}")
        print("A file the review hold protects was renamed or removed. Point the pattern at its new path.")
        return 1
    print(f"OK: all {len(conds)} protected-path patterns in .mergify.yml match tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
