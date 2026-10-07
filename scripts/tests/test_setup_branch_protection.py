"""Tests for the review-gate App pin in setup-branch-protection.sh (stdlib unittest).

Phase 3b: with REVIEW_GATE_APP_ID set, the gate must be required from that App
only, and the script must refuse to pin before the App actually posts the gate.

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "setup-branch-protection.sh"
GATE = "High-risk review gate"


def _checks(branch: str, app_id: str | None) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "REVIEW_GATE_APP_ID"}
    if app_id is not None:
        env["REVIEW_GATE_APP_ID"] = app_id
    out = subprocess.run(
        ["bash", str(SCRIPT), "--print-checks", branch],
        capture_output=True, text=True, check=True, env=env,
    ).stdout
    return json.loads("{" + out.strip() + "}")


class PrintChecks(unittest.TestCase):
    def test_without_the_app_the_plain_contexts_list_is_applied(self) -> None:
        self.assertIn(GATE, _checks("polity", None)["contexts"])

    def test_the_gate_alone_is_pinned_to_the_app(self) -> None:
        for branch in ("polity", "develop"):
            checks = _checks(branch, "424242")["checks"]
            pinned = {c["context"]: c["app_id"] for c in checks if c["app_id"] != -1}
            self.assertEqual(pinned, {GATE: 424242}, branch)
            contexts = json.loads(subprocess.run(
                ["bash", str(SCRIPT), "--print-contexts", branch],
                capture_output=True, text=True, check=True,
            ).stdout)
            self.assertEqual([c["context"] for c in checks], contexts, branch)

    def test_main_has_no_gate_so_nothing_is_pinned(self) -> None:
        self.assertNotIn(GATE, _checks("main", "424242")["contexts"])

    def test_whitespace_is_trimmed_and_a_non_number_refused(self) -> None:
        self.assertEqual(len([c for c in _checks("polity", " 424242\n")["checks"] if c["app_id"] == 424242]), 1)
        bad = subprocess.run(
            ["bash", str(SCRIPT), "--print-checks", "polity"],
            capture_output=True, text=True, env={**os.environ, "REVIEW_GATE_APP_ID": "x1"},
        )
        self.assertEqual(bad.returncode, 1)


STUB_GH = """#!/usr/bin/env bash
ep="$2"; jqf="$4"
case "$ep" in
  repos/*/pulls*) data='[{"base":{"ref":"main"},"head":{"sha":"m1"}},{"base":{"ref":"polity"},"head":{"sha":"p1"}}]';;
  repos/*/commits/p1/statuses) data="$STUB_STATUSES";;
  apps/vote-app-review-gate) data='{"id":424242}';;
  apps/github-actions) data='{"id":15368}';;
  apps/*) exit 1;;
  *) data='[]';;
esac
jq -r "$jqf" <<< "$data"
"""


class GatePostedByApp(unittest.TestCase):
    """require_gate_posted_by_app, run alone against a stub gh."""

    def _run(self, statuses: list[dict]) -> subprocess.CompletedProcess[str]:
        text = SCRIPT.read_text(encoding="utf-8")
        fn = re.search(r"^require_gate_posted_by_app\(\) \{.*?^\}", text, re.S | re.M)
        assert fn, "require_gate_posted_by_app not found"
        with tempfile.TemporaryDirectory() as tmp:
            gh = Path(tmp) / "gh"
            gh.write_text(STUB_GH)
            gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
            harness = Path(tmp) / "harness.sh"
            harness.write_text(
                f'OWNER=o; REPO=r; REVIEW_GATE="{GATE}"; REVIEW_GATE_APP_ID=424242\n'
                f"{fn.group(0)}\nrequire_gate_posted_by_app\n"
            )
            return subprocess.run(
                ["bash", str(harness)], capture_output=True, text=True,
                env={**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}",
                     "STUB_STATUSES": json.dumps(statuses)},
            )

    def test_a_gate_posted_by_actions_refuses_the_pin(self) -> None:
        r = self._run([{"context": GATE, "creator": {"login": "github-actions[bot]"}}])
        self.assertEqual(r.returncode, 1)
        self.assertIn("app id: 15368", r.stdout)

    def test_a_gate_posted_by_the_app_allows_it(self) -> None:
        r = self._run([{"context": GATE, "creator": {"login": "vote-app-review-gate[bot]"}}])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_no_gate_anywhere_refuses_the_pin(self) -> None:
        self.assertEqual(self._run([]).returncode, 1)


if __name__ == "__main__":
    unittest.main()
