# Status

> Where each part of the project stands and what comes next. One page; updated at
> the end of each phase of [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md) and whenever
> the next steps change. Last update: **2026-10-08**, Phase 0.

## The three parts

| Part | State | Plan workstream |
|---|---|---|
| **Vote Lab** (the teaching app) | 29 methods, 14 stories, 63 Lab fiches; the dual engine is parity-locked on 28 methods. Some taught claims are wrong (the paradox story names a Condorcet winner where there is a cycle; STAR is marked as passing majority), and the playground shows *that* methods disagree but not *why*. | W1 (claims), W3 (playground) |
| **Polity** (LLM-society research) | 30-year runs work (p500, about 2 h). The phase11 ensemble (10 seeds × 8 years, exploration profile) **finished on 2026-10-07; its analysis is pending**. The design's own experiment, two constitutions compared across seeds, has not been run. | W2 |
| **Process** (CI, agents, docs) | 23 workflows, high-risk review hold, parity and axiom harnesses. **Frozen to maintenance** while the plan runs. | W4 (docs), W5 (engine tie bugs) |

## Rules while the plan runs

CI and process work is frozen to maintenance, and there is no hosted instance: see
the plan's [ground rules](plan/PLAN_BEYOND_CI.md#context).

## Next 3 steps

1. **W1.1:** fix the confirmed teaching errors (paradox story, STAR majority, three
   THEORY.md facts), with a test that fails on today's paradox story.
2. **W3.1:** playground quick fixes. One candidate palette, scroll reset, remove the
   broken tour, English-mode leaks, one method count, `/polity` out of the main nav,
   recharts out of the eager bundle.
3. **W2.2 item 5, then the W2.1 gate probe:** tell party founders the electoral
   threshold (ADR-018 amendment), then measure in minutes of GPU whether founding
   responds to it.

## Waiting on the owner

- `/reviewed` on held PRs. High-risk paths are listed in `.mergify.yml`.
- **Outreach** (Phase 3–4): one social-choice researcher (W1.4), and one teacher for a
  projector demo (W3.5).
- **The Zenodo upload** of the archived runs (W2.5).

## Open questions

- Phase 4 exit for Polity: does phase11 meet it, now that OBS-041/042/043 are fixed?
- Does founding respond to a stated threshold at all (the W2.1 gate)?
