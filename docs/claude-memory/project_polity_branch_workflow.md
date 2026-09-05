---
name: project-polity-branch-workflow
description: "Polity work now stages through an integration branch 'polity' before develop -- every polity feature/lot PR targets polity, not develop, until a future milestone merge"
metadata: 
  node_type: memory
  type: project
  originSessionId: 22458a2f-ddf0-45bc-bb54-2e029e1a45ce
  modified: 2026-08-30T12:49:32.220Z
---

As of 2026-08-29, a long-lived `polity` branch exists in `Burbanit0/Vote-App`
(created from `origin/develop` at that date, commit `db77561` — the merge of
PR #216, the cast_votes/distribution/ADR-002/ADR-003 chain). Every
polity-related feature/lot branch should be created **from** `polity` and
PR'd **into** `polity` (`gh pr create --base polity`), not into `develop`
directly. `polity → develop` is a separate merge.

**Merge trigger, settled 2026-08-30**: the user stated the merge happens
"after the polity plan is fully complete" — the whole `polity-simulation-
design-v2.md` §13 roadmap (v0–v8), not an earlier checkpoint like a single
palier's close. As of 2026-08-30, v0–v7 are complete and merged into
`polity`; v8 (auto-hébergement/fine-tuning) is not — the vLLM half is
blocked on an upstream bug (`plan-vllm-switch-readiness.md`, dated
reopening conditions) and the fine-tuning half has its terminology resolved
but no chantier written yet. Do not propose or ask about `polity → develop`
again until v8 is actually done (or the user says otherwise) — this
question is answered, not open.

**Why:** the user's own call, made explicit 2026-08-29, right after PR #216
(ten commits, four chantiers) merged straight into `develop`. The polity
project is a large, multi-month, multi-palier effort (`polity-simulation-
design-v2.md` §13's roadmap runs to v8) generating frequent, often
exploratory commits (ADRs opened and closed same-day, calibration sweeps,
scratchpad-probe-backed findings) — staging it behind its own integration
branch keeps `develop` insulated from that churn until there's a coherent
milestone worth exposing to the rest of the repo.

**How to apply:**
- In the `Vote-App-polity` worktree (this session's own directory), when
  opening a PR for polity work: `gh pr create --base polity`, not
  `--base develop`. This SUPERSEDES [[feedback-gh-pr-targets-develop]] for
  polity-specific branches specifically — that memory's underlying fact
  (repo default branch is `main`, CI rejects non-`develop` → `main` PRs)
  still holds and still matters once `polity` itself is eventually merged
  toward `develop`/`main`, but the immediate target for polity feature
  branches is now `polity`.
- The `Vote-App` worktree (no `-polity` suffix, same remote) is presumably
  unaffected — its own PRs should keep targeting `develop` per the existing
  memory, unless told otherwise.
- Before merging `polity → develop` eventually, check with the user for
  which milestone triggers it — this was stated as "at the end," not tied to
  a specific version in the 2026-08-29 conversation.
