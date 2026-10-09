# Status

> Where each part of the project stands and what comes next. One page, updated at
> the end of each phase of [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md) and whenever
> the next steps change. Last update: **2026-10-08**; Phase 1 is nearly done (W1.2 and W1.3 are in PRs).

## The three parts

| Part | State | Plan workstream |
|---|---|---|
| **Vote Lab** (the teaching app) | 29 methods, 14 stories, 63 Lab fiches, with 28 methods parity-locked across the two engines. Merged: the paradox story's Condorcet claim, nine criteria cells and several THEORY.md statements (#859); the playground's quick fixes (#860). Queued to merge: two more story figures caught by the new claims checks (#868). Held for review: one registry for the criteria matrix, checked by both engines (#869). Still to do: the playground does not yet say *why* methods disagree (W3.2–W3.3). | W1, W3 |
| **Polity** (LLM-society research) | The threshold experiment is instrumented. Merged: founders told the threshold (#861), paired statistics (#862), ENP in the digest (#863), the re-seating script (#864), the arms' run knobs (#865), the fit-for-inference table (#866). **Blocked:** the W2.1 gate probe needs the GPU, and an unattended NVIDIA library upgrade means it needs a reboot first. The phase11 ensemble (10 seeds, finished 2026-10-07) is still not analysed. | W2 |
| **Process** (CI, agents, docs) | **Frozen to maintenance.** Every plan now states its status ([index](README.md#plans)); the journal is retired; the PR template and `/verify` are in English (#867). | W4, W5 |

## Rules while the plan runs

CI and process work is frozen to maintenance, and there is no hosted instance: see
the plan's [ground rules](plan/PLAN_BEYOND_CI.md#context).

## Next 3 steps

1. **W2.1 gate, after a reboot:** `python fast_api_voter/scripts/check_agent_prompt_neutrality.py --probe threshold --n 60`.
   It decides whether the threshold experiment runs at all.
2. **W3.2:** a winner strip on every playground step, and 5 methods by default.
3. **W1.4,** once #868 and #869 merge: the expert-review packet (THEORY §2–4, the registry's 110 unsourced
   cells) and a "report a content error" path.

## Waiting on the owner

- **A review** of #869, the one PR held (it touches the engine's test harness).
- **#869's CI filter.** The push token lacks GitHub's `workflow` scope, so the 4-line
  path-filter patch in #869's body is yours to apply.
- **A reboot,** so the GPU works again (`/var/run/reboot-required`).
- **The venv's stale scripts** (`.venv/bin/lint-imports` points at
  `/home/burbanit0/Vote-App/...`), which make fast-gate's layering check fail locally.
  Recreating the venv fixes it.
- **Outreach** (Phases 3–4): one social-choice researcher (W1.4), and one teacher for a
  projector demo (W3.5).
- **The Zenodo upload** of the archived runs (W2.5).

## Open questions

- Phase 4 exit for Polity: does phase11 meet it, now that OBS-041/042/043 are fixed?
- Does founding respond to a stated threshold at all (the W2.1 gate)?
- Expert review: are the 110 unsourced criteria cells right, and are W1.1's MJ
  "majority: conditional" and W1.2's two cell changes right?
