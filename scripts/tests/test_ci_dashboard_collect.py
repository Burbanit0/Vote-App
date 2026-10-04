"""Tests for the CI dashboard collector (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci_dashboard"))

import collect

NOW = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)


def run(id_, workflow="Backend CI", branch="polity", event="push", sha="a" * 40,
        conclusion="success", created="2026-10-04T10:00:00Z", attempt=1):
    return {"id": id_, "run_attempt": attempt, "name": workflow, "path": ".github/workflows/x.yml@polity",
            "head_branch": branch, "event": event, "head_sha": sha, "pull_requests": [],
            "conclusion": conclusion, "created_at": created, "run_started_at": created,
            "updated_at": created.replace("10:00:00", "10:05:00"), "html_url": f"https://x/{id_}"}


class Classify(unittest.TestCase):
    def test_categories(self):
        cases = {
            "code": ["FAILED api/tests/test_x.py::test_y - AssertionError: 1 != 2"],
            "advisory": ["npm audit report", "braces  <=3.0.3  GHSA-vfj7-8cjw-p6xm"],
            "infra": ["##[error]The runner has received a shutdown signal."],
            "timeout": ["##[error]The job running on runner X has exceeded the maximum execution time of 25 minutes."],
        }
        for want, lines in cases.items():
            with self.subTest(want=want):
                self.assertEqual(collect.categorize(lines), want)

    def test_error_lines_pick_errors_and_strip_timestamps(self):
        log = ("2026-10-04T10:00:00.1Z setup ok\n"
               "2026-10-04T10:00:01.2Z FAILED api/tests/test_a.py::test_b\n"
               "2026-10-04T10:00:02.3Z ##[error]Process completed with exit code 1.\n")
        self.assertEqual(collect.error_lines(log),
                         ["FAILED api/tests/test_a.py::test_b", "##[error]Process completed with exit code 1."])

    def test_error_lines_fall_back_to_the_tail(self):
        self.assertEqual(collect.error_lines("one\n\ntwo\n"), ["one", "two"])

    def test_signature_groups_the_same_error_across_runs(self):
        a = collect.signature("code", ["FAILED test_x.py::t - took 1.25s at line 40 in /tmp/abc"])
        b = collect.signature("code", ["FAILED test_x.py::t - took 3.5s at line 41 in /tmp/xyz"])
        self.assertEqual(a, b)
        self.assertNotEqual(a, collect.signature("code", ["FAILED test_y.py::t"]))


class History(unittest.TestCase):
    def test_merge_dedupes_keeps_reruns_and_trims_the_window(self):
        old = collect.record(run(1, created="2026-08-01T10:00:00Z"))
        kept = collect.record(run(2))
        fresh = [collect.record(run(2)), collect.record(run(2, attempt=2)), collect.record(run(3))]
        got = collect.merge([old, kept], fresh, NOW - timedelta(days=30))
        self.assertEqual([(r["id"], r["attempt"]) for r in got], [(2, 1), (2, 2), (3, 1)])

    def test_flaky_is_a_code_failure_that_later_passed_on_the_same_commit(self):
        fail = collect.record(run(1, conclusion="failure"))
        fail["failure"] = {"category": "code", "signature": "code: FAILED t", "job": "j", "step": "s", "lines": []}
        advisory = collect.record(run(2, workflow="Frontend CI", conclusion="failure"))
        advisory["failure"] = {"category": "advisory", "signature": "advisory: x", "job": "j", "step": "s",
                               "lines": []}
        records = [fail, advisory, collect.record(run(3)), collect.record(run(4, workflow="Frontend CI"))]
        collect.mark_flaky(records)
        self.assertEqual(fail["failure"]["category"], "test-flaky")
        self.assertEqual(fail["failure"]["signature"], "test-flaky: FAILED t")
        self.assertEqual(advisory["failure"]["category"], "advisory")  # a pass after an advisory is not a flake


class Summary(unittest.TestCase):
    def test_tips_grid_groups_and_speed(self):
        f = collect.record(run(2, workflow="Frontend CI", conclusion="failure", sha="b" * 40,
                               created="2026-10-04T11:00:00Z"))
        f["failure"] = {"category": "advisory", "signature": "advisory: braces", "job": "audit",
                        "step": "npm audit", "lines": ["GHSA-x"]}
        records = [collect.record(run(1, created="2026-10-03T10:00:00Z")),
                   collect.record(run(5, workflow="E2E Tests", created="2026-10-03T10:00:00Z")),
                   collect.record(run(3, sha="b" * 40, created="2026-10-04T11:00:00Z")),
                   f,
                   collect.record(run(4, event="pull_request", branch="feat/x"))]
        s = collect.summarize(records, {}, NOW)
        self.assertEqual(s["tips"]["polity"]["sha"], "b" * 40)
        self.assertEqual(s["tips"]["polity"]["workflows"]["Frontend CI"]["conclusion"], "failure")
        self.assertEqual(s["tips"]["polity"]["workflows"]["Backend CI"]["sha"], "b" * 40)
        self.assertEqual(s["tips"]["polity"]["workflows"]["E2E Tests"]["sha"], "a" * 40)  # older commit, still shown
        self.assertNotIn("feat/x", s["tips"])
        self.assertEqual(s["grid"]["Backend CI"], {"2026-10-03": {"success": 1}, "2026-10-04": {"success": 1}})
        self.assertEqual(s["failures_by_category"], {"advisory": 1})
        self.assertEqual(s["failure_groups"][0]["count"], 1)
        self.assertEqual(s["failure_groups"][0]["example"]["step"], "npm audit")
        self.assertEqual(s["speed"]["Backend CI"]["p50_s"], 300)
        self.assertEqual(s["latest_runs"]["Frontend CI"]["conclusion"], "failure")
        self.assertEqual(s["latest_runs"]["Backend CI"]["created_at"], "2026-10-04T11:00:00Z")


class Fetch(unittest.TestCase):
    def test_one_query_per_day_and_every_page(self):
        calls = []

        def fake_json(path):
            calls.append(path)
            page = int(path.split("&page=")[1].split("&")[0])
            n = 100 if "2026-10-03" in path and page == 1 else 3
            return {"workflow_runs": [run(page * 1000 + i) for i in range(n)]}

        with mock.patch.object(collect, "gh_json", side_effect=fake_json):
            got = collect.fetch_runs("o/r", NOW - timedelta(days=1), NOW)
        self.assertEqual([c.split("created=")[1] + "/" + c.split("&page=")[1].split("&")[0] for c in calls],
                         ["2026-10-03/1", "2026-10-03/2", "2026-10-04/1"])
        self.assertEqual(len(got), 106)

    def test_github_dynamic_runs_are_left_out(self):
        dyn = {**run(1), "event": "dynamic", "name": "Configured Graph Update #123"}
        with mock.patch.object(collect, "gh_json", return_value={"workflow_runs": [dyn, run(2)]}):
            got = collect.fetch_runs("o/r", NOW, NOW)
        self.assertEqual([r["id"] for r in got], [2])

    def test_an_unreadable_log_is_unknown_not_code(self):
        jobs = {"jobs": [{"id": 9, "name": "Tests", "conclusion": "failure",
                          "steps": [{"name": "pytest", "conclusion": "failure"}]}]}
        with mock.patch.object(collect, "gh_json", return_value=jobs), \
                mock.patch.object(collect, "gh_text", return_value=None):
            got = collect.failure_detail("o/r", collect.record(run(1, conclusion="failure")))
        self.assertEqual((got["category"], got["signature"]),
                         ("unknown", "unknown: Tests / pytest (log unavailable)"))


class Reruns(unittest.TestCase):
    def test_queue_time_only_on_the_first_attempt(self):
        r = run(1, attempt=2)
        r["created_at"] = "2026-10-04T06:00:00Z"  # re-run four hours after the first attempt
        self.assertIsNone(collect.record(r)["queue_s"])
        self.assertEqual(collect.record(run(1))["queue_s"], 0)

    def test_earlier_attempts_of_a_rerun_are_fetched_once(self):
        latest = collect.record(run(7, attempt=3))
        calls = []

        def fake_json(path):
            calls.append(path)
            n = int(path.rsplit("/", 1)[1])
            return run(7, attempt=n, conclusion="failure")

        with mock.patch.object(collect, "gh_json", side_effect=fake_json):
            got = collect.earlier_attempts("o/r", [latest], seen={(7, 1)})
        self.assertEqual(calls, ["repos/o/r/actions/runs/7/attempts/2"])
        self.assertEqual([(r["attempt"], r["conclusion"]) for r in got], [(2, "failure")])

    def test_a_failure_rerun_to_green_counts_as_flaky(self):
        fail = collect.record(run(7, attempt=1, conclusion="failure"))
        fail["failure"] = {"category": "code", "signature": "code: FAILED t", "job": "j", "step": "s", "lines": []}
        collect.mark_flaky([fail, collect.record(run(7, attempt=2))])
        self.assertEqual(fail["failure"]["category"], "test-flaky")


class Main(unittest.TestCase):
    def test_collects_appends_and_survives_an_unreadable_log(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT10:00:00Z")  # main() uses the real clock
        runs = [run(1, created=today), run(2, conclusion="failure", created=today)]

        def fake_json(path):
            if "/actions/runs?" in path:
                return {"workflow_runs": runs}
            raise RuntimeError("403")

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(collect, "gh_json", side_effect=fake_json):
            data = Path(d)
            self.assertEqual(collect.main(["--data", d]), 0)
            self.assertEqual(collect.main(["--data", d]), 0)  # second pass appends nothing new
            lines = (data / "runs.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 2)
            failed = json.loads(lines[1])
            self.assertEqual(failed["failure"]["signature"], "unknown: run details unavailable")
            # Past the cap, failures stay unread and are picked up by the next collection.
            many = [run(10 + i, conclusion="failure", created=today) for i in range(collect.MAX_LOG_FETCHES + 2)]
            runs[:] = many
            collect.main(["--data", d])
            unread = [json.loads(ln) for ln in (data / "runs.jsonl").read_text().splitlines()]
            self.assertEqual(sum("failure" not in r for r in unread if r["conclusion"] == "failure"), 2)
            collect.main(["--data", d])
            done = [json.loads(ln) for ln in (data / "runs.jsonl").read_text().splitlines()]
            self.assertTrue(all("failure" in r for r in done if r["conclusion"] == "failure"))
            summary = json.loads((data / "summary.json").read_text())
            self.assertEqual(summary["runs"], 2 + collect.MAX_LOG_FETCHES + 2)
            self.assertEqual(summary["window_days"], 30)


if __name__ == "__main__":
    unittest.main()
