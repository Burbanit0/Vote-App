#!/usr/bin/env python3
"""PreToolUse hook (Lot 2, PLAN_SOLIDITE_TECHNIQUE.md) — blocks any Edit/Write/
MultiEdit targeting voter-app/src/lib/__fixtures__/engineParity.json.

CLAUDE.md is explicit: "engineParity.json is a generated artifact — never
hand-edit it (not even to silence a failing parity test); always regenerate
it via gen_engine_parity.py." That rule was previously enforced only by
someone reading CLAUDE.md — this makes it structurally impossible instead.

Reads the PreToolUse payload from stdin, checks tool_input.file_path (the
field Edit/Write/MultiEdit all use), and prints a `permissionDecision: deny`
JSON response when it matches. Silent (no output) otherwise, so normal
permission handling applies to every other file.
"""
import json
import sys

TARGET_SUFFIX = "voter-app/src/lib/__fixtures__/engineParity.json"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    file_path = str(payload.get("tool_input", {}).get("file_path") or "")
    file_path = file_path.replace("\\", "/")

    if not file_path.endswith(TARGET_SUFFIX):
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "engineParity.json is a GENERATED artifact (CLAUDE.md) — "
                "never hand-edited, not even to fix a failing parity test. "
                "Regenerate it instead: "
                "python fast_api_voter/scripts/gen_engine_parity.py"
            ),
        }
    }))


if __name__ == "__main__":
    main()
