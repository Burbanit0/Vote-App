"""Tests for the static test-integrity diff (stdlib unittest, throwaway git repos).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_test_integrity as cti  # noqa: E402

PY_BASE = textwrap.dedent('''
    import pytest

    def test_a():
        assert 1

    def test_b():
        assert 2

    class TestGroup:
        def test_c(self):
            assert 3

    def helper():
        return "it.skip( and pytest.mark.skip in a string are data"
''')
TS_BASE = textwrap.dedent('''
    describe('rule', () => {
      it('elects the Condorcet winner', () => { expect(1).toBe(1); });
      test("ties break by index", () => { expect(2).toBe(2); });
      it.each([[1, 2], [3, (4)]])('case %s', (a) => { expect(a).toBeTruthy(); });
    });
''')


class Parsers(unittest.TestCase):
    def test_python_ids_and_asserts(self):
        ids, asserts = cti.python_tests(PY_BASE)
        self.assertEqual(ids, ["test_a", "test_b", "TestGroup::test_c"])
        self.assertEqual(asserts, 3)
        self.assertIsNone(cti.python_tests("def test_x(:\n"))

    def test_js_titles_including_each(self):
        ids, expects = cti.js_tests(TS_BASE)
        self.assertEqual(ids, ["elects the Condorcet winner", "ties break by index", "case %s"])
        self.assertEqual(expects, 3)

    def test_playwright_helpers_are_not_tests(self):
        src = ("test.describe('s', () => { test.beforeEach(async () => {}); test.setTimeout(5);"
               " test('a', async () => { await test.step('x', async () => {}); }); });")
        self.assertEqual(cti.js_tests(src)[0], ["a"])

    def test_every_js_disabler_form(self):
        for src in ["test.describe.skip('s', f)", "test.describe.only('s', f)", "test.fixme('t', f)",
                    "it.concurrent.skip('t', f)", "it.fails('t', f)", "it.skipIf(ci)('t', f)",
                    "test.skip(browserName === 'webkit')"]:
            with self.subTest(src=src):
                self.assertEqual(cti.disablers("a.spec.ts", src), 1)

    def test_title_scan_is_linear_on_hostile_input(self):
        import time
        t = time.perf_counter()
        cti.js_tests("it('" + "\\\\" * 5000 + "x")
        self.assertLess(time.perf_counter() - t, 1.0)

    def test_disablers_ignore_strings_and_count_real_markers(self):
        self.assertEqual(cti.disablers("t/test_x.py", PY_BASE), 0)
        marked = PY_BASE.replace("def test_b", "@pytest.mark.xfail(reason='x')\ndef test_b")
        marked += "\n@pytest.mark.skip\ndef test_d():\n    pytest.skip('no')\n"
        self.assertEqual(cti.disablers("t/test_x.py", marked), 3)
        self.assertEqual(cti.disablers("a.test.ts", "it.only('x', f); xit('y', g); expect.it('no')"), 2)
        self.assertEqual(cti.disablers("a.test.ts", "submit.skip(1); query.only()"), 0)


class Compare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(cti, "ROOT", self.root)
        self.patch.start()
        self.git("init", "-q", "-b", "main")
        self.write("api/tests/test_rules.py", PY_BASE)
        self.write("src/rules.test.ts", TS_BASE)
        self.write("src/rules.ts", "export const x = 1;\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "pr")

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       cwd=self.root, check=True, capture_output=True)

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def reasons(self) -> list[str]:
        return cti.hold_reasons(cti.compare("main", "pr"))

    def test_untouched_tests_are_clean(self):
        self.write("src/rules.ts", "export const x = 2;\n")
        self.commit("source only")
        self.assertEqual(self.reasons(), [])

    def test_deleting_a_test_is_held(self):
        self.write("api/tests/test_rules.py", PY_BASE.replace("def test_b():\n    assert 2\n", ""))
        self.commit("drop test_b")
        report = cti.compare("main", "pr")
        self.assertEqual(cti.hold_reasons(report), ["fewer tests: 3 -> 2 in the changed test files"])
        self.assertEqual(report["removed"], ["api/tests/test_rules.py: test_b"])

    def test_deleting_a_whole_test_file_is_held(self):
        (self.root / "src/rules.test.ts").unlink()
        self.commit("drop file")
        self.assertEqual(self.reasons(), ["fewer tests: 3 -> 0 in the changed test files"])

    def test_renaming_or_moving_tests_is_not_held_but_listed(self):
        self.write("api/tests/test_rules.py", PY_BASE.replace("def test_b", "def test_b_renamed"))
        self.git("mv", "src/rules.test.ts", "src/voting.test.ts")
        self.commit("rename")
        report = cti.compare("main", "pr")
        self.assertEqual(cti.hold_reasons(report), [])
        self.assertEqual(report["removed"], ["api/tests/test_rules.py: test_b"])

    def test_switching_a_test_off_is_held_even_with_new_tests(self):
        self.write("src/rules.test.ts", TS_BASE.replace("it('elects", "it.skip('elects")
                   + "it('another', () => {});\n")
        self.commit("skip one")
        self.assertEqual(self.reasons(), ["tests switched off: 1 more skip/only/xfail marker(s) in src/rules.test.ts"])

    def test_unparseable_test_file_is_held(self):
        self.write("api/tests/test_rules.py", PY_BASE + "\ndef test_broken(:\n")
        self.commit("broken")
        self.assertIn("test file does not parse: api/tests/test_rules.py", self.reasons())

    def test_silencers_are_reported_not_held(self):
        self.write("src/rules.ts", "export const x = (1 as any); // eslint-disable-line\n")
        self.commit("silence")
        report = cti.compare("main", "pr")
        self.assertEqual(cti.hold_reasons(report), [])
        self.assertEqual(sorted(report["silenced"]),
                         ["`as any` in src/rules.ts", "`eslint-disable` in src/rules.ts"])

    def test_branch_coverage_escape_hatches_are_reported(self):
        self.write("src/rules.ts", "/* v8 ignore else */\nexport const x = 1;\n")
        self.write("api/rules.py", "for x in []:  # pragma: no branch\n    pass\n")
        self.commit("hatches")
        report = cti.compare("main", "pr")
        self.assertEqual(cti.hold_reasons(report), [])
        self.assertEqual(sorted(report["silenced"]),
                         ["`pragma: no branch` in api/rules.py", "`v8 ignore` in src/rules.ts"])

    def test_renamed_file_keeps_its_silencers(self):
        self.write("src/rules.ts", "export const x = (1 as any);\n")
        self.commit("base silencer")
        self.git("branch", "-f", "main", "HEAD")
        self.git("mv", "src/rules.ts", "src/voting.ts")
        self.commit("rename")
        self.assertEqual(cti.compare("main", "pr")["silenced"], [])

    def test_main_reports_git_failure_as_exit_2(self):
        self.assertEqual(cti.main(["--base", "main", "--head", "no-such-ref"]), 2)


if __name__ == "__main__":
    unittest.main()
