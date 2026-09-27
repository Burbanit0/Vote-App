#!/usr/bin/env python3
"""PostToolUse hook (Lot 2, PLAN_SOLIDITE_TECHNIQUE.md) — reminds to
regenerate engineParity.json after editing either side of the dual voting
engine.

CLAUDE.md: "If you change a rule on either side: re-run
fast_api_voter/scripts/gen_engine_parity.py, then run the parity test."
A PostToolUse hook can't block (the edit already happened) — this is
reminder-only, via `systemMessage`, so the same nudge survives whichever
side (client or backend) gets touched, without anyone having to remember
CLAUDE.md's own wording.

Reads the PostToolUse payload from stdin, checks tool_input.file_path
against the two backend files + the client mirror, and prints a
systemMessage when it matches. Silent (no output) otherwise.
"""
import json
import sys

ENGINE_FILES = (
    "fast_api_voter/api/engine/utils/simulation_ranked_utils.py",
    "fast_api_voter/api/engine/utils/simulation_score_utils.py",
    "voter-app/src/lib/playgroundVoting.ts",
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    file_path = str(payload.get("tool_input", {}).get("file_path") or "")
    file_path = file_path.replace("\\", "/")

    if not any(file_path.endswith(f) for f in ENGINE_FILES):
        return

    print(json.dumps({
        "systemMessage": (
            "Reminder (CLAUDE.md — dual voting engine): this file backs one "
            "side of the client/backend voting engine. If you changed rule "
            "behavior, regenerate the parity fixture — "
            "python fast_api_voter/scripts/gen_engine_parity.py — then run "
            "playgroundVoting.parity.test.ts before committing."
        )
    }))


if __name__ == "__main__":
    main()
