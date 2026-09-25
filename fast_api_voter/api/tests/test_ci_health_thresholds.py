"""The CI health watchdog's staleness limit must outlast its own refresh interval.

scripts/check_ci_health.py --update only refreshes a healthy snapshot once it is
HEARTBEAT_MAX_DAYS old, but --verify used to fail any snapshot older than 36h.
The two disagreed, so on a quiet repo "CI health check" went red on develop and
on every PR for days 2-7 of each week, with nothing wrong (2026-09-21 onward: a
145h-old snapshot blocked everything). Nothing tied the two constants together;
this does, through the script's own --verify fixture mode.
"""
import argparse
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_ci_health.py"
NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def watchdog():
    if not SCRIPT.exists():
        pytest.skip(f"{SCRIPT} is not there: the backend was checked out without scripts/")
    spec = importlib.util.spec_from_file_location("check_ci_health", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def verify(watchdog, monkeypatch, tmp_path):
    """`verify(age_hours)` -> exit code of --verify on an otherwise healthy
    snapshot that many hours old."""
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)

    def run(age_hours):
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(json.dumps({
            "generated_at": (NOW - timedelta(hours=age_hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "workflows": {},
            "branch_protection": {"status": "healthy"},
        }))
        return watchdog.cmd_verify(argparse.Namespace(
            snapshot=str(snapshot), snoozes=str(tmp_path / "no-snoozes.json"),
        ))

    return run


def test_a_healthy_snapshot_never_trips_the_check_between_heartbeats(watchdog, verify):
    """Every age a healthy repo's snapshot can reach: right after a refresh,
    the 145h that blocked every PR, a heartbeat interval, and the worst case --
    the heartbeat comes due, then waits for the next daily audit to notice."""
    worst_healthy = watchdog.HEARTBEAT_MAX_DAYS * 24 + watchdog.AUDIT_EXPECTED_HOURS
    for age in (1, 36, 37, 145, watchdog.HEARTBEAT_MAX_DAYS * 24, worst_healthy):
        assert verify(age) == 0, f"a healthy {age}h-old snapshot failed --verify"


def test_the_refresh_is_due_before_the_check_would_fail(watchdog):
    assert watchdog.AUDIT_STALE_HOURS > watchdog.HEARTBEAT_MAX_DAYS * 24 + watchdog.AUDIT_EXPECTED_HOURS


def test_a_dead_audit_is_still_caught(watchdog, verify):
    """The check still exists to make a silent watcher loud: past the limit it
    fails, and it fails at exactly that limit."""
    assert verify(watchdog.AUDIT_STALE_HOURS - 1) == 0
    assert verify(watchdog.AUDIT_STALE_HOURS + 1) == 1
    assert verify(2 * watchdog.HEARTBEAT_MAX_DAYS * 24) == 1
