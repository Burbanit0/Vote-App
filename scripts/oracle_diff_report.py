#!/usr/bin/env python3
"""Explain, in plain words, what a PR changed in the test oracles.

Several tests compare against committed reference files a script regenerates
(the engine parity fixture, the polity golden digest, the OpenAPI contract,
the ratchet baselines, the screenshot snapshots). Regenerating one after a
behaviour change makes its own check pass by design, so the review of such a
PR has to read the behaviour change itself, not a 300 KB JSON diff. This
script turns each changed oracle into that summary:

  engineParity.json   which rule now elects whom, scenario by scenario
  golden/*.json       which recorded values moved (event counts, hashes)
  openapi.gen.json    endpoints and schemas added, removed or changed
  baselines           each number that moved, and in which direction
  snapshots           which images were added, changed or removed

Static, like check_test_integrity.py: it reads both sides with `git show` and
never imports or runs PR code, so the review gate can run it on an untrusted
PR head. Report-only: it never changes the gate's decision.

Usage:
  python3 scripts/oracle_diff_report.py --base origin/polity --head HEAD [--summary FILE]
Prints the Markdown report (nothing when no oracle changed); --summary also
appends it to FILE. Exit 0, or 2 when git fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from check_test_integrity import GitError, changed, git, show

PARITY = "voter-app/src/lib/__fixtures__/engineParity.json"
OPENAPI = "fast_api_voter/openapi.gen.json"
GOLDEN = re.compile(r"^fast_api_voter/api/tests/golden/.+\.json$")
BASELINE = re.compile(r"^\.github/[^/]*baseline[^/]*\.json$")
SNAPSHOT = re.compile(r"(^|/)__snapshots__/|-snapshots/")
GENERATED_TEXT = {"voter-app/src/api/types.gen.ts"}

# Per-scenario fields that hold the engine's output; everything else is input.
PARITY_OUTPUTS = re.compile(r"[Ww]inners?$")
MAX_LINES = 25

STATUS_WORD = {"A": "added", "D": "removed", "M": "changed", "R": "renamed", "C": "copied", "T": "changed"}


def load_json(ref: str, path: str) -> Any:
    text = show(ref, path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def capped(lines: list[str], total: int | None = None) -> list[str]:
    total = len(lines) if total is None else total
    if total <= MAX_LINES:
        return lines
    return lines[:MAX_LINES] + [f"- … and {total - MAX_LINES} more"]


# ── Generic JSON: leaf paths ───────────────────────────────────────────────

def leaves(value: Any, prefix: str = "") -> dict[str, Any]:
    if prefix and isinstance(value, (dict, list)) and not value:
        return {prefix: value}  # an emptied container is a change too
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out.update(leaves(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    if isinstance(value, list):
        out = {}
        for i, v in enumerate(value):
            out.update(leaves(v, f"{prefix}[{i}]"))
        return out
    return {prefix: value}


def fmt(v: Any) -> str:
    if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40,64}", v):
        return v[:12]
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 40 else s[:37] + "…"


def json_leaf_diff(old: Any, new: Any) -> list[str]:
    a, b = leaves(old), leaves(new)
    lines = []
    for path in sorted(a.keys() | b.keys()):
        if path not in b:
            lines.append(f"- `{path}` removed (was {fmt(a[path])})")
        elif path not in a:
            lines.append(f"- `{path}` added: {fmt(b[path])}")
        elif a[path] != b[path]:
            x, y = a[path], b[path]
            arrow = ""
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) \
                    and not isinstance(x, bool) and not isinstance(y, bool):
                arrow = " ▲" if y > x else " ▼"
            lines.append(f"- `{path}`: {fmt(x)} → {fmt(y)}{arrow}")
    return capped(lines)


# ── Engine parity: winners by rule ─────────────────────────────────────────

def _split(scenario: dict) -> tuple[str, dict]:
    inputs = {k: v for k, v in scenario.items() if not PARITY_OUTPUTS.search(k)}
    outputs = {k: v for k, v in scenario.items() if PARITY_OUTPUTS.search(k)}
    return json.dumps(inputs, sort_keys=True), outputs


def _flat_outputs(outputs: dict) -> dict[str, Any]:
    """{rule: winner} from `winners`, plus each other output field as its own entry."""
    flat: dict[str, Any] = {}
    for k, v in outputs.items():
        if k == "winners" and isinstance(v, dict):
            flat.update(v)
        else:
            flat[k] = v
    return flat


def parity_diff(old: Any, new: Any) -> list[str]:
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ["- the fixture is not a JSON object on one side; read the raw diff"]
    lines: list[str] = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        if a is None and isinstance(b, list):
            lines.append(f"- **{key}**: new, {len(b)} scenarios")
            continue
        if b is None and isinstance(a, list):
            lines.append(f"- **{key}**: **removed** ({len(a)} scenarios no longer checked)")
            continue
        if not isinstance(a, list) or not isinstance(b, list):
            lines.append(f"- `{key}`: {fmt(a)} → {fmt(b)}")
            continue
        before = dict(_split(s) for s in a if isinstance(s, dict))
        after = dict(_split(s) for s in b if isinstance(s, dict))
        kept = before.keys() & after.keys()
        added = len(after.keys() - before.keys())
        removed = len(before.keys() - after.keys())
        moved: Counter[str] = Counter()
        new_field: Counter[str] = Counter()
        gone_field: Counter[str] = Counter()
        example: dict[str, str] = {}
        for inputs in kept:
            x, y = _flat_outputs(before[inputs]), _flat_outputs(after[inputs])
            for rule in x.keys() | y.keys():
                if rule not in x:
                    new_field[rule] += 1
                elif rule not in y:
                    gone_field[rule] += 1
                elif x[rule] != y[rule]:
                    moved[rule] += 1
                    example.setdefault(rule, f"{fmt(x[rule])} → {fmt(y[rule])}")
        notes = []
        if not kept and a and b:
            notes.append("every input profile was regenerated, so no winner can be compared one to one:"
                         " check why the generator's inputs changed")
        else:
            if added:
                notes.append(f"{added} added")
            if removed:
                notes.append(f"{removed} removed")
            if moved:
                notes.append(f"{sum(moved.values())} winners changed")
        lines.append(f"- **{key}**: {len(b)} scenarios" + (f" ({'; '.join(notes)})" if notes
                     else "" if new_field or gone_field else " (reordered only)"))
        for rule, n in sorted(moved.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  - `{rule}`: {n} scenario{'s' if n > 1 else ''} changed winner, e.g. {example[rule]}")
        for rule, n in sorted(new_field.items()):
            lines.append(f"  - `{rule}`: new output, now checked on {n} scenarios")
        for rule, n in sorted(gone_field.items()):
            lines.append(f"  - `{rule}`: **no longer checked** on {n} scenarios")
    return capped(lines) if lines else ["- no winner changed (formatting or ordering only)"]


# ── OpenAPI: endpoints and schemas ─────────────────────────────────────────

HTTP = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def _operations(spec: Any) -> dict[str, Any]:
    ops = {}
    for path, item in (spec.get("paths") or {}).items() if isinstance(spec, dict) else []:
        for method, op in (item or {}).items():
            if method in HTTP:
                ops[f"{method.upper()} {path}"] = op
    return ops


def _schemas(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        return {}
    return (spec.get("components") or {}).get("schemas") or {}


def openapi_diff(old: Any, new: Any) -> list[str]:
    lines = []
    for label, a, b in (("endpoint", _operations(old), _operations(new)),
                        ("schema", _schemas(old), _schemas(new))):
        for name in sorted(b.keys() - a.keys()):
            lines.append(f"- {label} added: `{name}`")
        for name in sorted(a.keys() - b.keys()):
            lines.append(f"- {label} **removed**: `{name}`")
        for name in sorted(a.keys() & b.keys()):
            if a[name] != b[name]:
                lines.append(f"- {label} changed: `{name}`")
    if not lines and old != new:
        lines.append("- only metadata changed (info, servers, tags)")
    return capped(lines)


# ── The report ─────────────────────────────────────────────────────────────

def is_oracle(path: str) -> bool:
    return bool(path == PARITY or path == OPENAPI or path in GENERATED_TEXT
                or GOLDEN.search(path) or BASELINE.search(path) or SNAPSHOT.search(path))


def report(base: str, head: str) -> str:
    entries = [(s, old, new) for s, old, new in changed(base, head) if is_oracle(old) or is_oracle(new)]
    if not entries:
        return ""
    mb = git("merge-base", base, head).strip()  # the side `git diff base...head` compares with
    sections: list[str] = []
    snapshots: list[str] = []
    for status, old, new in entries:
        if SNAPSHOT.search(new) or SNAPSHOT.search(old):
            name = new if old == new else f"{old} → {new}"
            snapshots.append(f"- {STATUS_WORD.get(status, status)}: `{name}`")
            continue
        if status == "D":
            sections.append(f"### `{old}`\n\n- **removed** (its check no longer has a reference)")
            continue
        if status == "A":
            sections.append(f"### `{new}`\n\n- added")
            continue
        if new in GENERATED_TEXT:
            a, b = show(mb, old) or "", show(head, new) or ""
            regenerated = any(OPENAPI in (o, n) for _, o, n in entries)
            why = ("regenerated from openapi.gen.json, see that section" if regenerated else
                   "**changed without openapi.gen.json changing: a hand edit, or a contract left stale**")
            sections.append(f"### `{new}`\n\n- {len(a.splitlines())} → {len(b.splitlines())} lines; {why}")
            continue
        before, after = load_json(mb, old), load_json(head, new)
        if new == PARITY:
            body = parity_diff(before, after)
        elif new == OPENAPI:
            body = openapi_diff(before, after)
        else:
            body = json_leaf_diff(before, after) or ["- formatting only"]
        sections.append(f"### `{new}`\n\n" + "\n".join(body))
    if snapshots:
        sections.append("### Screenshot snapshots\n\n" + "\n".join(capped(snapshots))
                        + "\n\nOpen the images in the PR's Files tab to compare them.")
    return ("## Test oracle changes\n\n"
            "These files are what the tests compare against. A regeneration makes its own"
            " check pass, so this is the behaviour change to review.\n\n" + "\n\n".join(sections))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="the base branch ref (compared from its merge-base)")
    ap.add_argument("--head", required=True)
    ap.add_argument("--summary", type=Path, help="append the Markdown report to this file")
    args = ap.parse_args(argv)
    try:
        text = report(args.base, args.head)
    except GitError as e:
        print(f"oracle_diff_report: {e}", file=sys.stderr)
        return 2
    if text:
        print(text)
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as fh:
                fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
