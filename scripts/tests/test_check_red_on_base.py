"""Tests for the red-on-base check (stdlib unittest, throwaway git repos).

The pytest runs need pytest installed in the interpreter running the tests
(they are skipped otherwise); the vitest path is covered on its parsing only.

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_red_on_base as crb  # noqa: E402

HAS_PYTEST = importlib.util.find_spec("pytest") is not None
LIB = "def add(a, b):\n    return a + b\n"
TESTS = textwrap.dedent('''
    from lib import add

    def test_add():
        assert add(1, 2) == 3
''')


class Repo:
    """A git repo with lib.py + test_lib.py on `main`, and a branch to change them on."""

    def __init__(self, tmp: str):
        self.root = Path(tmp)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("lib.py", LIB)
        self.write("test_lib.py", TESTS)
        self.commit("base")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def branch(self, name: str) -> None:
        self.git("switch", "-q", "-c", name)

    def check(self, branch: str) -> dict:
        return crb.check(self.root, "main", "HEAD", branch, py_root="", js_root="")

    def check_only(self, branch: str, only: str) -> dict:
        return crb.check(self.root, "main", "HEAD", branch, only=only, py_root="", js_root="")


class NewTests(unittest.TestCase):
    def test_added_and_changed_python_tests_are_new_unchanged_ones_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("fix/x")
            r.write("test_lib.py", TESTS + "\ndef test_sub():\n    assert add(2, -1) == 1\n"
                    "\nclass TestMore:\n    def test_zero(self):\n        assert add(0, 0) == 0\n")
            r.write("tests/fixtures/data.json", "{}")
            r.write("README.md", "doc")
            r.commit("more tests")
            files, support, touched = crb.new_tests(r.root, "main", "HEAD")
            self.assertEqual(files, {"test_lib.py": ["test_sub", "TestMore::test_zero"]})
            self.assertEqual(support, ["tests/fixtures/data.json"])
            self.assertEqual(touched, 1)

    def test_a_changed_assertion_makes_the_test_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("fix/x")
            r.write("test_lib.py", TESTS.replace("== 3", "== 3 and add(0, 0) == 0"))
            r.commit("tighten")
            self.assertEqual(crb.new_tests(r.root, "main", "HEAD")[0], {"test_lib.py": ["test_add"]})

    def test_new_js_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("a.test.ts", "it('old', () => { expect(1).toBe(1) })\n")
            r.commit("js")
            r.branch("feat/x")
            r.write("a.test.ts", "it('old', () => { expect(2).toBe(2) })\nit('new', () => {})\n")
            r.commit("js more")
            self.assertEqual(crb.new_tests(r.root, "main", "HEAD")[0], {"a.test.ts": ["new"]})


@unittest.skipUnless(HAS_PYTEST, "pytest not installed in this interpreter")
class OnBase(unittest.TestCase):
    def test_a_fix_whose_test_fails_on_base_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("lib.py", "def add(a, b):\n    return a - b if b < 0 else a + b\n")  # the bug
            r.commit("bug")
            r.branch("fix/negative")
            r.write("lib.py", LIB)
            r.write("test_lib.py", TESTS + "\ndef test_negative():\n    assert add(2, -1) == 1\n")
            r.commit("fix")
            rep = r.check("fix/negative")
            self.assertEqual(rep["results"], {"test_lib.py::test_negative": "fails"})
            self.assertEqual(rep["verdict"], "ok")
            self.assertEqual(r.git("worktree", "list").count("\n"), 1)  # cleaned up

    def test_a_test_that_also_passes_on_base_is_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/whatever")
            r.write("lib.py", LIB + "\ndef mul(a, b):\n    return a * b\n")
            r.write("test_lib.py", TESTS + "\ndef test_still_adds():\n    assert add(2, 2) == 4\n")
            r.commit("feature without a real test")
            rep = r.check("feat/whatever")
            self.assertEqual(rep["results"], {"test_lib.py::test_still_adds": "passes"})
            self.assertEqual(rep["verdict"], "warn")
            self.assertIn("also pass on the base code", rep["reason"])

    def test_a_test_importing_what_the_feature_adds_errors_on_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/mul")
            r.write("lib.py", LIB + "\ndef mul(a, b):\n    return a * b\n")
            r.write("test_mul.py", "from lib import mul\n\ndef test_mul():\n    assert mul(2, 3) == 6\n")
            r.commit("mul")
            rep = r.check("feat/mul")
            self.assertEqual(rep["results"], {"test_mul.py::test_mul": "errors"})
            self.assertEqual(rep["verdict"], "ok")

    def test_a_parametrized_test_is_red_when_any_case_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("lib.py", "def add(a, b):\n    return a - b if b < 0 else a + b\n")
            r.commit("bug")
            r.branch("fix/p")
            r.write("lib.py", LIB)
            r.write("test_p.py", "import pytest\nfrom lib import add\n\n"
                    "@pytest.mark.parametrize('b', [1, -1])\ndef test_p(b):\n    assert add(0, b) == b\n")
            r.commit("fix")
            self.assertEqual(r.check("fix/p")["results"], {"test_p.py::test_p": "fails"})


    def test_one_file_that_cannot_load_does_not_hide_the_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/mul")
            r.write("lib.py", LIB + "\ndef mul(a, b):\n    return a * b\n")
            r.write("test_mul.py", "from lib import mul\n\ndef test_mul():\n    assert mul(2, 3) == 6\n")
            r.write("test_lib.py", TESTS + "\ndef test_zero():\n    assert add(0, 0) == 0\n")
            r.commit("mul, and a test that also passes on base")
            self.assertEqual(r.check("feat/mul")["results"],
                             {"test_mul.py::test_mul": "errors", "test_lib.py::test_zero": "passes"})


class Verdicts(unittest.TestCase):
    def test_types_from_the_branch_prefix(self):
        self.assertEqual([crb.pr_type(b) for b in ("feat/a", "feature/a", "hotfix/a", "refactor/a", "docs/a",
                                                   "dependabot/pip/x")],
                         ["feat", "feat", "fix", "refactor", "other", "other"])

    def test_no_new_test_on_a_feat_is_a_warning_and_other_branches_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/untested")
            r.write("lib.py", LIB + "\ndef mul(a, b):\n    return a * b\n")
            r.commit("no test")
            self.assertEqual(r.check("feat/untested")["verdict"], "warn")
            self.assertEqual(r.check("docs/untested")["verdict"], "skip")

    def test_a_refactor_must_leave_the_tests_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("refactor/x")
            r.write("lib.py", "def add(a, b):\n    return sum((a, b))\n")
            r.commit("same behaviour")
            self.assertEqual(r.check("refactor/x")["verdict"], "ok")
            r.write("test_lib.py", TESTS.replace("== 3", "> 0"))
            r.commit("and a looser test")
            rep = r.check("refactor/x")
            self.assertEqual(rep["verdict"], "warn")
            self.assertEqual(rep["results"], {})  # a refactor's tests are not run on base

    def test_new_tests_outside_the_suites_are_reported_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/tool")
            r.write("scripts/tests/test_tool.py", "def test_tool():\n    assert True\n")
            r.commit("a script test")
            rep = crb.check(r.root, "main", "HEAD", "feat/tool", py_root="app", js_root="web")
            self.assertEqual((rep["verdict"], rep["results"], rep["not_run"]),
                             ("skip", {}, ["scripts/tests/test_tool.py"]))

    def test_vitest_report_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree, out = Path(tmp), Path(tmp) / "v.json"
            report = {"testResults": [{"name": str(tree / "a.test.ts"), "assertionResults": [
                {"title": "new", "status": "failed"}, {"title": "kept", "status": "passed"}]}]}

            def fake_run(cmd, **kw):
                out.write_text(json.dumps(report))
                return mock.Mock(returncode=1)

            with mock.patch.object(crb.subprocess, "run", side_effect=fake_run) as run:
                got = crb.run_vitest(tree, tree, {"a.test.ts": ["new", "kept", "gone"]}, "", out)
            self.assertEqual(got, {"a.test.ts::new": "fails", "a.test.ts::kept": "passes",
                                   "a.test.ts::gone": "errors"})
            self.assertIn("--reporter=json", run.call_args[0][0])

    def test_playwright_specs_are_not_sent_to_vitest(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/e2e")
            r.write("web/tests/e2e/flow.spec.ts", "test('opens', async () => {})\n")
            r.commit("an e2e spec")
            rep = crb.check(r.root, "main", "HEAD", "feat/e2e", only="js", py_root="app", js_root="web")
            self.assertEqual((rep["verdict"], rep["results"], rep["not_run"]),
                             ("skip", {}, ["web/tests/e2e/flow.spec.ts"]))

    def test_interpolated_titles_match_what_vitest_reports(self):
        self.assertTrue(crb._title_pattern("case %s").match("case 1"))
        self.assertTrue(crb._title_pattern("elects ${name} first").match("elects Alice first"))
        self.assertTrue(crb._title_pattern("$rule wins").match("borda wins"))
        self.assertFalse(crb._title_pattern("case %s").match("other 1"))
        self.assertFalse(crb._title_pattern("a.b").match("aXb"))  # literal text stays literal
        with tempfile.TemporaryDirectory() as tmp:
            tree, out = Path(tmp), Path(tmp) / "v.json"
            report = {"testResults": [{"name": str(tree / "a.test.ts"), "assertionResults": [
                {"title": "case 1", "status": "passed"}, {"title": "case 2", "status": "failed"}]}]}

            def fake_run(cmd, **kw):
                out.write_text(json.dumps(report))
                return mock.Mock(returncode=1)

            with mock.patch.object(crb.subprocess, "run", side_effect=fake_run):
                got = crb.run_vitest(tree, tree, {"a.test.ts": ["case %s"]}, "", out)
            self.assertEqual(got, {"a.test.ts::case %s": "fails"})

    def test_a_job_with_no_new_test_of_its_language_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.branch("feat/py-only")
            r.write("test_more.py", "def test_more():\n    assert True\n")
            r.commit("a python test")
            rep = r.check_only("feat/py-only", "js")
            self.assertEqual(rep["verdict"], "skip")
            self.assertIn("no new JS/TS test", rep["reason"])

    def test_summary_table(self):
        md = crb.summary({"type": "fix", "verdict": "warn", "reason": "r",
                          "results": {"t.py::test_a": "passes", "t.py::test_b": "errors"}})
        self.assertIn("### Red on base (fix): ⚠️ r", md)
        self.assertIn("| `t.py::test_b` | 🔴 errors (does not load) |", md)


if __name__ == "__main__":
    unittest.main()
