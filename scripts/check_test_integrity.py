#!/usr/bin/env python3
"""Did this change weaken the test suite? A static diff of tests between two refs.

CI hardening plan, phase 11 (W2: tests can be weakened without tripping
anything). The required `High-risk review gate` (human-review.yml) holds a PR
until the owner reviews it when this reports a hold reason, the same way it
holds a PR touching a protected path:

  - **fewer tests**: the number of test cases in the changed test files went
    down (deleting a failing test is the classic way to get green). Counted
    net, across all changed files, so a test renamed or moved between files is
    not a hold; every test name that disappeared is still listed;
  - **tests switched off**: an added `it.skip`/`.only`/`.todo`/`xit`, or
    `pytest.mark.skip`/`skipif`/`xfail`/`pytest.skip()`, in any code file.

Reported but not held: other added silencers (`noqa`, `type: ignore`,
`eslint-disable`, `@ts-ignore`, `as any`: the quality ratchet already counts
those), and the assertion count going down.

Static on purpose: it parses Python with `ast` and scans JS/TS text, never
imports or runs the code, so the gate can run it on an untrusted PR head from
`pull_request_target`. Limits: parametrize/`each` cases count as one test, and
replacing a test with a weaker one is not caught (that is mutation testing's
job, phase 6).

Usage: python3 scripts/check_test_integrity.py --base REF --head REF [--summary FILE]
Prints one hold reason per line on stdout (nothing when the suite is intact);
exit 0 either way, 2 when git fails (the gate treats that as held).
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PY_TEST_FILE = re.compile(r"(^|/)(test_[^/]*|[^/]*_test)\.py$")
JS_TEST_FILE = re.compile(r"\.(test|spec)\.(ts|tsx|js|jsx|mjs|cjs)$")
CODE_FILE = re.compile(r"\.(py|ts|tsx|js|jsx|mjs|cjs)$")

# Kept in step with .claude/hooks/edit_guard.py's SILENCERS (the local, ask-
# first version of the same rule). Python is counted on the AST, so a pattern
# quoted inside a string (a guard's own test data) is not a disabled test.
JS_DISABLER = re.compile(
    r"(?<![\w.$])(?:it|test|describe|suite)(?:\.\w+)*?\.(?:skip|only|todo|fixme|fails|skipIf|runIf)\b"
    r"|(?<![\w.$])x(?:it|describe|test)\s*\(|(?<![\w.$])f(?:it|describe)\s*\(")
PY_DISABLERS = {("pytest", "mark", "skip"), ("pytest", "mark", "skipif"), ("pytest", "mark", "xfail"),
                ("pytest", "skip"), ("pytest", "xfail"), ("pytest", "importorskip")}
SILENCERS = {
    "`# noqa`": re.compile(r"#\s*noqa\b"),
    "`type: ignore`": re.compile(r"#\s*type:\s*ignore\b"),
    "`pragma: no cover`": re.compile(r"pragma:\s*no\s*cover"),
    "`eslint-disable`": re.compile(r"eslint-disable"),
    "`@ts-ignore`/`@ts-expect-error`": re.compile(r"@ts-(?:ignore|expect-error|nocheck)\b"),
    "`as any`": re.compile(r"\bas\s+any\b"),
}
JS_TEST_CALL = re.compile(r"(?<![\w.$])(it|test)((?:\.\w+)*)\s*\(")
# Modifiers a test declaration can carry; any other member (describe, step,
# beforeEach, setTimeout, slow, use, extend, info...) is not a test.
JS_TEST_MODIFIERS = {"each", "for", "concurrent", "sequential", "skip", "only", "todo",
                     "fixme", "fails", "failing", "skipIf", "runIf", "fail"}
# Modifiers whose first call takes arguments before the titled call:
# it.each([...])('title', fn), it.skipIf(cond)('title', fn).
JS_CURRIED = {"each", "for", "skipIf", "runIf"}
JS_EXPECT = re.compile(r"(?<![\w.$])expect(?:\.\w+)?\s*\(")


class GitError(RuntimeError):
    pass


def git(*args: str) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def show(ref: str, path: str) -> str | None:
    res = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    return res.stdout.decode("utf-8", "replace") if res.returncode == 0 else None


# ── Test inventories ──────────────────────────────────────────────────────

def python_tests(source: str) -> tuple[list[str], int] | None:
    """(test ids, assertion count), or None when the file doesn't parse."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    ids: list[str] = []

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                ids.append(prefix + node.name)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body, f"{prefix}{node.name}::")

    walk(tree.body, "")
    asserts = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert)) + sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and (n.func.attr.startswith("assert") or n.func.attr == "raises"))
    return ids, asserts


def _dotted(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return ()


def disablers(path: str, source: str | None) -> int:
    """How many test-disabling markers a file holds (0 when absent/unparseable)."""
    if not source:
        return 0
    if path.endswith(".py"):
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            return 0
        # `pytest.mark.skip` as a bare decorator and `pytest.mark.skip(...)` /
        # `pytest.skip(...)` both reach here as the same dotted Attribute once.
        return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Attribute) and _dotted(n) in PY_DISABLERS)
    return len(JS_DISABLER.findall(source))


def _skip_call(text: str, i: int) -> int:
    """Index just past the parenthesised call starting at text[i] == '('."""
    depth, quote = 0, ""
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = ""
        elif c in "'\"`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


_TITLE = re.compile(r"\s*(['\"`])((?:\\.|(?!\1)[^\\])*)\1", re.S)


