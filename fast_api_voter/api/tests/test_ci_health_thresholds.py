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
        **{key: {"status": "healthy", "detail": ""} for key in watchdog.PROTECTED_BRANCHES},
    }))
    output = tmp_path / "github_output"
    output.unlink(missing_ok=True)  # cmd_update appends; one decision per call
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)
    monkeypatch.setattr(watchdog, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(watchdog, "SNAPSHOT_PATH", snapshot)
    monkeypatch.setattr(watchdog, "query_workflow_health", lambda wf: dict(healthy))
    monkeypatch.setattr(watchdog, "check_branch_protection_drift",
                        lambda branch: {"status": "healthy", "detail": ""})
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


def test_the_review_gate_develop_requires_is_expected_not_drift(watchdog):
    """protect_develop() appends `High-risk review gate` to the shared context list
    (setup-branch-protection.sh); the drift check read REQUIRED_CONTEXTS alone, so
    the correctly applied protection would have reported as drifted and turned
    "CI health check" red on every PR to develop and main."""
    contexts, strict = watchdog.parse_setup_script_expectations()
    assert strict
    assert "High-risk review gate" in contexts
    assert contexts.count("High-risk review gate") == 1
    assert "CI health check" in contexts  # the shared list is still there


def test_each_branch_expects_what_the_setup_script_applies(watchdog):
    """Read through the script's own --print-contexts: polity requires the CI
    health check (ci-health.yml runs on PRs to it), polity-ui can't; polity and
    develop require Workflow lint."""
    develop, _ = watchdog.parse_setup_script_expectations("develop")
    polity, strict = watchdog.parse_setup_script_expectations("polity")
    polity_ui, _ = watchdog.parse_setup_script_expectations("polity-ui")
    assert strict
    assert sorted(polity) == sorted(develop)
    assert "CI health check" in polity and "High-risk review gate" in polity
    assert "CI health check" not in polity_ui
    # Workflow lint runs on PRs to polity and develop only (workflow-lint.yml).
    assert "Workflow lint" in polity and "Workflow lint" in develop
    assert "Workflow lint" not in polity_ui


def _verify_with(watchdog, monkeypatch, tmp_path, protections, snoozes=None):
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"generated_at": _iso(1), "workflows": {}, **protections}))
    snooze_file = tmp_path / "snoozes.json"
    snooze_file.write_text(json.dumps(snoozes or {}))
    monkeypatch.setattr(sys, "argv", [
        "check_ci_health.py", "--verify", "--snapshot", str(snapshot), "--snoozes", str(snooze_file),
    ])
    return watchdog.main()


def test_polity_drift_fails_the_check_and_has_its_own_snooze(watchdog, monkeypatch, tmp_path):
    healthy = {"status": "healthy", "detail": ""}
    drifted = {"status": "drifted", "detail": "missing live required contexts: ['CI health check']"}
    both = {"branch_protection": healthy, "branch_protection_polity": drifted}
    assert _verify_with(watchdog, monkeypatch, tmp_path, both) == 1
    # develop's snooze key does not cover polity, polity's does.
    snooze = {"until": "2026-10-01", "reason": "x"}
    assert _verify_with(watchdog, monkeypatch, tmp_path, both, {"branch-protection": snooze | {"until": "2026-12-31"}}) == 1
    assert _verify_with(watchdog, monkeypatch, tmp_path, both, {"branch-protection-polity": snooze | {"until": "2026-12-31"}}) == 0


def test_main_is_checked_without_strict_and_has_its_own_snooze(watchdog, monkeypatch, tmp_path):
    """main's protection is checked too: the same base contexts as develop
    minus the review gate and Workflow lint (they never run on PRs to main),
    and strict off (protect_main explains why). Drift fails the check, and
    only main's own snooze key silences it."""
    develop, _ = watchdog.parse_setup_script_expectations("develop")
    main, strict = watchdog.parse_setup_script_expectations("main")
    assert not strict
    assert sorted(main) == sorted(c for c in develop if c not in {"High-risk review gate", "Workflow lint"})
    healthy = {"status": "healthy", "detail": ""}
    drifted = {"status": "drifted", "detail": "missing live required contexts: ['Playwright E2E']"}
    snap = {"branch_protection": healthy, "branch_protection_polity": healthy,
            "branch_protection_main": drifted}
    assert _verify_with(watchdog, monkeypatch, tmp_path, snap) == 1
    snooze = {"until": "2026-12-31", "reason": "x"}
    assert _verify_with(watchdog, monkeypatch, tmp_path, snap, {"branch-protection": snooze}) == 1
    assert _verify_with(watchdog, monkeypatch, tmp_path, snap, {"branch-protection-polity": snooze}) == 1
    assert _verify_with(watchdog, monkeypatch, tmp_path, snap, {"branch-protection-main": snooze}) == 0


def test_a_branch_without_a_protect_function_is_an_error_not_a_guess(watchdog, monkeypatch):
    """A branch the map doesn't know must not inherit another branch's strict flag."""
    monkeypatch.delitem(watchdog.PROTECT_FUNCTIONS, "main")
    with pytest.raises(ValueError, match="no protect function for main"):
        watchdog.parse_setup_script_expectations("main")
    assert watchdog.check_branch_protection_drift("main")["status"] == "unhealthy"


