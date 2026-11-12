"""Tests for the diff-mutation planner and report (stdlib unittest, throwaway git repos).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mutation_diff as md  # noqa: E402

ENGINE = textwrap.dedent('''
    def helper(x):
        return x + 1


    @cache
    def winner(votes):
        def inner(v):
            return v
        return max(votes, key=inner)


    class Tally:
        def add(self, v):
            self.n += v

        def total(self):
            return self.n
''')


class Repo:
    def __init__(self, tmp: str):
        self.root = Path(tmp)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")


class ChangedLines(unittest.TestCase):
    def test_added_and_changed_blocks_in_head_line_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("a.py", "1\n2\n3\n4\n5\n")
            r.write("gone.py", "x\n")
            r.commit()
            r.git("switch", "-q", "-c", "feat/x")
            r.write("a.py", "1\nTWO\n3\n4\n4b\n4c\n5\n")
            (r.root / "gone.py").unlink()
            r.write("new.py", "n1\nn2\n")
            r.commit()
            got = md.changed_lines("main", "HEAD", root=r.root)
            self.assertEqual(got, {"a.py": [(2, 2), (5, 6)], "new.py": [(1, 2)]})

    def test_a_pure_deletion_changes_no_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("a.py", "1\n2\n3\n")
            r.commit()
            r.git("switch", "-q", "-c", "fix/x")
            r.write("a.py", "1\n3\n")
            r.commit()
            self.assertEqual(md.changed_lines("main", "HEAD", root=r.root), {})


class Stryker(unittest.TestCase):
    def test_only_source_files_under_lib_hooks_services(self):
        changes = {"voter-app/src/lib/rules.ts": [(10, 12), (40, 40)],
                   "voter-app/src/hooks/useX.tsx": [(3, 4)],
                   "voter-app/src/lib/rules.test.ts": [(1, 9)],
                   "voter-app/src/lib/types.d.ts": [(1, 2)],
                   "voter-app/src/components/Card.tsx": [(5, 6)],
                   "voter-app/tests/e2e/flow.spec.ts": [(1, 1)]}
        self.assertEqual(md.stryker_targets(changes),
                         (["src/hooks/useX.tsx:3-4", "src/lib/rules.ts:10-12", "src/lib/rules.ts:40-40"], False))

    def test_a_large_diff_keeps_the_largest_ranges(self):
        changes = {"voter-app/src/lib/big.ts": [(i * 10, i * 10 + (i % 5)) for i in range(1, md.MAX_RANGES + 11)]}
        targets, sampled = md.stryker_targets(changes)
        self.assertTrue(sampled)
        self.assertEqual(len(targets), md.MAX_RANGES)
        self.assertNotIn("src/lib/big.ts:50-50", targets)  # the 1-line ranges are the ones dropped
        self.assertIn("src/lib/big.ts:40-44", targets)     # a 5-line range is kept

    def test_report_rows(self):
        report = {"files": {"src/lib/r.ts": {"mutants": [
            {"status": "Killed", "mutatorName": "BlockStatement", "replacement": "{}",
             "location": {"start": {"line": 3}}},
            {"status": "Survived", "mutatorName": "EqualityOperator", "replacement": "i <= n",
             "location": {"start": {"line": 9}}},
            {"status": "NoCoverage", "mutatorName": "StringLiteral", "location": {"start": {"line": 12}}},
            {"status": "CompileError", "mutatorName": "X", "location": {"start": {"line": 1}}}]}}}
        md_text = md.summary("stryker", md.stryker_results(report))
        self.assertIn("**33%** of the mutants on the changed lines are killed (1 killed, 2 survived, 1 other)",
                      md_text)
        self.assertIn("| `src/lib/r.ts:9` | EqualityOperator → i <= n | Survived |", md_text)
        self.assertIn("| `src/lib/r.ts:12` | StringLiteral | NoCoverage |", md_text)


class Mutmut(unittest.TestCase):
    def test_changed_lines_map_to_their_function_or_method(self):
        lines = ENGINE.splitlines()
        at = {name: lines.index(text) + 1 for name, text in
              [("helper", "    return x + 1"), ("deco", "@cache"), ("inner", "        return v"),
               ("total", "        return self.n")]}
        self.assertEqual(md.enclosing_keys(ENGINE, [(at["helper"], at["helper"])]), ["x_helper"])
        self.assertEqual(md.enclosing_keys(ENGINE, [(at["deco"], at["deco"])]), ["x_winner"])
        self.assertEqual(md.enclosing_keys(ENGINE, [(at["inner"], at["inner"])]), ["x_winner"])
        self.assertEqual(md.enclosing_keys(ENGINE, [(at["total"], at["total"])]), ["xǁTallyǁtotal"])
        self.assertEqual(md.enclosing_keys(ENGINE, [(1, 1)]), [])  # a blank line, outside any function

    def test_targets_are_limited_to_the_configured_source_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            r.write("fast_api_voter/pyproject.toml", '[tool.mutmut]\nsource_paths = ["api/engine/rules.py"]\n')
            r.write("fast_api_voter/api/engine/rules.py", ENGINE)
            r.write("fast_api_voter/api/other.py", "def f():\n    return 1\n")
            r.commit()
            r.git("switch", "-q", "-c", "fix/x")
            r.write("fast_api_voter/api/engine/rules.py", ENGINE.replace("x + 1", "x + 2"))
            r.write("fast_api_voter/api/other.py", "def f():\n    return 2\n")
            r.commit()
            changes = md.changed_lines("main", "HEAD", root=r.root)
            self.assertEqual(md.mutmut_targets(changes, "HEAD", root=r.root),
                             ["api.engine.rules.x_helper__mutmut_*"])

    def test_results_text(self):
        text = ("    api.e.x_f__mutmut_1: killed\n    api.e.x_f__mutmut_2: survived\n"
                "    api.e.xǁTǁm__mutmut_1: no tests\n    api.e.x_f__mutmut_3: timeout\n")
        rows = md.mutmut_results(text)
        self.assertEqual([(r["where"], r["status"]) for r in rows],
                         [("api.e.x_f__mutmut_1", "killed"), ("api.e.x_f__mutmut_2", "survived"),
                          ("api.e.xǁTǁm__mutmut_1", "no tests"), ("api.e.x_f__mutmut_3", "timeout")])
        self.assertIn("**50%**", md.summary("mutmut", rows))

    def test_results_are_kept_to_the_planned_patterns(self):
        text = ("    api.e.x_f__mutmut_1: killed\n    api.e.x_g__mutmut_1: not checked\n"
                "    api.e.x_fg__mutmut_1: not checked\n")
        rows = md.mutmut_results(text, ["api.e.x_f__mutmut_*"])
        self.assertEqual([r["where"] for r in rows], ["api.e.x_f__mutmut_1"])


class Summary(unittest.TestCase):
    def test_a_replacement_cannot_break_the_table(self):
        rows = [{"where": "f:1", "status": "Survived", "what": "LogicalOperator → a || b\n  && c"}]
        line = [ln for ln in md.summary("stryker", rows).splitlines() if ln.startswith("| `f:1`")][0]
        self.assertEqual(line, "| `f:1` | LogicalOperator → a \\|\\| b && c | Survived |")

    def test_nothing_to_score(self):
        self.assertIn("No mutant on the changed lines", md.summary("mutmut", []))

    def test_sampled_note_and_survivor_cap(self):
        rows = [{"where": f"f:{i}", "status": "Survived", "what": ""} for i in range(md.MAX_SURVIVORS + 3)]
        text = md.summary("stryker", rows, sampled=True)
        self.assertIn("…and 3 more in the run's artifact.", text)
        self.assertIn("the 40 largest changed ranges", text)


if __name__ == "__main__":
    unittest.main()
