# ADR-022: a president who refuses to leave

**Status**: Accepted — Phase 5.1 of `docs/plan/polity/plan-polity-agency-roadmap.md`. Covers one act; the others wait for evidence.
**Date**: 2026-09-30
**Context**: Decision D6 says extra-legal acts can succeed. The limit-testing log (`other_initiative`, three
8-year LLM runs, OBS-029) holds no extra-legal act, because the menu offers none to name. What it does hold
is presidents proposing to lift the term limit (seeds 1 and 3), so the first act is the one that wish leads to.

## Decision

- **The act**: `extra_legal: "refuse_to_leave"` on the president's turn (`ActingLeaderTurn`, only when
  `regime.enabled`). It counts only from a term-limited president, on the tick before their election; at any
  other time it is ignored. The system prompt states the act and its stakes, never what to do (C4).
  **Amended 2026-10-10 (OBS-041):** a term counts against the limit only if it was won with at least half of it
  left, so a snap winner a few ticks before the calendar election is not term-limited by that win, and cannot be
  offered the act on the tick they take office.
- **The kernel rolls, once, at the election tick** with `regime_rng` (seeded from `run.seed`, checkpointed):
  `P = logistic(support_weight * (approval - 0.5) + loyalty_weight * (1 - 2 * loyalty) - severity_weight * severity)`.
  Approval is the president's own poll. `loyalty` is one scalar, the share of the state's servants who obey the
  constitution over the president (0.8 by default); the roadmap's drift with legitimacy and churn is not built yet.
- **Success**: the election is not held, the president serves another term (`term_end_tick` moves, `mandates_served`
  goes one past the limit). Irregular is derived, not stored: `mandates_served > president_term_limit`. Recalls
  (the legitimacy floor and the confidence vote) are suspended while irregular. The next fixed election is at
  the end of the extended term.
- **Failure**: the president is removed at once and the election goes ahead without them (they are already
  barred by the term limit).
- `extra_legal_act` (institutional) journals the act, the approval, the probability and the outcome.
- `regime.enabled` needs `agents.amendments` and a finite `president_term_limit`. The exploration profile turns it on.

## Not settled

- **The constants are a first guess.** At approval 0.5 and the defaults P is about 6%; at 0.9 about 40%.
- **No way out of an irregular regime yet**: no constituent process, no counter-uprising. A president who stays
  can refuse again each term.
- **No `postpone_election`, no `insurrection`**, and no citizen or chamber act. Add each when a log shows agents reaching for it.
- **Λ does not drift**, and only the president has a menu of rule-breaking.
