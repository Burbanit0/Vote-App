"""Tests for the code-scanning issue sync (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import code_scanning_issues as csi  # noqa: E402


def alert(number: int, tool: str = "Trivy", category: str = "trivy-image", path: str = "library/votelab",
          rule_id: str = "CVE-1", sev: str = "high", desc: str = "pkg: bad") -> dict:
    return {"number": number, "html_url": f"https://x/{number}", "tool": {"name": tool},
            "rule": {"id": rule_id, "description": desc, "security_severity_level": sev},
            "most_recent_instance": {"category": category, "location": {"path": path}}}


class Grouping(unittest.TestCase):
    def test_trivy_groups_by_scanned_file_not_by_cve(self):
        groups = csi.group_alerts([alert(1, rule_id="CVE-1"), alert(2, rule_id="CVE-2"),
                                   alert(3, category="trivy", path="fast_api_voter/requirements.lock.txt")])
        self.assertEqual(sorted(groups), ["trivy · fast_api_voter/requirements.lock.txt",
                                          "trivy-image · library/votelab"])
        self.assertEqual(len(groups["trivy-image · library/votelab"]), 2)

    def test_other_tools_group_by_rule(self):
        a = alert(1, tool="CodeQL", category="/language:python", rule_id="py/sql-injection", path="a.py")
        b = alert(2, tool="CodeQL", category="/language:python", rule_id="py/sql-injection", path="b.py")
        c = alert(3, tool="CodeQL", category="/language:python", rule_id="py/path-injection", path="a.py")
        self.assertEqual(sorted(csi.group_alerts([a, b, c])),
                         ["CodeQL · py/path-injection", "CodeQL · py/sql-injection"])

    def test_alert_without_instance_does_not_crash(self):
        self.assertEqual(csi.group_key({"number": 1, "tool": {"name": "X"}, "rule": {"id": "r"}}), "X · r")


class Rendering(unittest.TestCase):
    def test_most_severe_first_and_marker_round_trips(self):
        body = csi.render("k · p", [alert(1, sev="low"), alert(2, sev="critical"), alert(3, sev="high")])
        self.assertEqual(csi.marker_of(body), "k · p")
        self.assertLess(body.index("#2"), body.index("#3"))
        self.assertLess(body.index("#3"), body.index("#1"))
        self.assertIn("1 critical, 1 high, 1 low", body)

    def test_long_list_is_capped(self):
        body = csi.render("k", [alert(n) for n in range(csi.MAX_LINES + 20)])
        self.assertIn("and 20 more", body)
        self.assertLess(len(body), 65536)

    def test_marker_only_read_from_its_own_line(self):
        self.assertIsNone(csi.marker_of("see <!-- code-scanning-group: x --> inline"))
        self.assertIsNone(csi.marker_of(None))


class Plan(unittest.TestCase):
    def issue(self, key: str, alerts: list[dict], state: str = "open", number: int = 5) -> dict:
        return {"number": number, "state": state, "body": csi.render(key, alerts), "html_url": "https://x/i"}

    def test_new_group_is_created(self):
        groups = csi.group_alerts([alert(1)])
        self.assertEqual([a[0] for a in csi.plan(groups, [])], ["create"])

    def test_unchanged_group_is_left_alone(self):
        alerts = [alert(1)]
        issue = self.issue("trivy-image · library/votelab", alerts)
        self.assertEqual(csi.plan(csi.group_alerts(alerts), [issue]), [])

    def test_changed_group_is_updated(self):
        issue = self.issue("trivy-image · library/votelab", [alert(1)])
        actions = csi.plan(csi.group_alerts([alert(1), alert(2)]), [issue])
        self.assertEqual([a[0] for a in actions], ["update"])

    def test_emptied_group_closes_its_issue(self):
        issue = self.issue("trivy-image · library/votelab", [alert(1)])
        self.assertEqual([a[0] for a in csi.plan({}, [issue])], ["close"])

    def test_closed_issue_of_an_emptied_group_is_not_closed_again(self):
        issue = self.issue("trivy-image · library/votelab", [alert(1)], state="closed")
        self.assertEqual(csi.plan({}, [issue]), [])

    def test_returning_group_reopens_its_closed_issue(self):
        issue = self.issue("trivy-image · library/votelab", [alert(1)], state="closed")
        self.assertEqual([a[0] for a in csi.plan(csi.group_alerts([alert(1)]), [issue])], ["reopen"])

    def test_issue_without_marker_is_ignored(self):
        self.assertEqual(csi.plan({}, [{"number": 1, "state": "open", "body": "hand-written"}]), [])


if __name__ == "__main__":
    unittest.main()