@pytest.mark.parametrize(
    ("app_var", "branch", "live_app", "expected"),
    [
        ("", "polity", -1, "healthy"),  # no App configured: any source, as before
        ("424242", "polity", 424242, "healthy"),  # pinned to the configured App
        ("424242", "polity", -1, "drifted"),  # App configured, gate left unpinned
        ("424242", "develop", 15368, "drifted"),  # pinned to another app (Actions)
        ("424242", "main", None, "healthy"),  # main never requires the gate
        (" 424242\n", "polity", 424242, "healthy"),  # a pasted variable's whitespace
    ],
)
def test_the_review_gate_must_be_pinned_to_the_configured_app(
    watchdog, monkeypatch, app_var, branch, live_app, expected
):
    """Phase 3b: with REVIEW_GATE_APP_ID set, an unpinned (or wrongly pinned)
    gate is drift, since any workflow's GITHUB_TOKEN could then satisfy it."""
    assert watchdog.review_gate_name() == "High-risk review gate"  # read from the script
    contexts, strict = watchdog.parse_setup_script_expectations(branch)
    checks = [
        {"context": c, "app_id": live_app if c == watchdog.review_gate_name() else -1} for c in contexts
    ]
    live = {"required_status_checks": {"strict": strict, "checks": checks}}
    monkeypatch.setattr(watchdog, "_run_gh_json", lambda _args: live)
    monkeypatch.setenv("REVIEW_GATE_APP_ID", app_var)
    result = watchdog.check_branch_protection_drift(branch)
    assert result["status"] == expected, result
    if expected == "drifted":
        assert "REVIEW_GATE_APP_ID" in result["detail"]


def test_a_snapshot_from_before_polity_was_checked_still_verifies(watchdog, monkeypatch, tmp_path):
    """PRs read develop's snapshot, which predates this check until the next audit."""
    assert _verify_with(watchdog, monkeypatch, tmp_path, {"branch_protection": {"status": "healthy"}}) == 0


def test_runs_from_both_branches_count_once_each(watchdog, monkeypatch):
    """Scheduled deep-test runs report develop; pushes to polity report polity."""
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)
    runs = {
        "develop": [{"databaseId": 1, "status": "completed", "conclusion": "failure", "createdAt": _iso(30), "event": "schedule"}],
        "polity": [{"databaseId": 2, "status": "completed", "conclusion": "failure", "createdAt": _iso(2), "event": "push"},
                   {"databaseId": 1, "status": "completed", "conclusion": "failure", "createdAt": _iso(30), "event": "schedule"}],
    }
    monkeypatch.setattr(watchdog, "_run_gh_json",
                        lambda args: runs[next(a for a in args if a.startswith("--branch=")).split("=", 1)[1]])
    health = watchdog.query_workflow_health("flaky-check-backend.yml")
    assert health["recent_conclusions"] == ["failure", "failure"]
    assert health["status"] == "unhealthy"


def test_the_security_audit_is_judged_on_its_scheduled_runs_alone(watchdog, monkeypatch):
    """audit.yml runs on every push and PR, which scan only new commits; their
    green buried the weekly full-history Secret Scan failing four Mondays
    running. Its runs are queried with --event=schedule, the others' are not."""
    monkeypatch.setattr(watchdog, "_now", lambda: NOW)
    queried: list[list[str]] = []
    scheduled = [{"databaseId": 1, "status": "completed", "conclusion": "failure", "createdAt": _iso(24), "event": "schedule"},
                 {"databaseId": 2, "status": "completed", "conclusion": "failure", "createdAt": _iso(192), "event": "schedule"}]
    pushes = [{"databaseId": 3, "status": "completed", "conclusion": "success", "createdAt": _iso(1), "event": "push"}]

    def fake_gh(args):
        queried.append(args)
        return scheduled if "--event=schedule" in args else pushes + scheduled

    monkeypatch.setattr(watchdog, "_run_gh_json", fake_gh)
    health = watchdog.query_workflow_health("audit.yml")
    assert health["status"] == "unhealthy"
    assert health["expected_cadence_hours"] == 24 * 7
    assert all("--event=schedule" in args for args in queried)
    assert {a for args in queried for a in args if a.startswith("--branch=")} == {f"--branch={watchdog.BRANCH}"}

    queried.clear()
    watchdog.query_workflow_health("dast.yml")
    assert not any("--event=schedule" in args for args in queried)


def test_an_unreadable_expectation_is_reported_not_crashed(watchdog, monkeypatch, tmp_path):
    """--update must still write the snapshot (workflow health included) when the
    setup script can't print a branch's contexts, e.g. jq missing."""
    broken = tmp_path / "setup.sh"
    broken.write_text("echo 'jq: command not found' >&2; exit 127\n")
    monkeypatch.setattr(watchdog, "SETUP_BRANCH_PROTECTION", broken)
    result = watchdog.check_branch_protection_drift("polity")
    assert result["status"] == "unhealthy"
    assert "jq: command not found" in result["detail"]


def test_every_branch_requiring_workflow_lint_triggers_it_on_prs(watchdog):
    """A required check nothing posts blocks every PR forever (PR #205): each
    branch whose contexts include "Workflow lint" must be a pull_request branch
    of workflow-lint.yml."""
    import yaml

    workflow = SCRIPT.parents[1] / ".github" / "workflows" / "workflow-lint.yml"
    triggers = yaml.safe_load(workflow.read_text(encoding="utf-8"))[True]  # `on:` parses as True
    pr_branches = set(triggers["pull_request"]["branches"])
    requiring = {b for b in ("main", "develop", "polity", "polity-ui")
                 if "Workflow lint" in watchdog.parse_setup_script_expectations(b)[0]}
    assert requiring == {"develop", "polity"}
    assert requiring <= pr_branches
