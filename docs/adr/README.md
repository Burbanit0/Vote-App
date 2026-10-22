# Architecture decision records

One file per binding decision, with the alternatives that were rejected. ADRs are numbered in the
order they were written. Each file's own `**Status**` line is authoritative; this index summarises
it. For the decisions in context, see [`docs/overview/`](../overview/README.md); for their history,
the [journal](../journal/JOURNAL_DE_BORD.md) and the pull requests each ADR cites.

Area: **app** (Vote Lab), **polity** (the simulator's model), **LLM** (serving and inference).

| ADR | Decision | Area | Date | Status |
|---|---|---|---|---|
| [001](ADR-001-serving-layer-ollama-vs-llama-server.md) | Stay on Ollama, not native llama-server (later superseded in practice by the move to vLLM: [`plan-vllm-switch-readiness.md`](../plan/polity/plan-vllm-switch-readiness.md)) | LLM | 2026-08-19 | Accepted |
| [002](ADR-002-ambition-threshold-blocks-candidacy.md) | `ambition_threshold` 0.7 → 0.30: the shipped candidacy config could not hold an election | polity | 2026-08-29 | Accepted (calibrated) |
| [003](ADR-003-ballot-access-filter-is-inert.md) | The ballot-access filter is inert on both candidacy paths | polity | 2026-08-29 | Resolved |
| [004](ADR-004-dual-voting-engine-with-parity-lock.md) | Two voting engines (client and backend), locked identical by a golden-fixture parity test | app | 2026-06-27 | Adopted (FR) |
| [005](ADR-005-svg-native-core-recharts-for-exploration-only.md) | Native SVG for the always-mounted views; Recharts only in on-demand panels | app | 2026-05-23 | Adopted (FR) |
| [006](ADR-006-playground-single-five-moment-instrument.md) | One 5-moment Playground instrument, not a gallery of pages | app | 2026-06-15 | Adopted (FR) |
| [007](ADR-007-no-authentication-stateless-anonymous-app.md) | No accounts, no authentication: the app is anonymous and stateless | app | 2026-07-06 | Adopted (FR) |
| [008](ADR-008-law-system-seam-bounds-and-comparability.md) | The law system: seam, bounded amendment, comparability | polity | 2026-09-11 | Proposed (design only) |
| [009](ADR-009-ordinary-legislation.md) | Ordinary legislation: a policy status quo, bills, the chamber's suspensive veto | polity | 2026-09-13 | Accepted |
| [010](ADR-010-phase-clock-and-campaign-windows.md) | The phase clock and campaign windows | polity | 2026-09-13 | Accepted |
| [011](ADR-011-utility-vote-with-turnout.md) | The utility vote, with turnout and an LLM audit sample | polity | 2026-09-13 | Accepted |
| [012](ADR-012-dynamic-citizens.md) | Dynamic citizens: opinion dynamics and emotions | polity | 2026-09-13 | Accepted |
| [013](ADR-013-canvas-2d-for-dense-point-clouds.md) | Canvas 2D for dense point clouds, a bounded exception to ADR-005 | app | 2026-09-15 | Adopted (FR) |
| [014](ADR-014-agent-tier.md) | The agent tier: citizens the model plays in the first person | polity | 2026-09-28 | Accepted |
| [015](ADR-015-typed-constitution.md) | A typed constitution: amendable articles over the founding config | polity | 2026-09-28 | Accepted |
| [016](ADR-016-forum.md) | The forum: citizens who talk | polity | 2026-09-28 | Accepted |
| [017](ADR-017-opinion-change.md) | Opinion change: a forum turn may move its speaker | polity | 2026-09-28 | Accepted |
| [018](ADR-018-mutable-parties.md) | Mutable parties: join, leave, found; a party too small is dissolved | polity | 2026-09-28 | Accepted |
| [019](ADR-019-leader-coalition.md) | Coalition talks between party leaders | polity | 2026-09-28 | Accepted |
| [020](ADR-020-referendum.md) | A referendum on a voting-method change | polity | 2026-09-28 | Accepted |
| [021](ADR-021-engagement.md) | Citizens who give up (engagement) | polity | 2026-09-28 | Accepted |
| [022](ADR-022-extra-legal-acts.md) | A president who refuses to leave | polity | 2026-09-30 | Accepted |
| [023](ADR-023-campaigning.md) | Campaigning | polity | 2026-10-02 | Accepted |
| [024](ADR-024-strategic-voting.md) | Strategic voting at legislative elections | polity | 2026-10-10 | Accepted (exploration profile; parked by D11) |
| [025](ADR-025-majority-recall.md) | A recall needs the population against the president | polity | 2026-10-11 | Accepted (exploration profile) |
| [026](ADR-026-amendment-stakes.md) | The president knows what a rule change would do | polity | 2026-10-11 | Accepted (exploration profile) |
| [027](ADR-027-forward-method-stakes.md) | A voting method is weighed by the next election, not the last | polity | 2026-10-12 | Accepted (exploration profile) |
| [028](ADR-028-ambition-shapes-the-presidents-goal.md) | A president's goal follows their ambition (supersedes roadmap D8) | polity | 2026-10-12 | Accepted |
| [029](ADR-029-referendum-is-a-new-vote.md) | A referendum is a new vote, each citizen for their own interest (amends ADR-020) | polity | 2026-10-13 | Accepted |
| [030](ADR-030-field-order-is-part-of-the-prompt.md) | The order of a schema's fields is part of the prompt, chosen by measurement | polity | 2026-10-19 | Accepted |
| [033](ADR-033-radicalisation.md) | Radicalisation: once events have shaken the polity, angry citizens step away from the president (scenario profile) | polity | 2026-10-21 | Accepted (scenario profile) |
| [034](ADR-034-economic-voting-and-scripted-events.md) | Voters judge the economy (scenario profile), and a scenario names its crises (`events.scripted`) | polity | 2026-10-22 | Accepted (scripted events everywhere; economic voting in the scenario profile) |

Also in this folder, not ADRs:

- [`BACKLOG-alternatives.md`](BACKLOG-alternatives.md): options already evaluated and set aside (FR).
- [`v3-readiness-checklist.md`](v3-readiness-checklist.md): what to verify before moving Polity
  from 100 to 1000 citizens (an open gate).

Dates: the ADR's own `Date` line. ADR-005's is the date of the first Recharts chunking it records.
