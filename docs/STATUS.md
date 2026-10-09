# Status

> Where each part of the project stands and what comes next. One page, updated at
> the end of each phase of [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md) and whenever
> the next steps change. Last update: **2026-10-09**: the W2.1 gate said STOP; W1.2,
> W1.4 (first half) and W3.2 are in PRs held for review.

## The three parts

| Part | State | Plan workstream |
|---|---|---|
| **Vote Lab** (the teaching app) | 29 methods, 14 stories, 63 Lab fiches, with 28 methods parity-locked across the two engines. Merged: the paradox story's Condorcet claim, nine criteria cells and several THEORY.md statements (#859); the playground's quick fixes (#860); two more story figures caught by the new claims checks (#868). Held for review: one registry for the criteria matrix, checked by both engines (#869); a winner strip on every playground step, five methods by default, and "no fixed winner" for the lottery (#874); a "report a content error" form and an e2e winner oracle for the stories (#875). Still to do: the playground does not yet say *why* methods disagree (W3.3). | W1, W3 |
| **Polity** (LLM-society research) | **The threshold experiment stops at its gate.** Told the seat threshold is 3% or 7%, founders found a party 59 times in 60 either way (exact McNemar p = 1), and at least 13 of the 14 whose backing is below 7 founded at 7% (OBS-045). By the plan's rule there is no pilot, no main run and no pre-registration, and Polity's Phase 2–3 time goes to the write-up (W2.6). The instrumentation stays merged (#861–#866). The phase11 ensemble is analysed (OBS-044, #876): with OBS-041–043 fixed, turnout recovers to about 85%, but Phase 4's exit is still not met (4 of 10 seeds in the 1.5–8 band at the last election). | W2 |
| **Process** (CI, agents, docs) | **Frozen to maintenance.** Every plan states its status ([index](README.md#plans)); the journal is retired; the PR template and `/verify` are in English (#867). | W4, W5 |

## Rules while the plan runs

CI and process work is frozen to maintenance, and there is no hosted instance: see
the plan's [ground rules](plan/PLAN_BEYOND_CI.md#context).

## Next 3 steps

1. **W2.6:** the `docs/stories/` piece on the logprob instrument, which gets Polity's
   Phase 2–3 time now that the experiment is off.
2. **W3.3:** the "why" in the Bilan, after #874 merges.
3. **W1.4, second half,** after #869 merges: a tooltip per matrix cell with its source
   and basis, and the expert-review packet (THEORY §2–4, the registry's 110 unsourced cells).

## Waiting on the owner

- **Reviews** of the three held PRs: #869, #874, #875. All three regenerate the
  Laboratoire screenshot baseline, so each one merged after the first needs it regenerated.
- **#869's CI filter.** The push token lacks GitHub's `workflow` scope, so the 4-line
  path-filter patch in #869's body is yours to apply.
- **The venv's stale scripts** (`.venv/bin/lint-imports` still points at
  `/home/burbanit0/Vote-App/...`), which make fast-gate's layering check fail locally.
  Recreating the venv fixes it.
- **Outreach** (Phases 3–4): one social-choice researcher (W1.4), and one teacher for a
  projector demo (W3.5).
- **The Zenodo upload** of the archived runs (W2.5).

## Open questions

- Phase 4 exit for Polity: still not met at ten seeds (OBS-044). Move the band, a rule, or nothing?
  The roadmap leaves that to the owner.
- Why does founding not follow the stated threshold (OBS-045)? At least 13 of the 14 founders
  it should have stopped founded anyway; a rerun logging each answer next to its backing would
  give the exact figure.
- Expert review: are the 110 unsourced criteria cells right, and are W1.1's MJ
  "majority: conditional" and W1.2's two cell changes right?
