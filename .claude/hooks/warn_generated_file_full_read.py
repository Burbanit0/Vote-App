#!/usr/bin/env python3
"""PreToolUse hook (Lot 12.2, PLAN_SOLIDITE_TECHNIQUE.md) — warns on a
full-file `Read` of a generated artifact nobody should ever load in full.

Real, measured sizes on this repo (~4 bytes/token):

    voter-app/package-lock.json                          ~752 KB
    fast_api_voter/openapi.gen.json                      ~544 KB
    voter-app/src/api/types.gen.ts                        ~440 KB
    voter-app/src/lib/__fixtures__/engineParity.json      ~364 KB

All four are generated artifacts (never hand-edited — CLAUDE.md already says
so for engineParity.json, enforced by block_engine_parity_edit.py) that
together weigh ~2.1MB. A single accidental full read of one of them burns a
large fraction of a context window for zero benefit: nothing in them is meant
to be read start to finish, only regenerated (see each file's generator) or
grepped/diffed for one specific value.

`.claudeignore` is not a real Claude Code mechanism (verified against
https://code.claude.com/docs/en/permissions and the still-open upstream
request, github.com/anthropics/claude-code#579 — it does not exist, and a
`.claudeignore` file would be silently inert). A hard `permissions.deny` Read
rule was also considered and rejected: it would block the targeted
offset/limit reads this hook deliberately exempts (e.g. checking one specific
line after a regen diff), which is sometimes legitimate. A PreToolUse
*warning* is the closest real lever, modeled on the existing graphify guard
in .claude/settings.json.

This is advisory only (`additionalContext`), never `permissionDecision: deny`
— the plan item's own wording calls it an "avertissement", and unlike
engineParity.json there's no hand-edit hazard here to hard-block, just a
token-budget hazard to flag.

Reads the PreToolUse payload from stdin, checks tool_input.file_path against
the four generated files, and — unless tool_input.limit is set (a genuinely
range-scoped read) — prints an additionalContext nudge toward offset/limit or
a targeted grep. Silent (no output) otherwise.
"""
import json
import sys

TARGET_SUFFIXES = (
    "voter-app/package-lock.json",
    "fast_api_voter/openapi.gen.json",
    "voter-app/src/api/types.gen.ts",
    "voter-app/src/lib/__fixtures__/engineParity.json",
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    tool_input = payload.get("tool_input", {}) or {}

    file_path = str(tool_input.get("file_path") or "")
    file_path = file_path.replace("\\", "/")

    if not any(file_path.endswith(suffix) for suffix in TARGET_SUFFIXES):
        return

    # `limit` is what actually bounds how much of the file gets read — a bare
    # `offset` with no `limit` still reads to EOF, so only a set `limit`
    # counts as a genuinely targeted range-read and is exempt from the nudge.
    limit = tool_input.get("limit")
    try:
        limit_is_set = limit is not None and int(limit) > 0
    except (TypeError, ValueError):
        limit_is_set = False

    if limit_is_set:
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                "Heads up (Lot 12.2, PLAN_SOLIDITE_TECHNIQUE.md): this is a "
                "GENERATED artifact, not source — it can run several hundred "
                "KB and reading it in full burns a large chunk of context "
                "for no benefit. Prefer a targeted `grep`/`rg` for the value "
                "you need, or a `Read` with `offset`/`limit` scoped to a "
                "specific range. A full read is still allowed if you "
                "actually need it (e.g. auditing the whole file) — this is "
                "advisory, not blocked."
            ),
        }
    }))


if __name__ == "__main__":
    main()
