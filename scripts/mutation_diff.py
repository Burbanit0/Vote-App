#!/usr/bin/env python3
"""Mutation testing on the lines a PR changes ("diff mutation").

CI hardening plan, phase 6. Line coverage proves a line ran, not that any test
would fail if it were wrong. The full mutation runs (mutation-testing.yml)
answer that for four files, weekly, in hours. This scopes the same tools to
what a PR changed, so the PR shows the mutants its tests let survive: each
survivor is a changed line no test really checks.

  stryker  voter-app/src/{lib,hooks,services}/**/*.ts(x) (not tests): the
           changed line ranges become `--mutate file:start-end`.
  mutmut   the files in fast_api_voter's [tool.mutmut] source_paths only (the
           engine and the theory workers; EXP-015 explains why mutmut cannot
           run against the whole api/ package): changed lines are mapped to
           their enclosing functions, which become mutmut's name patterns.

Usage:
  mutation_diff.py plan   --tool stryker|mutmut --base REF [--head REF]
      prints one argument per line (nothing when there is nothing to mutate)
  mutation_diff.py report --tool stryker|mutmut --input FILE [--sampled]
      prints a Markdown summary of a Stryker JSON report / `mutmut results`
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS_ROOT = "voter-app"
PY_ROOT = "fast_api_voter"
STRYKER_FILE = re.compile(r"^voter-app/src/(lib|hooks|services)/.+\.tsx?$")
NOT_SOURCE = re.compile(r"\.(test|spec)\.tsx?$|\.d\.ts$")
MAX_RANGES = 40       # Stryker --mutate ranges per run, the largest kept
MAX_SURVIVORS = 15    # listed in the summary; the rest are in the artifact
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
KILLED = {"Killed", "Timeout", "killed", "timeout"}
SURVIVED = {"Survived", "NoCoverage", "survived", "no tests"}


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def changed_lines(base: str, head: str, root: Path = ROOT) -> dict[str, list[tuple[int, int]]]:
    """{path: [(first, last) line of each added/changed block]} in the head version."""
    out: dict[str, list[tuple[int, int]]] = {}
    path = None
    for line in git("diff", "-U0", "--no-color", f"{base}...{head}", root=root).splitlines():
        if line.startswith("+++ "):
            path = None if line == "+++ /dev/null" else line[6:]
        elif path and (m := HUNK.match(line)):
            start, count = int(m.group(1)), int(m.group(2) or "1")
            if count:
                out.setdefault(path, []).append((start, start + count - 1))
    return out


# ── Stryker ────────────────────────────────────────────────────────────────

def stryker_targets(changes: dict[str, list[tuple[int, int]]]) -> tuple[list[str], bool]:
    """(--mutate values relative to voter-app/, sampled?)."""
    ranges = [(path, a, b) for path, spans in changes.items()
              if STRYKER_FILE.match(path) and not NOT_SOURCE.search(path) for a, b in spans]
    sampled = len(ranges) > MAX_RANGES
    if sampled:
        ranges = sorted(ranges, key=lambda r: r[2] - r[1], reverse=True)[:MAX_RANGES]
    return [f"{p[len(JS_ROOT) + 1:]}:{a}-{b}" for p, a, b in sorted(ranges)], sampled


def stryker_results(report: dict) -> list[dict]:
    rows = []
    for path, f in report.get("files", {}).items():
        for m in f.get("mutants", []):
            rows.append({"where": f"{path}:{m.get('location', {}).get('start', {}).get('line', '?')}",
                         "status": m.get("status", ""), "what": f"{m.get('mutatorName', '')}"
                         + (f" → {m['replacement']}" if m.get("replacement") else "")})
    return rows


# ── mutmut ─────────────────────────────────────────────────────────────────

def mutmut_sources(root: Path = ROOT) -> list[str]:
    conf = tomllib.loads((root / PY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return [f"{PY_ROOT}/{p}" for p in conf.get("tool", {}).get("mutmut", {}).get("source_paths", [])]


def enclosing_keys(source: str, spans: list[tuple[int, int]]) -> list[str]:
    """mutmut keys (x_func / xǁClassǁmethod) of the top-level functions and
    methods overlapping the changed spans. A nested def counts as its outer
    function: mutmut mutates (and names) only the outer one."""
    tree = ast.parse(source)
    found: list[str] = []

    def overlaps(node: ast.AST) -> bool:
        end = getattr(node, "end_lineno", node.lineno)
        first = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
        return any(a <= end and b >= first for a, b in spans)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and overlaps(node):
            found.append(f"x_{node.name}")
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and overlaps(sub):
                    found.append(f"xǁ{node.name}ǁ{sub.name}")
    return found


def mutmut_targets(changes: dict[str, list[tuple[int, int]]], head: str, root: Path = ROOT) -> list[str]:
    """mutmut name patterns for the changed functions in its source_paths."""
    patterns = []
    for path in mutmut_sources(root):
        if path not in changes:
            continue
        source = git("show", f"{head}:{path}", root=root)
        module = path[len(PY_ROOT) + 1:-3].replace("/", ".")
        patterns += [f"{module}.{key}__mutmut_*" for key in enclosing_keys(source, changes[path])]
    return patterns


RESULT_LINE = re.compile(r"^\s*(\S+__mutmut_\d+):\s*(.+?)\s*$")


def mutmut_results(text: str, patterns: list[str] | None = None) -> list[dict]:
    """Rows of `mutmut results --all true`, kept to the planned patterns: the
    listing covers every mutant of every source file, the rest "not checked"."""
    rows = []
    for line in text.splitlines():
        if (m := RESULT_LINE.match(line)) and (
                not patterns or any(fnmatch.fnmatchcase(m.group(1), p) for p in patterns)):
            rows.append({"where": m.group(1), "status": m.group(2), "what": ""})
    return rows


# ── Report ─────────────────────────────────────────────────────────────────

def _cell(text: str) -> str:
    """Text safe inside a Markdown table cell (a replacement can hold `||` or span lines)."""
    return " ".join(text.split()).replace("|", "\\|")


def summary(tool: str, rows: list[dict], sampled: bool = False) -> str:
    killed = [r for r in rows if r["status"] in KILLED]
    survived = [r for r in rows if r["status"] in SURVIVED]
    scored = len(killed) + len(survived)
    title = "Frontend (Stryker)" if tool == "stryker" else "Backend (mutmut)"
    out = [f"### Diff mutation: {title}", ""]
    if not scored:
        out.append("No mutant on the changed lines (nothing mutable, or no test reaches them).")
    else:
        out.append(f"**{100 * len(killed) / scored:.0f}%** of the mutants on the changed lines are killed "
                   f"({len(killed)} killed, {len(survived)} survived, {len(rows) - scored} other).")
        if survived:
            out += ["", "Survivors (each one is a changed line no test checks):", "",
                    "| Where | Mutation | Status |", "|---|---|---|"]
            out += [f"| `{r['where']}` | {_cell(r['what']) or '–'} | {r['status']} |"
                    for r in survived[:MAX_SURVIVORS]]
            if len(survived) > MAX_SURVIVORS:
                out.append(f"\n…and {len(survived) - MAX_SURVIVORS} more in the run's artifact.")
            if tool == "mutmut":
                out.append("\nTo see a survivor's change: `cd fast_api_voter && python -m mutmut show <name>`.")
    if sampled:
        out += ["", f"_Large diff: the {MAX_RANGES} largest changed ranges were mutated, not all of them._"]
    out += ["", "_Advisory (phase 6): a survivor means a test would still pass with that line broken._"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--tool", choices=["stryker", "mutmut"], required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--head", default="HEAD")
    r = sub.add_parser("report")
    r.add_argument("--tool", choices=["stryker", "mutmut"], required=True)
    r.add_argument("--input", type=Path, required=True)
    r.add_argument("--sampled", action="store_true")
    r.add_argument("--patterns", type=Path, help="mutmut: the planned name patterns, one per line")
    args = ap.parse_args(argv)
    if args.cmd == "plan":
        merge_base = git("merge-base", args.base, args.head).strip()
        changes = changed_lines(merge_base, args.head)
        if args.tool == "stryker":
            targets, sampled = stryker_targets(changes)
            if sampled:
                print("# sampled", file=sys.stderr)
        else:
            targets = mutmut_targets(changes, args.head)
        print("\n".join(targets))
        return 0
    text = args.input.read_text(encoding="utf-8") if args.input.exists() else ""
    if args.tool == "stryker":
        rows = stryker_results(json.loads(text)) if text else []
    else:
        patterns = args.patterns.read_text(encoding="utf-8").split() if args.patterns else None
        rows = mutmut_results(text, patterns)
    sys.stdout.write(summary(args.tool, rows, args.sampled))
    return 0


if __name__ == "__main__":
    sys.exit(main())
