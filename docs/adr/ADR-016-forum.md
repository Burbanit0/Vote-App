# ADR-016: the forum — citizens who talk, and an agent set derived from the journal

**Status**: Accepted — built in Phase 3.1 and 3.2 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: the roadmap's goal of citizens who change their minds through talk. Opinion change itself
is Phase 3.3; this ADR is the talk.

## Decision

- **A citizen speaks if they sit in the sortition chamber or launched a petition in the last 8
  ticks.** The roadmap's 3.1 asked for a promotion rule ("consulted in 3 of the last 4 ticks"), a
  cap (`agents.max_full`), a demotion counter and agent ids in the checkpoint. None is built:
  - "consulted" has no meaning once the crowd is deterministic (D3), and a petition is the one act
    of the crowd that says "this citizen does something";
  - the 8 ticks are read from the journal (`AgentMemory.petitioned`, rebuilt on resume like the rest
    of the memory), so demotion is the window running out and the checkpoint gains nothing;
  - `agents.forum_size` (30) caps the speakers per tick, recent launchers first, then the chamber
    by id.
- **One turn a tick, run in parallel and blind.** A speaker's turn (`decide_forum`, decision type
  `forum_post`) returns a rationale, a `post` and a `note_to_self`; an empty post is silence. Every
  turn is journaled as a `forum_post` event, silent or not, so the fallback rate and the notes stay
  visible. A post reaches the others the next tick.
- **The feed is the last 8 posts a citizen can see.** They see their social-graph neighbours' posts,
  the president's and nominees' speeches (the `agent_turn` events), and, for a member of the chamber,
  the other members' posts. Never their own (OBS-028: shown their words, agents repeat them).
- **On in the exploration profile only** (`agents.forum`), and it needs the model and named issues
  like every agent.

## What this ADR does not settle

- That the talk moves anyone. Until ADR-017 a post changes no stance, so the chamber talks and still
  votes as before (OBS-004). ADR-017 (3.3) makes it move; the exposure analysis waits for a run.
- Replies, direct messages and a party caucus: the logs must show demand first.
- Scoring which posts to show. The feed is the most recent, which favours the loudest neighbour.
