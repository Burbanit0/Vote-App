#!/usr/bin/env python3
"""The high-risk path list in .mergify.yml, as data: check it, and classify a PR.

The review hold covers PRs that touch the voting engine, the CI safety net or a
test oracle: they wait until the owner reviews them (`/reviewed <sha>`). The
list lives in .mergify.yml's `merge_protections`; the `High-risk review gate`
status (human-review.yml, required by branch protection) is what enforces it.

Two modes:

  (default)    Fail when a pattern stops matching any tracked file. The
               patterns are anchored paths, so a routine rename
               (eslint.config.js -> .mjs, a moved golden file) would leave a
               pattern matching nothing and silently drop that file out of the
               hold. Same idea as the e2e suite's "routes are data" rule.
  --classify   Read changed paths on stdin (one per line) and print the ones
               the hold covers. `--author LOGIN` applies the `-author = ...`
               exceptions (Dependabot's version bumps in package.json).

Stdlib only (no PyYAML on a bare runner): the conditions are one per line,
`- files ~= <regex>` or `- files = <path>`, optionally grouped in an
`- and:` block with `- -author = <login>`, which this reads directly.

Usage: python3 scripts/check_mergify_protected_paths.py
       git diff --name-only ... | python3 scripts/check_mergify_protected_paths.py --classify --author LOGIN
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
CONDITION = re.compile(r"^\s*-\s*files\s*(~=|=)\s*(\S.*?)\s*$")
NOT_AUTHOR = re.compile(r"^\s*-\s*-author\s*=\s*(\S+)\s*$")
AND_BLOCK = re.compile(r"^(\s*)-\s*and:\s*$")


class Rule(NamedTuple):
    op: str  # "=" exact path, "~=" regex search
    pattern: str
    unless_author: frozenset[str]  # PRs by these authors are not held by this rule

    def matches(self, path: str) -> bool:
        return path == self.pattern if self.op == "=" else re.search(self.pattern, path) is not None


def _strip(line: str) -> str:
    return "" if line.lstrip().startswith("#") else line.split(" #", 1)[0].rstrip()


def rules(text: str) -> list[Rule]:
    lines = [_strip(raw) for raw in text.splitlines()]
    found: list[Rule] = []
    i = 0
    while i < len(lines):
        block = AND_BLOCK.match(lines[i])
        if block:
            # Everything indented deeper than `- and:` belongs to the block.
            indent, conds, authors = len(block.group(1)), [], set()
            i += 1
            while i < len(lines) and (not lines[i] or len(lines[i]) - len(lines[i].lstrip()) > indent):
                if (m := CONDITION.match(lines[i])):
                    conds.append((m.group(1), m.group(2)))
                elif (a := NOT_AUTHOR.match(lines[i])):
                    authors.add(a.group(1))
                i += 1
            found += [Rule(op, pat, frozenset(authors)) for op, pat in conds]
            continue
        if (m := CONDITION.match(lines[i])):
            found.append(Rule(m.group(1), m.group(2), frozenset()))
        i += 1
    return found


def conditions(text: str) -> list[tuple[str, str]]:
    return [(r.op, r.pattern) for r in rules(text)]


def held_paths(text: str, paths: list[str], author: str = "") -> list[str]:
    """The changed paths the review hold covers, for a PR by `author`."""
    active = [r for r in rules(text) if author not in r.unless_author]
    return [p for p in paths if any(r.matches(p) for r in active)]


def check() -> int:
    text = (ROOT / ".mergify.yml").read_text(encoding="utf-8")
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    found = rules(text)
    if not found:
        print("::error::no `files` conditions found in .mergify.yml -- this check needs updating")
        return 1
    dead = [f"files {r.op} {r.pattern}" for r in found if not any(r.matches(f) for f in files)]
    if dead:
        for d in dead:
            print(f"::error file=.mergify.yml::protected-path pattern matches no tracked file: {d}")
        print("A file the review hold protects was renamed or removed. Point the pattern at its new path.")
        return 1
    print(f"OK: all {len(found)} protected-path patterns in .mergify.yml match tracked files.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--classify", action="store_true", help="print the stdin paths the hold covers")
    ap.add_argument("--author", default="", help="PR author login, for `-author` exceptions")
    ap.add_argument("--config", type=Path, default=ROOT / ".mergify.yml")
    args = ap.parse_args(argv)
    if not args.classify:
        return check()
    text = args.config.read_text(encoding="utf-8")
    if not rules(text):
        print("no `files` conditions found in the config", file=sys.stderr)
        return 2  # never classify everything as low-risk because parsing broke
    paths = [line.strip() for line in sys.stdin if line.strip()]
    for path in held_paths(text, paths, args.author):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
