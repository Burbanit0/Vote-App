"""
SessionStart hook: surface simulation runs whose story has not been written yet.

A flagship run (fast_api_voter/scripts/run_polity_flagship.py) now writes a
`digest.json` beside its journal on every ending -- completed, crashed or
interrupted (api/domain/polity/run_digest.py). Turning that digest into a
readable `TIMELINE.md` is a judgement task, so it is done in-session by the
`run-narrator` sub-agent rather than unattended; this hook is what makes sure
nobody has to remember it happened.

**Why SessionStart and not TaskCompleted.** Measured, 2026-09-11, with the
sentinel test /update-config prescribes: a `TaskCompleted` hook did NOT fire
when a `run_in_background` Bash task completed. That was confirmed to be a real
negative and not a stale-config artifact by a control probe -- a PostToolUse
hook added in the same edit DID fire in the same session, so new hooks were
loading. TaskCompleted appears to be tied to the task tool, not to backgrounded
shell commands. SessionStart is also the only leg that covers the case that
motivated all of this: a host reboot killed a 14-hour run at 07:14 the same
morning, and no in-process or in-session mechanism can run at all when the
machine goes down -- but the next session still starts.

Never blocks and never fails a session: every failure path returns silently,
the same guarantee scripts/git_commit_capture.py gives a commit.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RUNS_GLOB = "fast_api_voter/scripts/flagship_runs/*/run/*/digest.json"
TIMELINE_NAME = "TIMELINE.md"
MAX_LISTED = 5


def pending_narratives(project_dir: Path) -> list[tuple[str, str]]:
    """(run_id, outcome) for every run holding a digest with no TIMELINE.md, or
    one written before the digest was last updated -- a run interrupted, then
    resumed and completed, has a story worth rewriting."""
    pending = []
    for digest_path in sorted(project_dir.glob(RUNS_GLOB)):
        timeline = digest_path.with_name(TIMELINE_NAME)
        if timeline.is_file() and timeline.stat().st_mtime >= digest_path.stat().st_mtime:
            continue
        try:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(digest, dict):
            continue
        ticks = digest.get("ticks") or {}
        reached = f"{ticks.get('last_tick_journaled')}/{ticks.get('planned_total')} ticks"
        pending.append((str(digest.get("run_id", digest_path.parent.name)),
                        f"{digest.get('outcome', 'unknown')}, {reached}{_fallback_note(digest)}"))
    return pending


def _fallback_note(digest: dict) -> str:
    """Surface a degraded run here rather than only inside digest.json.

    This hook already opens every digest at session start, so flagging a
    tripped `llm_fallback_alerts` costs no extra I/O -- and without it, a run
    where one decision type ran almost entirely on its deterministic fallback
    is listed in exactly the same words as a clean one. `None` means the check
    could not run (no progress.json), which is deliberately NOT reported as
    clear -- see run_digest.build_digest's own comment."""
    alerts = digest.get("llm_fallback_alerts")
    if alerts is None:
        return ", fallback UNKNOWN"
    if not alerts:
        return ""
    worst_type, worst_rate = max(alerts.items(), key=lambda kv: kv[1])
    if len(alerts) > 1:
        return f", FALLBACK ALERT: {len(alerts)} types, worst {worst_type} {worst_rate:.0%}"
    return f", FALLBACK ALERT: {worst_type} {worst_rate:.0%}"


def main() -> None:
    try:
        json.load(sys.stdin)  # payload unused; consumed so the hook never blocks on a pipe
    except Exception:  # noqa: BLE001 -- a hook must not fail a session over its own input
        pass
    try:
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
        pending = pending_narratives(project_dir)
    except Exception:  # noqa: BLE001 -- same reason
        return
    if not pending:
        return

    shown = pending[:MAX_LISTED]
    lines = [f"  - {run_id} ({state})" for run_id, state in shown]
    if len(pending) > MAX_LISTED:
        lines.append(f"  - ... and {len(pending) - MAX_LISTED} more")
    # Plain stdout: SessionStart injects it into the model's context.
    print(
        f"{len(pending)} simulation run(s) have a digest but no written TIMELINE.md:\n"
        + "\n".join(lines)
        + "\nRun /log-run to have the run-narrator sub-agent write the story of one of them."
    )


if __name__ == "__main__":
    main()
