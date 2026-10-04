"""Tests for the polity red-branch alert (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import branch_red_alert as bra  # noqa: E402


def run(event: str, branch: str, conclusion: str | None, name: str = "Backend CI", sha: str = "abcdef123") -> dict:
    return {"event": event, "head_branch": branch, "conclusion": conclusion, "name": name,
            "head_sha": sha, "html_url": f"https://x/{sha}"}


class LatestVerdict(unittest.TestCase):
    def test_newest_polity_push_wins(self):
        runs = [run("pull_request", "fix/x", "failure"), run("push", "develop", "failure"),
                run("push", "polity", "success"), run("push", "polity", "failure")]
        self.assertEqual(bra.latest_verdict(runs, deep=False)["conclusion"], "success")

    def test_cancelled_and_skipped_runs_are_passed_over(self):
        runs = [run("push", "polity", "cancelled"), run("push", "polity", "skipped"),
                run("push", "polity", "failure")]
        self.assertEqual(bra.latest_verdict(runs, deep=False)["conclusion"], "failure")

    def test_schedule_counts_only_for_deep_tests(self):
        runs = [run("schedule", "develop", "failure"), run("push", "polity", "success")]
        self.assertEqual(bra.latest_verdict(runs, deep=False)["conclusion"], "success")
        self.assertEqual(bra.latest_verdict(runs, deep=True)["conclusion"], "failure")

    def test_dispatch_on_polity_counts(self):
        runs = [run("workflow_dispatch", "polity", "timed_out"), run("workflow_dispatch", "develop", "success")]
        self.assertEqual(bra.latest_verdict(runs, deep=True)["conclusion"], "timed_out")

    def test_nothing_relevant(self):
        self.assertIsNone(bra.latest_verdict([run("pull_request", "polity", "failure")], deep=True))


class Render(unittest.TestCase):
    def test_one_sorted_line_per_red_workflow(self):
        body = bra.render([run("push", "polity", "failure", "E2E Tests", "1234567890"),
                           run("schedule", "develop", "timed_out", "DAST", "fff")])
        self.assertTrue(body.startswith(bra.HEADER))
        self.assertEqual(body.splitlines()[-2:], [
            "- [ ] **DAST**: timed_out on scheduled run, [run](https://x/fff)",
            "- [ ] **E2E Tests**: failure on `1234567`, [run](https://x/1234567890)",
        ])

    def test_render_is_stable_so_an_unchanged_issue_is_not_rewritten(self):
        reds = [run("push", "polity", "failure", "B"), run("push", "polity", "failure", "A")]
        self.assertEqual(bra.render(reds), bra.render(list(reversed(reds))))


class WorkflowWiring(unittest.TestCase):
    """branch-red-alert.yml names workflows; the script keys them by file. Keep both in step."""

    def test_every_watched_file_is_listed_by_its_name(self):
        alert = (ROOT / ".github/workflows/branch-red-alert.yml").read_text()
        block = alert.split("    workflows:\n", 1)[1].split("    types:", 1)[0]
        listed = set(re.findall(r"^\s+- (.+)$", block, re.M))
        names = set()
        for wf in bra.WATCHED:
            text = (ROOT / ".github/workflows" / wf).read_text()
            names.add(re.search(r"^name:\s*(.+)$", text, re.M).group(1).strip())
        self.assertEqual(listed, names)

    def test_deep_tests_check_out_polity_on_schedule(self):
        for wf, deep in bra.WATCHED.items():
            text = (ROOT / ".github/workflows" / wf).read_text()
            if deep:
                self.assertIn("github.event_name == 'schedule' && 'polity'", text, wf)
                self.assertRegex(text, r"push:\n    branches: \[develop, polity\]", wf)


if __name__ == "__main__":
    unittest.main()
