# ADR-019: coalition talks between party leaders

**Status**: Accepted — built in Phase 4.2 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: the crowd's `coalition_decision` batch collapses to one answer on Qwen, Granite and
Gemma alike: every party gets the same action whatever the platforms say. The roadmap replaces it
with the parties' leaders, who take a turn each.

## Decision

- **Switched on by `agents.coalition`** (needs `llm.enabled` and `citizens.issue_count` 20, like the
  other agent turns), and ON in the exploration profile when the LLM is. Off, the crowd batch runs
  exactly as before.
- **One seam, no second negotiation.** `decide_coalition` takes a `negotiation` callable, by
  default the crowd's round loop. Everything around it is unchanged: the formateur (the party with
  most seats, ties by `tiebreak_key`), the short-circuits (a majority alone, no responder),
  `assemble_coalition`, and the journal events. `agents.negotiate_leaders` is the other callable.
- **A leader is derived, not stored.** `party_leader` is the party's most ambitious member (lowest
  id on a tie), never the leader of two parties. The roadmap's "founder or last nominee" needs a
  field in the checkpoint; this needs none, and a party that changes members changes leader.
- **Each round, every leader takes one turn** (`coalition_turn`), in parallel, none seeing another's
  answer of the same round. The prompt gives their party's platform, the three issues where the
  formateur's differs most (in words), the provisional coalition's seats against the threshold, what
  the other leaders said last round, and the leader's own memory of earlier talks.
- **The stop rule is the crowd's**: `_negotiation_converged`, which needs a prior round, so at least
  two, and `parties.coalition_max_negotiation_rounds`. A leader who never answers keeps their
  previous answer, or declines in round 1, so a failed call cannot join a coalition.
- **The words are journaled.** `coalition_decision` events carry `leader`, `statement`, `rationale`,
  `note_to_self` and `llm_fallback` (all dropped while empty). The leader's statement and note reach
  their diary and their memory of the next talks (`_own_line`).

## Not settled

- `party_leader_turn` (a leader moving the platform) waits for a run that shows platforms are too rigid.
- Whether the leaders' answers still collapse is a question for the first exploration run: read
  the `coalition_decision` events' statements before trusting the coalitions.