def _title_at(text: str, i: int) -> str | None:
    m = _TITLE.match(text, i)
    return m.group(2) if m else None


def js_tests(source: str) -> tuple[list[str], int]:
    """(test titles, expect() count) for a JS/TS test file (text scan)."""
    ids: list[str] = []
    for m in JS_TEST_CALL.finditer(source):
        chain = [c for c in m.group(2).split(".") if c]
        if any(c not in JS_TEST_MODIFIERS for c in chain):
            continue  # test.describe(...), test.beforeEach(...), test.step(...)
        start = m.end() - 1  # the "("
        if chain and chain[-1] in JS_CURRIED:
            after = _skip_call(source, start)  # it.each([...])("title", ...)
            nxt = re.compile(r"\s*\(").match(source, after)
            if not nxt:
                continue
            start = nxt.end() - 1
        title = _title_at(source, start + 1)
        ids.append(title if title is not None else f"<dynamic title @{m.start()}>")
    return ids, len(JS_EXPECT.findall(source))


def inventory(ref: str, path: str) -> tuple[list[str], int, bool]:
    """(test ids, assertions, parsed) for one file at one ref."""
    source = show(ref, path)
    if source is None:
        return [], 0, True  # absent at this ref
    if PY_TEST_FILE.search(path):
        parsed = python_tests(source)
        return (parsed[0], parsed[1], True) if parsed else ([], 0, False)
    return (*js_tests(source), True)


# ── The comparison ─────────────────────────────────────────────────────────

def changed(base: str, head: str) -> list[tuple[str, str, str]]:
    """(status, old path, new path) for every file the head changed since base."""
    out = []
    for line in git("diff", "--name-status", "-M", f"{base}...{head}").splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        old, new = (parts[1], parts[2]) if status in "RC" else (parts[1], parts[1])
        out.append((status, old, new))
    return out


def is_test_file(path: str) -> bool:
    return bool(PY_TEST_FILE.search(path) or JS_TEST_FILE.search(path))


def compare(base: str, head: str) -> dict:
    merge_base = git("merge-base", base, head).strip()
    old_ids: Counter[str] = Counter()
    new_ids: Counter[str] = Counter()
    where: dict[str, str] = {}
    asserts = [0, 0]
    unparsed: list[str] = []
    disabled: list[str] = []
    silenced: list[str] = []
    for status, old, new in changed(merge_base, head):
        if is_test_file(old) or is_test_file(new):
            if is_test_file(old):
                ids, n, _ = inventory(merge_base, old)
                old_ids.update(ids)
                asserts[0] += n
                for i in ids:
                    where.setdefault(i, old)
            if is_test_file(new) and status != "D":
                ids, n, ok = inventory(head, new)
                new_ids.update(ids)
                asserts[1] += n
                if not ok:
                    unparsed.append(new)
        if status == "D" or not CODE_FILE.search(new):
            continue
        old_src = show(merge_base, old) if status != "A" else None
        before = disablers(old, old_src)
        after = disablers(new, show(head, new))
        if after > before:
            disabled.append(f"{after - before} more skip/only/xfail marker(s) in {new}")
        old_src = (show(merge_base, old) or "") if status != "A" else ""
        new_src = show(head, new) or ""
        for name, rx in SILENCERS.items():
            if len(rx.findall(new_src)) > len(rx.findall(old_src)):
                silenced.append(f"{name} in {new}")
    removed = sorted((old_ids - new_ids).elements())
    return {
        "before": sum(old_ids.values()), "after": sum(new_ids.values()),
        "removed": [f"{where.get(t, '?')}: {t}" for t in removed],
        "added": sum((new_ids - old_ids).values()),
        "asserts": asserts, "unparsed": unparsed, "disabled": disabled, "silenced": silenced,
    }


def hold_reasons(r: dict) -> list[str]:
    reasons = []
    if r["after"] < r["before"]:
        reasons.append(f"fewer tests: {r['before']} -> {r['after']} in the changed test files")
    reasons += [f"tests switched off: {d}" for d in r["disabled"]]
    reasons += [f"test file does not parse: {p}" for p in r["unparsed"]]
    return reasons


def summary(r: dict, reasons: list[str]) -> str:
    lines = ["## Test integrity", ""]
    lines.append(f"Tests in the changed test files: **{r['before']} → {r['after']}** "
                 f"({len(r['removed'])} gone, {r['added']} new). "
                 f"Assertions: {r['asserts'][0]} → {r['asserts'][1]}.")
    lines.append("")
    lines += (["**Held for the owner's review:**", *[f"- {x}" for x in reasons], ""] if reasons
              else ["Nothing that weakens the suite.", ""])
    if r["removed"]:
        lines += ["<details><summary>Test names that disappeared (renamed, moved or deleted)</summary>", "",
                  *[f"- `{x}`" for x in r["removed"]], "", "</details>", ""]
    if r["silenced"]:
        lines += ["Added silencers (reported, not held):", *[f"- {x}" for x in r["silenced"]], ""]
    if r["asserts"][1] < r["asserts"][0]:
        lines += ["Note: the changed test files assert less than before.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="the base branch ref (compared from its merge-base)")
    ap.add_argument("--head", required=True)
    ap.add_argument("--summary", type=Path, help="append a Markdown report to this file")
    args = ap.parse_args(argv)
    try:
        report = compare(args.base, args.head)
    except GitError as e:
        print(f"check_test_integrity: {e}", file=sys.stderr)
        return 2
    reasons = hold_reasons(report)
    for reason in reasons:
        print(reason)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(summary(report, reasons) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
