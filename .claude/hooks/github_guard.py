#!/usr/bin/env python3
"""PreToolUse hook on the GitHub MCP tools (CI hardening plan, phase 4).

The GitHub MCP server acts with the owner's own credentials, so it can do what
the Bash guard denies for `gh`. This closes the same doors:
  - merging, enabling auto-merge, or approving the high-risk review hold
    (`/reviewed` comments, the `reviewed` label, `human-review` statuses):
    the owner's alone (.mergify.yml, human-review.yml);
  - writing files straight to GitHub (create_or_update_file, push_files,
    delete_file): that skips git, the pre-push fast gate and every local hook.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guardlib import decide, read_payload  # noqa: E402

APPROVAL = "approving or merging a PR is the repository owner's alone (CLAUDE.md, .mergify.yml)"
DENY_TOOLS = {
    "merge_pull_request": f"merging: {APPROVAL}. Mergify merges once checks and the review hold pass.",
    "enable_pr_auto_merge": f"enabling auto-merge: {APPROVAL}",
    "create_or_update_file": "writing files directly on GitHub skips git, the pre-push fast gate and the local hooks; commit and push instead",
    "push_files": "pushing files through the API skips the pre-push fast gate and the local hooks; use git push",
    "delete_file": "deleting files through the API skips the pre-push fast gate and the local hooks; use git",
}


def main() -> None:
    payload = read_payload()
    tool = str(payload.get("tool_name") or "")
    if not tool.startswith("mcp__github__"):
        return
    name = tool.removeprefix("mcp__github__")
    if name in DENY_TOOLS:
        decide("deny", DENY_TOOLS[name])
        return
    blob = json.dumps(payload.get("tool_input") or {})
    if re.search(r"(^|\\n|\")\s*/reviewed\b", blob):
        decide("deny", f"posting `/reviewed`: {APPROVAL}")
    elif re.search(r"\"labels\"\s*:\s*\[[^\]]*\"reviewed\"", blob):
        decide("deny", f"adding the `reviewed` label: {APPROVAL}")
    elif re.search(r"human-review", blob) and re.search(r"status", name):
        decide("deny", f"setting the `human-review` status: {APPROVAL}")


if __name__ == "__main__":
    main()
