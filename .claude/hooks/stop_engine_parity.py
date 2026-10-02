#!/usr/bin/env python3
"""Stop hook (CI hardening plan, phase 4): don't end a turn with one side of the
dual voting engine changed and the parity fixture untouched.

remind_engine_parity_regen.py only nudges right after the edit, and a nudge can
scroll away. This checks at the end of the turn, against everything the branch
changed (commits since origin/polity plus the working tree), and blocks the stop
once with the instruction. `stop_hook_active` guards the loop: a turn that was
already blocked by this hook is let through, so a change that genuinely leaves
the winners alone (regeneration gives no diff) can still finish, by saying so.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guardlib import ROOT, read_payload  # noqa: E402

ENGINE = {
    "fast_api_voter/api/engine/utils/simulation_ranked_utils.py",
    "fast_api_voter/api/engine/utils/simulation_score_utils.py",
    "voter-app/src/lib/playgroundVoting.ts",
}
FIXTURE = "voter-app/src/lib/__fixtures__/engineParity.json"


def git_lines(*args: str) -> set[str]:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def changed_files() -> set[str]:
    base = git_lines("merge-base", "HEAD", "origin/polity")
    changed = set()
    if base:
        changed |= git_lines("diff", "--name-only", next(iter(base)), "HEAD")
    changed |= git_lines("diff", "--name-only", "HEAD")  # staged + unstaged
    changed |= git_lines("ls-files", "--others", "--exclude-standard")  # untracked
    return changed


def main() -> None:
    payload = read_payload()
    if payload.get("stop_hook_active"):
        return
    changed = changed_files()
    touched = sorted(ENGINE & changed)
    if touched and FIXTURE not in changed:
        print(json.dumps({
            "decision": "block",
            "reason": (
                "The voting engine changed (" + ", ".join(touched) + ") but the parity fixture didn't. "
                "Run `PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py`, then "
                "`npx vitest run src/lib/playgroundVoting.parity.test.ts` in voter-app/, and commit the fixture. "
                "If regeneration produces no diff, say so explicitly in your reply (CLAUDE.md, dual engine)."
            ),
        }))


if __name__ == "__main__":
    main()
