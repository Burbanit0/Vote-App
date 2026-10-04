"""Tests for the CI weekly report (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci_dashboard"))

import weekly_report as wr

NOW = datetime(2026, 10, 12, 7, tzinfo=timezone.utc)


def rec(id_, day, conclusion="success", workflow="Backend CI", sig=None, cat="code"):
    r = {"id": id_, "workflow": workflow, "conclusion": conclusion, "created_at": f"2026-10-{day:02d}T10:00:00Z",
         "url": f"https://x/{id_}"}
    if sig:
        r["failure"] = {"category": cat, "signature": f"{cat}: {sig}"}
    return r


class Report(unittest.TestCase):
    def setUp(self):
        self.records = [
            {**rec(1, 1, "failure", sig="old error"), "created_at": "2026-09-20T10:00:00Z"},  # older: not counted
            rec(2, 3, "failure", sig="old error"),                      # week before
            rec(3, 3, "failure", "Frontend CI", "GHSA-x", "advisory"),  # week before
            rec(4, 6),
            rec(5, 8, "failure", sig="old error"),
            rec(6, 9, "failure", sig="old error"),
            rec(7, 10, "failure", "E2E Tests", "spec t", "test-flaky"),
            rec(8, 11),
        ]
        self.summary = {
            "speed": {"E2E Tests": {"p50_s": 600, "p95_s": 900}, "Backend CI": {"p50_s": 300, "p95_s": 400}},
            "latest_runs": {"Mutation Testing": {"conclusion": "success", "created_at": "2026-09-30T02:00:00Z",
                                                 "url": "https://x/m"},
                            "Backend CI": {"conclusion": "success", "created_at": "2026-10-11T10:00:00Z",
                                           "url": "https://x/8"}},
            "baselines": {"mutation": {"score": 66.02}, "quality": {"knip": 53}},
        }
        self.md = wr.report(self.records, self.summary, NOW, "https://dash")

    def test_counts_and_trend_against_the_week_before(self):
        self.assertIn("5 runs, 3 failed (2 runs, 2 failed the week before).", self.md)
        self.assertIn("| code | 2 | 1 | ▲ |", self.md)
        self.assertIn("| advisory | 0 | 1 | ▼ |", self.md)
        self.assertIn("| test-flaky | 1 | 0 | ▲ |", self.md)

    def test_groups_new_and_flaky(self):
        self.assertIn("- **2×** `code: old error` (Backend CI, [latest](https://x/6))\n", self.md)
        self.assertIn("`test-flaky: spec t` (E2E Tests, [latest](https://x/7)) **new**", self.md)
        self.assertIn("## New flaky tests\n\n- `test-flaky: spec t`", self.md)

    def test_speed_staleness_and_baselines(self):
        self.assertLess(self.md.index("E2E Tests: p50 10m"), self.md.index("Backend CI: p50 5m"))
        self.assertIn("- Mutation Testing: last success on 2026-09-30", self.md)
        self.assertNotIn("- Backend CI: last", self.md)
        self.assertIn("- mutation score: 66.02%", self.md)
        self.assertIn("- knip: 53", self.md)
        self.assertIn("Dashboard: https://dash", self.md)

    def test_a_scheduled_workflow_gone_past_the_window_is_still_listed(self):
        md = wr.report(self.records, self.summary, NOW, None, ["Mutation Testing", "DAST — ZAP Baseline"])
        self.assertIn("- DAST — ZAP Baseline: **no run in the last 30 days**", md)
        self.assertIn("- Mutation Testing: last success on 2026-09-30", md)
        self.assertNotIn("Mutation Testing: **no run", md)

    def test_scheduled_workflows_are_read_from_the_workflow_files(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.yml").write_text('name: "Deep A"\non:\n  schedule:\n    - cron: "0 3 * * 1"\n')
            Path(d, "b.yml").write_text("name: Push only\non:\n  push:\n")
            self.assertEqual(wr.scheduled_workflows(Path(d)), ["Deep A"])
        real = wr.scheduled_workflows(wr.WORKFLOWS)
        self.assertIn("Mutation Testing", real)
        self.assertNotIn("Backend CI", real)

    def test_a_failure_with_an_unread_log_is_counted(self):
        md = wr.report([rec(9, 11, "failure")], {}, NOW, None)
        self.assertIn("1 runs, 1 failed", md)
        self.assertIn("| not yet read | 1 | 0 | ▲ |", md)

    def test_an_empty_week_still_renders(self):
        md = wr.report([], {}, NOW, None)
        self.assertIn("0 runs, 0 failed", md)
        self.assertIn("| none | 0 | 0 | → |", md)
        self.assertNotIn("Dashboard:", md)


if __name__ == "__main__":
    unittest.main()
