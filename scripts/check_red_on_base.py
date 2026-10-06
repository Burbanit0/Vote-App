#!/usr/bin/env python3
"""Do this PR's new tests fail on the code before the change? ("red on base")

CI hardening plan, phase 13a (W5: the same author writes the code and the
tests, so the tests can pass whether or not the change works). A test that
also passes on the base branch does not exercise the change. This runs the
tests a PR adds or changes against the base code, with the PR's test files
laid over it, and reports which of them fail there:

  feat/ fix/ bugfix/ hotfix/  ok when at least one new test is red on base;
                              WARN when every one passes on base, or when the
                              PR adds no test at all
  refactor/                   ok when no test file changed (behaviour must be
                              unchanged; CI already runs the whole suite);
                              WARN otherwise
  anything else               skipped (docs, chore, ci, test, perf, deps)

"Red" is either a failing assertion (`fails`) or a test that cannot even be
collected on base, because what it imports does not exist yet (`errors`):
both mean the test depends on the change.

New tests are Python test functions added or whose body changed, and JS/TS
test titles added (a JS body change is not detected: titles are matched by a
text scan, see check_test_integrity.js_tests). The base run uses the
dependencies installed for the head, so a test that only fails because a
dependency moved is reported as red on base too.

Usage: python3 scripts/check_red_on_base.py --base REF [--head REF] [--branch NAME]
         [--only py|js] [--summary FILE] [--strict]
Prints the report as JSON on stdout. Exit 0 (advisory), 1 with --strict on a
WARN, 2 when git fails.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_test_integrity import JS_TEST_FILE, PY_TEST_FILE, js_tests  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PY_ROOT = "fast_api_voter"  # where pytest runs (its pyproject holds the config)
JS_ROOT = "voter-app"       # where vitest runs
# What vitest collects (voter-app/vitest.config.ts `include`), relative to
# JS_ROOT. Playwright specs (tests/e2e/*.spec.ts) are not unit tests: sent to
# vitest they would run nothing and read as "errors on base".
VITEST_FILE = re.compile(r"^src/.*\.test\.(ts|tsx)$")
# Files a test needs besides itself, laid over the base too: fixtures,
# conftest, helpers living next to the tests.
SUPPORT = re.compile(r"(^|/)(conftest\.py|tests?/|__tests__/|__fixtures__/|fixtures/)")
TYPES = {"feat": "feat", "feature": "feat", "fix": "fix", "bugfix": "fix", "hotfix": "fix",
         "refactor": "refactor"}


class GitError(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def show(root: Path, ref: str, path: str) -> str | None:
    res = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True)
    return res.stdout.decode("utf-8", "replace") if res.returncode == 0 else None


def pr_type(branch: str) -> str:
    return TYPES.get(branch.split("/", 1)[0].lower(), "other")


# ── Which tests are new ────────────────────────────────────────────────────

def python_bodies(source: str | None) -> dict[str, str]:
    """{test id: source of the test} for a Python test file (empty if unparsable)."""
    if not source:
        return {}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return {}
    out: dict[str, str] = {}

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                deco = "\n".join(ast.unparse(d) for d in node.decorator_list)
                out[prefix + node.name] = deco + "\n" + ast.unparse(node)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                walk(node.body, f"{prefix}{node.name}::")

    walk(tree.body, "")
    return out


def new_tests(root: Path, base: str, head: str) -> tuple[dict[str, list[str]], list[str], int]:
    """({test file: [new or changed test ids]}, support files to overlay, test files changed)."""
    found: dict[str, list[str]] = {}
    support: list[str] = []
    touched = 0
    for line in git(root, "diff", "--name-status", "-M", f"{base}...{head}").splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        old, new = (parts[1], parts[2]) if status in "RC" else (parts[1], parts[1])
        if status == "D":
            continue
        is_py, is_js = bool(PY_TEST_FILE.search(new)), bool(JS_TEST_FILE.search(new))
        if is_py or is_js:
            touched += 1
            before, after = show(root, base, old), show(root, head, new)
            if is_py:
                was, now = python_bodies(before), python_bodies(after)
                ids = [t for t, body in now.items() if was.get(t) != body]
            else:
                was_t = set(js_tests(before)[0]) if before else set()
                ids = [t for t in js_tests(after or "")[0] if t not in was_t and not t.startswith("<dynamic")]
            if ids:
                found[new] = ids
        elif SUPPORT.search(new):
            support.append(new)
    return found, support, touched


# ── Running them on the base ───────────────────────────────────────────────

def overlay(root: Path, head: str, tree: Path, paths: list[str]) -> None:
    for p in paths:
        data = subprocess.run(["git", "show", f"{head}:{p}"], cwd=root, capture_output=True).stdout
        dest = tree / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)


def _module(rel: str) -> str:
    return rel[:-3].replace("/", ".")


def run_pytest(tree: Path, files: dict[str, list[str]], py_root: str, out: Path) -> dict[str, str]:
    """{file::id: passes|fails|errors} for each new Python test, run in `tree`."""
    rels = {f: f[len(py_root) + 1:] if py_root and f.startswith(py_root + "/") else f for f in files}
    subprocess.run([sys.executable, "-m", "pytest", *rels.values(), "-o", "addopts=", "-q",
                    "-p", "no:cacheprovider", "-p", "no:randomly", "--continue-on-collection-errors",
                    f"--junitxml={out}"],
                   cwd=tree / py_root if py_root else tree, capture_output=True, text=True)
    # The report is pytest's own output, but produced by running the PR's code:
    # parse it XXE-safely, as scripts/check_flaky_backend.py does. Imported here,
    # not at the top, so the no-tests job runs on a bare interpreter.
    import defusedxml.ElementTree as ET

    seen: dict[tuple[str, str], str] = {}
    if out.exists():
        for case in ET.parse(out).iter("testcase"):
            name = case.get("name", "").split("[", 1)[0]
            outcome = ("errors" if case.find("error") is not None else
                       "fails" if case.find("failure") is not None else
                       "skipped" if case.find("skipped") is not None else "passes")
            key = (case.get("classname", ""), name)
            # A parametrized test is red when any of its cases is.
            if seen.get(key) not in ("fails", "errors"):
                seen[key] = outcome
    result: dict[str, str] = {}
    for f, ids in files.items():
        mod = _module(rels[f])
        for t in ids:
            *cls, name = t.split("::")
            # Not in the report at all: the file failed to import on base.
            result[f"{f}::{t}"] = seen.get((".".join([mod, *cls]), name), "errors")
    return result


def _title_pattern(title: str) -> re.Pattern[str]:
    """A source title as vitest reports it: `%s`/`%d`/`$name`/`${…}` filled in."""
    out, i = [], 0
    for m in re.finditer(r"%[sdifjoOc#%]|\$\{[^}]*\}|\$[A-Za-z_][\w.]*", title):
        out += [re.escape(title[i:m.start()]), ".+?"]
        i = m.end()
    out.append(re.escape(title[i:]))
    return re.compile("".join(out) + r"\Z", re.S)


def run_vitest(root: Path, tree: Path, files: dict[str, list[str]], js_root: str, out: Path) -> dict[str, str]:
    """{file::title: passes|fails|errors} for each new JS/TS test, run in `tree`."""
    rels = {f: f[len(js_root) + 1:] if js_root and f.startswith(js_root + "/") else f for f in files}
    cwd = tree / js_root if js_root else tree
    head_modules = root / js_root / "node_modules"
    if head_modules.exists() and not (cwd / "node_modules").exists():
        (cwd / "node_modules").symlink_to(head_modules)
    subprocess.run(["npx", "vitest", "run", *rels.values(), "--reporter=json", f"--outputFile={out}"],
                   cwd=cwd, capture_output=True, text=True)
    by_file: dict[str, dict[str, str]] = {}
    if out.exists():
        for res in json.loads(out.read_text(encoding="utf-8")).get("testResults", []):
            name = os.path.relpath(res.get("name", ""), cwd)
            by_file[name] = [(a.get("title", ""), "passes" if a.get("status") == "passed" else
                              "skipped" if a.get("status") in ("skipped", "pending", "todo") else "fails")
                             for a in res.get("assertionResults", [])]
    result: dict[str, str] = {}
    for f, ids in files.items():
        reported = by_file.get(rels[f], [])
        for t in ids:
            pat = _title_pattern(t)
            got = [v for title, v in reported if pat.match(title)]
            # Not reported at all: the file did not load on base. A titled
            # family (it.each) is red when any of its cases is.
            result[f"{f}::{t}"] = ("errors" if not got else "fails" if "fails" in got else
                                   "passes" if "passes" in got else "skipped")
    return result


# ── Verdict ────────────────────────────────────────────────────────────────

def verdict(kind: str, results: dict[str, str], touched: int) -> tuple[str, str]:
    red = [k for k, v in results.items() if v in ("fails", "errors")]
    if kind == "other":
        return "skip", "not a feat/fix/refactor branch"
    if kind == "refactor":
        return (("ok", "no test file changed") if touched == 0 else
                ("warn", f"a refactor changed {touched} test file(s): behaviour should not move"))
    if not results:
        return "warn", "no new or changed test: nothing shows the change works"
    if red:
        return "ok", f"{len(red)} of {len(results)} new test(s) fail on the base code"
    return "warn", f"all {len(results)} new test(s) also pass on the base code: they don't exercise the change"


def summary(report: dict) -> str:
    icon = {"ok": "✅", "warn": "⚠️", "skip": "⏭️"}[report["verdict"]]
    lines = [f"### Red on base ({report['type']}): {icon} {report['reason']}", ""]
    if report["results"]:
        lines += ["| Test | On base |", "|---|---|"]
        mark = {"fails": "🔴 fails", "errors": "🔴 errors (does not load)", "passes": "🟢 passes",
                "skipped": "⚪ skipped"}
        lines += [f"| `{t}` | {mark.get(v, v)} |" for t, v in sorted(report["results"].items())]
    lines += ["", "_Advisory (phase 13a): a new test that also passes on the base code does not "
              "test the change._"]
    return "\n".join(lines)


def check(root: Path, base: str, head: str, branch: str, only: str | None = None,
          py_root: str = PY_ROOT, js_root: str = JS_ROOT) -> dict:
    kind = pr_type(branch)
    merge_base = git(root, "merge-base", base, head).strip()
    files, support, touched = new_tests(root, merge_base, head)
    results: dict[str, str] = {}
    if kind in ("feat", "fix") and files:
        def under(f: str, top: str) -> bool:
            return not top or f.startswith(top + "/")

        py = {f: ids for f, ids in files.items()
              if f.endswith(".py") and under(f, py_root) and only in (None, "py")}
        js = {f: ids for f, ids in files.items()
              if not f.endswith(".py") and under(f, js_root) and only in (None, "js")
              and VITEST_FILE.search(f[len(js_root) + 1:] if js_root else f)}
        outside = sorted(f for f in files if f not in py and f not in js
                         and only in (None, "py" if f.endswith(".py") else "js"))
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "base"
            git(root, "worktree", "add", "--detach", "-q", str(tree), merge_base)
            try:
                overlay(root, head, tree, [*files, *support])
                if py:
                    results.update(run_pytest(tree, py, py_root, Path(tmp) / "junit.xml"))
                if js:
                    results.update(run_vitest(root, tree, js, js_root, Path(tmp) / "vitest.json"))
            finally:
                git(root, "worktree", "remove", "--force", str(tree))
    else:
        outside = []
    v, why = verdict(kind, results, touched)
    if only and kind in ("feat", "fix") and not results and files and not outside:
        v, why = "skip", f"no new {'Python' if only == 'py' else 'JS/TS'} test; the other job covers the rest"
    if kind in ("feat", "fix") and not results and outside:
        v, why = "skip", f"the new tests are outside {py_root}/ and {js_root}/, which this check runs"
    return {"branch": branch, "type": kind, "base": merge_base, "verdict": v, "reason": why,
            "results": results, "test_files_changed": touched, "not_run": outside}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="the base branch ref (compared from its merge-base)")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--branch", help="the PR's head branch name (default: the current branch)")
    ap.add_argument("--only", choices=["py", "js"], help="run only the Python or only the JS/TS tests")
    ap.add_argument("--summary", type=Path, help="append a Markdown report to this file")
    ap.add_argument("--strict", action="store_true", help="exit 1 on a WARN")
    args = ap.parse_args(argv)
    try:
        branch = args.branch or git(ROOT, "rev-parse", "--abbrev-ref", args.head).strip()
        report = check(ROOT, args.base, args.head, branch, args.only)
    except GitError as e:
        print(f"check_red_on_base: {e}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(summary(report) + "\n")
    return 1 if args.strict and report["verdict"] == "warn" else 0


if __name__ == "__main__":
    sys.exit(main())
