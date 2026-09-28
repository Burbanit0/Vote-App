# ADR-017: opinion change — a forum turn may move its speaker, and the crowd follows the graph

**Status**: Accepted — built in Phase 3.3 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: the roadmap's goal of citizens who change their minds. ADR-016 built the talk; this makes
it count. Builds on ADR-012 (the dynamic crowd).

## Decision

- **The forum turn carries the change of mind.** `ForumTurn` gains `shift_issue` (the issue number
  in the persona, -1 for none) and `shift_direction` (`none`, `low` or `high`). The roadmap's
  "reflection returns a `stance_update`" needs no reflection turn: an agent already reads the feed
  and their own notes when it decides, and there is no separate reflection to build.
- **The kernel bounds it.** A move is always `agents.stance_step` logit units (0.25 in the profile),
  whatever the model wrote, along that issue's loading on the latent factors
  (`opinion_dynamics.shift_stance`). Issues that load with it move too, and the FJ pull
  (`dynamics.susceptibility`) draws the citizen back toward their anchor over time. A direction
  with no issue is an invalid turn and is retried like any other.
- **The move is applied and journaled in the same phase.** `forum_post` carries `shift_issue` and
  `shift_logit` (what the kernel applied; 0 when nothing moved), so exposure and movement can be
  joined offline. The new stance reaches the citizen's next persona, and the crowd through ADR-012.
- **The crowd is dynamic in the exploration profile**: `dynamics.enabled`, `susceptibility` 0.9,
  `influence_step` 0.1 over the social graph. The agents are nodes of that graph, so their moves
  spread to their neighbours with no new code. These values are a first guess, not calibrated.
- `agents.stance_step` needs `agents.forum` and `dynamics.enabled`. At 0 (the shipped default) the
  prompt asks for no move and a stray one is ignored.

## What this ADR does not settle

- The exit test "agents exposed to counter-arguments shift more than unexposed ones". The events
  carry what it needs; the analysis waits for a run.
- A cap on the total drift over a run. The pull toward the anchor is the only brake.
- Whether an 8B model moves at all; the first run says.
