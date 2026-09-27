---
name: feedback-gh-pr-targets-develop
description: "In Vote-App(-polity), gh pr create must explicitly target develop — it defaults to main, which fails a repo CI gate"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-29T15:19:01.533Z
---

`gh pr create` without an explicit `--base` targets the repo's default branch, which is `main` in this repo — but this repo's CI ("Validate branch source and naming") hard-rejects any PR into `main` whose source isn't `develop` itself. Every feature/lot PR must target `develop`, never `main` directly; `develop → main` is reserved for releases via the `🚀 Release Vote Lab` workflow.

**Why:** hit this directly while landing the v4 vLLM switch (PR #139, [[project_polity_vllm_switch]]) — `gh pr create` silently opened against `main`, and the branch-naming check failed immediately (fixed with `gh pr edit 139 --base develop`, which re-triggered CI cleanly). Costs a wasted CI cycle each time it's missed.

**How to apply:** always pass `--base develop` explicitly when running `gh pr create` in this repo (both `Vote-App` and `Vote-App-polity` worktrees, same remote). If it's already been created against the wrong base, `gh pr edit <number> --base develop` fixes it in place without needing to recreate the PR.

**Update 2026-08-29 — superseded for polity work specifically**, see
[[project-polity-branch-workflow]]: an integration branch `polity` now sits
between polity feature branches and `develop`. In the `Vote-App-polity`
worktree, polity PRs now target `--base polity`, not `--base develop` — the
underlying fact here (default branch is `main`, CI rejects non-`develop` →
`main`) still applies once `polity` itself eventually merges onward, just
not as the immediate target for feature-branch PRs anymore.
