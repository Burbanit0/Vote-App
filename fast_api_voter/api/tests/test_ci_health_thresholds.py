"""The CI health watchdog's staleness limit must outlast its own refresh interval.

scripts/check_ci_health.py --update only refreshes a healthy snapshot once it is
HEARTBEAT_MAX_DAYS old, but --verify used to fail any snapshot older than 36h.
The two disagreed, so on a quiet repo "CI health check" went red on develop and
on every PR for days 2-7 of each week, with nothing wrong (2026-09-21 onward: a
145h-old snapshot blocked everything). Nothing tied the constants together, or
the refresh decision to the limit; this does, through the script's own entry
point and its --verify fixture mode.
"""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_ci_health.py"
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def _iso(age_hours):
    return (NOW - timedelta(hours=age_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(scope="module")
def watchdog():
    """The script, loaded by path. It lives at the repo root, so a bare backend
    checkout lacks it: that skips locally, but never in GitHub Actions, where a
    moved or renamed script must fail loudly rather than turn the guard into
    three quiet skips."""
    if not SCRIPT.exists():
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail(f"{SCRIPT} is missing: was check_ci_health.py moved or renamed?")
        pytest.skip(f"{SCRIPT} is not there: the backend was checked out without scripts/")
    spec = importlib.util.spec_from_file_location("check_ci_health", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # exec_module needs it for e.g. @dataclass
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture
def verify(watchdog, monkeypatch, tmp_path):
    """`verify(age_hours)` -> the exit status of `check_ci_health.py --verify
    --snapshot ...` on an otherwise healthy snapshot that many hours old, run
    through main() as the workflow runs it."""
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)

    def run(age_hours):
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(json.dumps({
            "generated_at": _iso(age_hours),
            "workflows": {},
            "branch_protection": {"status": "healthy"},
        }))
        monkeypatch.setattr(sys, "argv", [
            "check_ci_health.py", "--verify", "--snapshot", str(snapshot),
            "--snoozes", str(tmp_path / "no-snoozes.json"),
        ])
        return watchdog.main()

    return run


def test_a_healthy_snapshot_never_trips_the_check_between_heartbeats(watchdog, verify):
    """Every age a healthy repo's snapshot can reach: right after a refresh,
    the 145h that blocked every PR, a heartbeat interval, and the worst case --
    the heartbeat comes due, then waits for the next daily audit to notice."""
    for age in (1, 36, 37, 145, watchdog.HEARTBEAT_MAX_DAYS * 24, _worst_healthy(watchdog)):
        assert verify(age) == 0, f"a healthy {age}h-old snapshot failed --verify"


def _worst_healthy(watchdog):
    """The age at which a healthy snapshot's refresh PR is opened: the
    heartbeat is due after HEARTBEAT_MAX_DAYS, and the daily audit that notices
    can run up to a day later."""
    return watchdog.HEARTBEAT_MAX_DAYS * 24 + watchdog.AUDIT_EXPECTED_HOURS


def test_the_refresh_pr_gets_its_full_allowance_before_the_check_fails(watchdog):
    """After the worst-case refresh trigger the PR still has a day and a half
    to merge -- not the ~12h that leaving the daily wait out of the limit gave.
    A literal 1.5, not INERT_MULTIPLIER: the margin is derived from that, so
    asserting against it could never fail."""
    assert watchdog.AUDIT_STALE_HOURS - _worst_healthy(watchdog) >= 1.5 * watchdog.AUDIT_EXPECTED_HOURS


def _update_output(watchdog, monkeypatch, tmp_path, age_hours):
    """What `--update` decides (`pr_needed=...`, as the workflow reads it from
    $GITHUB_OUTPUT) for a snapshot that many hours old and otherwise unchanged,
    with GitHub itself stubbed out."""
    healthy = {"status": "healthy", "detail": "", "display_name": "stub"}
    snapshot = tmp_path / "ci-health.json"
    snapshot.write_text(json.dumps({
        "generated_at": _iso(age_hours),
        "workflows": {wf: dict(healthy) for wf in watchdog.WATCHED_WORKFLOWS},
        "branch_protection": {"status": "healthy", "detail": ""},
    }))
    output = tmp_path / "github_output"
    output.unlink(missing_ok=True)  # cmd_update appends; one decision per call
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)
    monkeypatch.setattr(watchdog, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(watchdog, "SNAPSHOT_PATH", snapshot)
    monkeypatch.setattr(watchdog, "query_workflow_health", lambda wf: dict(healthy))
    monkeypatch.setattr(watchdog, "check_branch_protection_drift",
                        lambda: {"status": "healthy", "detail": ""})
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert watchdog.cmd_update(argparse.Namespace()) == 0
    return output.read_text().strip()


def test_the_refresh_pr_is_opened_at_the_heartbeat_and_not_before(watchdog, monkeypatch, tmp_path):
    """The other half of the disagreement: --update decides when a healthy
    snapshot is refreshed, and --verify's limit is only right relative to it.
    Driven through cmd_update, so the heartbeat cannot be unwired from it."""
    interval = watchdog.HEARTBEAT_MAX_DAYS * 24
    assert _update_output(watchdog, monkeypatch, tmp_path, interval - 1) == "pr_needed=false"
    assert _update_output(watchdog, monkeypatch, tmp_path, interval + 1) == "pr_needed=true"


def test_the_audit_cadence_the_limit_assumes_is_the_workflows_real_one(watchdog):
    """AUDIT_EXPECTED_HOURS is a hand-copied literal. If ci-health.yml's cron
    went weekly the limit would silently be a week too short."""
    assert watchdog.derive_expected_hours("ci-health.yml") == watchdog.AUDIT_EXPECTED_HOURS


def test_a_dead_audit_is_still_caught(watchdog, verify):
    """The check still exists to make a silent watcher loud: within an hour of
    the limit it flips, and a snapshot that has missed its refresh entirely fails."""
    assert verify(watchdog.AUDIT_STALE_HOURS - 1) == 0
    assert verify(watchdog.AUDIT_STALE_HOURS + 1) == 1
    assert verify(2 * watchdog.HEARTBEAT_MAX_DAYS * 24) == 1
