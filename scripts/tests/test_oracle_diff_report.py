"""Tests for the test-oracle diff report (stdlib unittest, throwaway git repos).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_test_integrity as cti  # noqa: E402
import oracle_diff_report as odr  # noqa: E402

PROFILE_1 = {"candidates": ["A", "B", "C"], "ballots": [["A", "B", "C"], ["B", "C", "A"]]}
PROFILE_2 = {"candidates": ["A", "B"], "ballots": [["B", "A"]]}


def scenario(profile: dict, **winners: str) -> dict:
    return {**profile, "winners": winners}


class Parity(unittest.TestCase):
    def test_reports_each_rule_whose_winner_moved(self):
        old = {"scenarios": [scenario(PROFILE_1, borda="A", irv="B"), scenario(PROFILE_2, borda="B", irv="B")]}
        new = {"scenarios": [scenario(PROFILE_2, borda="B", irv="A"), scenario(PROFILE_1, borda="C", irv="A")]}
        lines = odr.parity_diff(old, new)
        self.assertEqual(lines[0], "- **scenarios**: 2 scenarios (3 winners changed)")
        self.assertIn('  - `irv`: 2 scenarios changed winner, e.g. "B" → "A"', lines)
        self.assertIn('  - `borda`: 1 scenario changed winner, e.g. "A" → "C"', lines)

    def test_reordering_alone_is_not_a_change(self):
        a = scenario(PROFILE_1, borda="A")
        b = scenario(PROFILE_2, borda="B")
        self.assertEqual(odr.parity_diff({"scenarios": [a, b]}, {"scenarios": [b, a]}),
                         ["- **scenarios**: 2 scenarios (reordered only)"])

    def test_dropped_rule_is_called_out(self):
        old = {"scenarios": [scenario(PROFILE_1, borda="A", irv="B")]}
        new = {"scenarios": [scenario(PROFILE_1, borda="A")]}
        self.assertIn("  - `irv`: **no longer checked** on 1 scenarios", odr.parity_diff(old, new))

    def test_regenerated_inputs_and_new_or_removed_lists(self):
        old = {"scenarios": [scenario(PROFILE_1, borda="A")], "gone": [scenario(PROFILE_2, borda="B")]}
        new = {"scenarios": [scenario(PROFILE_2, borda="B")], "fresh": [scenario(PROFILE_1, borda="A")]}
        lines = odr.parity_diff(old, new)
        self.assertIn("- **fresh**: new, 1 scenarios", lines)
        self.assertIn("- **gone**: **removed** (1 scenarios no longer checked)", lines)
        self.assertTrue(any("every input profile was regenerated" in line for line in lines))


class OtherOracles(unittest.TestCase):
    def test_openapi_endpoints_and_schemas(self):
        old = {"paths": {"/a": {"get": {"x": 1}}, "/b": {"post": {}}}, "components": {"schemas": {"S": {"t": 1}}}}
        new = {"paths": {"/a": {"get": {"x": 2}}, "/c": {"get": {}}}, "components": {"schemas": {"S": {"t": 1}, "T": {}}}}
        self.assertEqual(odr.openapi_diff(old, new), [
            "- endpoint added: `GET /c`",
            "- endpoint **removed**: `POST /b`",
            "- endpoint changed: `GET /a`",
            "- schema added: `T`",
        ])

    def test_leaf_diff_marks_direction_and_shortens_hashes(self):
        old = {"sonarjs": 265, "events": {"sha256": "a" * 64}, "old": 1}
        new = {"sonarjs": 264, "events": {"sha256": "b" * 64}, "new": True}
        self.assertEqual(odr.json_leaf_diff(old, new), [
            "- `events.sha256`: " + "a" * 12 + " → " + "b" * 12,
            "- `new` added: true",
            "- `old` removed (was 1)",
            "- `sonarjs`: 265 → 264 ▼",
        ])

    def test_emptied_container_is_a_change(self):
        self.assertEqual(odr.json_leaf_diff({"by_event_type": {"x": 1}}, {"by_event_type": {}}),
                         ["- `by_event_type` added: {}", "- `by_event_type.x` removed (was 1)"])

    def test_long_reports_are_capped(self):
        lines = odr.json_leaf_diff({}, {f"k{i:02}": i for i in range(40)})
        self.assertEqual(len(lines), odr.MAX_LINES + 1)
        self.assertEqual(lines[-1], "- … and 15 more")


class Report(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(cti, "ROOT", self.root)
        self.patch.start()
        self.git("init", "-q", "-b", "main")
        self.write(odr.PARITY, {"scenarios": [scenario(PROFILE_1, borda="A")]})
        self.write(".github/quality-baseline.json", {"sonarjs": 265})
        self.write("src/rules.ts", "export const x = 1;\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "pr")

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       cwd=self.root, check=True, capture_output=True)

    def write(self, path: str, value: object) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(value if isinstance(value, str) else json.dumps(value, indent=2))

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def test_silent_when_no_oracle_changed(self):
        self.write("src/rules.ts", "export const x = 2;\n")
        self.commit("code only")
        self.assertEqual(odr.report("main", "pr"), "")

    def test_compares_against_the_merge_base(self):
        self.write(odr.PARITY, {"scenarios": [scenario(PROFILE_1, borda="B")]})
        self.write(".github/quality-baseline.json", {"sonarjs": 264})
        self.write("visual.spec.ts-snapshots/home.png", "png")
        self.commit("regenerate")
        # A later base commit must not show up as the PR's change.
        self.git("checkout", "-q", "main")
        self.write(".github/quality-baseline.json", {"sonarjs": 200})
        self.commit("base moves on")
        text = odr.report("main", "pr")
        self.assertIn('  - `borda`: 1 scenario changed winner, e.g. "A" → "B"', text)
        self.assertIn("- `sonarjs`: 265 → 264 ▼", text)
        self.assertIn("- added: `visual.spec.ts-snapshots/home.png`", text)

    def test_generated_client_edited_without_its_contract(self):
        self.write("voter-app/src/api/types.gen.ts", "a\n")
        self.commit("client")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "pr")
        self.git("checkout", "-q", "pr")
        self.write("voter-app/src/api/types.gen.ts", "a\nb\n")
        self.commit("hand edit")
        self.assertIn("changed without openapi.gen.json changing", odr.report("main", "pr"))

    def test_cli_writes_summary_and_fails_cleanly_on_git_error(self):
        self.write(".github/quality-baseline.json", {"sonarjs": 264})
        self.commit("ratchet")
        summary = self.root / "summary.md"
        with mock.patch("sys.stdout"):
            self.assertEqual(odr.main(["--base", "main", "--head", "pr", "--summary", str(summary)]), 0)
        self.assertIn("## Test oracle changes", summary.read_text())
        with mock.patch("sys.stderr"):
            self.assertEqual(odr.main(["--base", "main", "--head", "no-such-ref"]), 2)


if __name__ == "__main__":
    unittest.main()
