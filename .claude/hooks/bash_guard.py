#!/usr/bin/env python3
"""PreToolUse hook on Bash (CI hardening plan, phase 4).

Denies, for an agent session:
  - force pushes, `--no-verify`, `git reset --hard`, and pushes straight to
    polity / develop / main (every change goes through a PR);
  - merging a PR or approving its high-risk hold: `gh pr merge`, posting
    `/reviewed`, adding a `reviewed` label, setting a `human-review` status.
    That approval is the owner's alone (.mergify.yml, human-review.yml).
Asks the owner before:
  - regenerating a test oracle or ratchet baseline (gen_*.py, snapshot
    updates, `--update` on a ratchet script): a regeneration after a code change
    makes its drift check pass by design;
  - shell writes to a guardrail file (redirects, tee, sed -i, mv, cp, rm, ...).
Runs scripts/fast-gate.sh before any other `git push` and denies the push on
findings, quoting the output.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guardlib import (  # noqa: E402
    ROOT, context, decide, is_guardrail, read_payload, rel_path, shell_segments,
)

PROTECTED_BRANCHES = {"polity", "develop", "main"}
FAST_GATE_TIMEOUT_S = 540
APPROVAL = "approving or merging a PR is the repository owner's alone (CLAUDE.md, .mergify.yml)"


_GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}


def git_argv(argv: list[str]) -> tuple[list[str], str | None] | None:
    """For a git command, (["git", <subcommand>, ...], -C dir or None) with the
    global options before the subcommand removed; None for anything else."""
    if not argv or Path(argv[0]).name != "git":
        return None
    i, cwd = 1, None
    while i < len(argv) and argv[i].startswith("-"):
        opt = argv[i]
        if opt in _GIT_OPTS_WITH_VALUE:
            if opt == "-C" and i + 1 < len(argv):
                cwd = argv[i + 1]
            i += 2
        else:
            i += 1  # --no-pager, -P, --bare, --git-dir=x, ...
    return ["git", *argv[i:]], cwd


def current_branch(cwd: str | None) -> str:
    override = os.environ.get("GUARD_CURRENT_BRANCH")
    if override is not None:
        return override
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT / (cwd or "."),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def push_problem(argv: list[str], cwd: str | None = None) -> str | None:
    args = argv[2:]
    if any(a in {"-f", "--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "-d"}
           or a.startswith("--force") for a in args):
        return "force/mirror/delete pushes are not allowed from an agent session"
    if "--no-verify" in args:
        return "--no-verify skips the checks this repo relies on"
    positional = [a for a in args if not a.startswith("-")]
    implicit = len(positional) <= 1 or any(r.split(":")[-1].lstrip("+") in {"HEAD", "@"} for r in positional[1:])
    if implicit:
        # `git push`, `git push origin`, `git push origin HEAD`: the destination
        # is the current branch (push.default=simple/current).
        branch = current_branch(cwd)
        if branch in PROTECTED_BRANCHES:
            return f"this pushes the current branch, {branch}: open a PR from a feat/fix/ci/chore branch (CLAUDE.md)"
    for refspec in positional[1:]:  # positional[0] is the remote
        dst = refspec.split(":")[-1].lstrip("+")
        dst = dst.removeprefix("refs/heads/")
        if refspec.startswith("+"):
            return "force pushes (+refspec) are not allowed from an agent session"
        if dst in PROTECTED_BRANCHES:
            return f"never push directly to {dst}: open a PR from a feat/fix/ci/chore branch (CLAUDE.md)"
    return None


def classify(argv: list[str]) -> tuple[str, str] | None:
    """(decision, reason) for one simple command, or None."""
    joined = " ".join(argv)
    prog = Path(argv[0]).name
    git = git_argv(argv)
    if git and len(git[0]) > 1:
        gargv, cwd = git
        if gargv[1] == "push":
            problem = push_problem(gargv, cwd)
            return ("deny", problem) if problem else ("push", "")
        if gargv[1] == "reset" and "--hard" in gargv:
            return "deny", "git reset --hard discards work irrecoverably; ask the user first"
        if gargv[1] in {"commit", "merge", "rebase", "cherry-pick"} and "--no-verify" in gargv:
            return "deny", "--no-verify skips the checks this repo relies on"
    if prog == "gh":
        if argv[1:3] == ["pr", "merge"]:
            return "deny", f"`gh pr merge`: {APPROVAL}. Mergify merges once checks and the review hold pass."
        if argv[1:2] in (["pr"], ["issue"]) and "--add-label" in argv and re.search(r"\breviewed\b", joined):
            return "deny", f"adding the `reviewed` label: {APPROVAL}"
        if re.search(r"(^|\s)/reviewed\b", joined):
            return "deny", f"posting `/reviewed`: {APPROVAL}"
        if argv[1:2] == ["api"] and re.search(r"/statuses/|human-review|/merge\b|labels.*reviewed|reviewed.*labels", joined):
            return "deny", f"setting statuses, review labels or merging through the API: {APPROVAL}"
        if argv[1:3] == ["api", "graphql"] and _GRAPHQL_APPROVAL.search(joined):
            return "deny", f"merging or approving through the GraphQL API: {APPROVAL}"
        if _body_file_has_reviewed(argv):
            return "deny", f"posting `/reviewed` from a file: {APPROVAL}"
    if prog in {"curl", "wget", "http", "xh", "httpie"} and _RAW_GITHUB_APPROVAL.search(joined):
        return "deny", f"merging, setting statuses or calling GraphQL on GitHub outside gh: {APPROVAL}"
    if re.search(r"(^|/)gen_(engine_parity|polity_golden|openapi)\.py\b", joined) or re.search(
            r"--snapshot-update\b|--update-snapshots\b|(^|\s)-u(\s|$).*(vitest|playwright)|(vitest|playwright).*\s-u(\s|$)", joined):
        return "ask", ("this regenerates a test oracle. After a behaviour change that makes the oracle's own check pass "
                       "by design; confirm the new output is the intended behaviour, not a bug being signed off.")
    if re.search(r"check_(quality_ratchet|mutation_score)\.sh\b.*--update|type-coverage.*--update", joined):
        return "ask", "this re-records a ratchet baseline. Only legitimate after a real improvement (voter-ci skill)."
    return None


# GraphQL mutations that merge or approve; `gh api graphql` bypasses the REST path checks above.
_GRAPHQL_APPROVAL = re.compile(
    r"mergePullRequest|PullRequestAutoMerge|enqueuePullRequest|mergeBranch|createCommitStatus"
    r"|addPullRequestReview\b.*APPROVE|addLabelsToLabelable.*reviewed")
# The same endpoints reached without gh (curl and friends): merges, statuses, GraphQL.
_RAW_GITHUB_APPROVAL = re.compile(r"api\.github\.com/(?:\S*/(?:merges?|statuses)\b|graphql\b)")


def _body_file_has_reviewed(argv: list[str]) -> bool:
    """`gh pr|issue comment --body-file f` and `gh api ... -F body=@f`: the command
    line never shows the body, so read the file it names."""
    paths = []
    for k, tok in enumerate(argv):
        if tok in {"--body-file", "-F", "--field"} and k + 1 < len(argv):
            nxt = argv[k + 1]
            paths.append(nxt[nxt.index("=@") + 2:] if "=@" in nxt else nxt if tok == "--body-file" else "")
        elif tok.startswith("--body-file="):
            paths.append(tok.split("=", 1)[1])
    for path in filter(None, paths):
        if path == "-":
            return True  # a body read from stdin can't be checked: refuse rather than guess
        try:
            if re.search(r"(^|\s)/reviewed\b", (ROOT / path if not os.path.isabs(path) else Path(path)).read_text(errors="ignore")):
                return True
        except OSError:
            continue
    return False


_ALL_ARGS_WRITE = {"tee", "mv", "rm", "truncate", "ln", "chmod", "install", "dd", "unlink", "shred"}


def write_targets(argv: list[str]) -> list[str]:
    """Paths one simple command writes, deletes or moves (best effort)."""
    targets = []
    for k, tok in enumerate(argv):
        # Redirections: `> f`, `>> f`, `>f`, `1>f` (stderr-only `2>` is not a write we care about).
        m = re.match(r"^(?:1|&)?>>?(.*)$", tok)
        if m:
            if m.group(1):
                targets.append(m.group(1))
            elif k + 1 < len(argv):
                targets.append(argv[k + 1])
    prog = Path(argv[0]).name
    args = [a for a in argv[1:] if not a.startswith("-")]
    if prog in _ALL_ARGS_WRITE:
        targets += args
    elif prog == "cp" and args:
        targets.append(args[-1])
    elif prog in {"sed", "perl"} and any(a.startswith("-i") or a.startswith("-pi") for a in argv[1:]):
        targets += args[1:] if prog == "sed" else args
    elif (git := git_argv(argv)) and len(git[0]) > 1 and git[0][1] in {"checkout", "restore", "rm", "mv"}:
        targets += [a for a in git[0][2:] if not a.startswith("-")]
    return targets


def guardrail_write(segments: list[list[str]]) -> str | None:
    for argv in segments:
        for target in write_targets(argv):
            rel = rel_path(target)
            if rel and is_guardrail(rel):
                return rel
    return None


def fast_gate_path() -> Path:
    # Tests point this at a stub. The hook runs in Claude Code's own process
    # environment, which a Bash tool command cannot change.
    return Path(os.environ.get("GUARD_FAST_GATE") or ROOT / "scripts" / "fast-gate.sh")


def run_fast_gate() -> tuple[int, str]:
    try:
        res = subprocess.run(["bash", str(fast_gate_path())], cwd=ROOT,
                             capture_output=True, text=True, timeout=FAST_GATE_TIMEOUT_S)
        return res.returncode, (res.stdout + res.stderr)
    except subprocess.TimeoutExpired:
        return 0, f"fast-gate timed out after {FAST_GATE_TIMEOUT_S}s; CI will run the full checks."
    except OSError as e:
        return 0, f"fast-gate could not run ({e}); CI will run the full checks."


def main() -> None:
    payload = read_payload()
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not command:
        return
    # Whole-command check: a `/reviewed` body can reach gh through a heredoc,
    # a file, or `$'...'` quoting that the per-command split doesn't see.
    segments = shell_segments(command)
    if re.search(r"/reviewed\b", command) and any(
            Path(a[0]).name in {"gh", "curl", "wget", "http", "xh"} for a in segments):
        decide("deny", f"posting `/reviewed`: {APPROVAL}")
        return
    pushes = False
    asks = []
    for argv in segments:
        verdict = classify(argv)
        if not verdict:
            continue
        decision, reason = verdict
        if decision == "deny":
            decide("deny", reason)
            return
        if decision == "push":
            pushes = True
        elif decision == "ask":
            asks.append(reason)
    target = guardrail_write(segments)
    if target:
        asks.append(f"this shell command writes to `{target}`, part of the CI/guardrail safety net.")
    if asks:
        decide("ask", " ".join(asks))
        return
    if pushes and fast_gate_path().exists():
        code, out = run_fast_gate()
        tail = "\n".join(out.strip().splitlines()[-60:])
        if code != 0:
            decide("deny", "scripts/fast-gate.sh found problems in this branch's changes; fix them, then push again.\n" + tail)
        elif "SKIPPED" in out:
            context("fast-gate passed, but some sections were SKIPPED (missing deps); CI is the only check for those:\n" + tail)


if __name__ == "__main__":
    main()
