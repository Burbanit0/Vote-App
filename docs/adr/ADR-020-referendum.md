# ADR-020: a referendum on a voting-method change

**Status**: Accepted — built in Phase 4.3 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: ADR-015's chamber can change how the president is elected by itself. The roadmap wants
the citizens able to stop that, with a vote counted on what the change would have done.

## Decision

- **One article, `constitution.referendum`**: `never` (the chamber alone decides, today's rule),
  `petition`, or `always`. It is amendable like the others.
- **Only the voting method is referred.** It is the one article whose effect can be counted without
  a model of the future: the last election's ballots are re-counted under the old and the new
  method (`get_presidential_winner`, `amendments.referendum_count`). The other articles are
  ratified by the chamber alone, whatever the mode.
- **A citizen votes yes if their own ballot ranks the new method's winner above the old one's, no if
  the reverse**; a ballot that ranks them equally, or names neither, abstains. This needs no
  utility and no agent turn: the ballot is the citizen's stated preference.
- **When it is held**: always in `always`; in `petition` when the citizens who would vote no reach
  `petition.signature_threshold` of the ballots (they are the signers of the initiative). Not held,
  the chamber's ratification stands. It is also not held when both methods elect the same person:
  the change would have altered nothing.
- **It passes on strictly more yes than no**, and is journaled as `referendum_held` (trigger
  `required` or `petition`, the counts, `passed`), an institutional event. A rejected change is
  dropped like one the chamber refused: `amendment_resolved` then carries `ratified: 0`.
- **The ballots are state.** `TickState.last_ballots` keeps the last election's ballots while
  `agents.amendments` is on and is checkpointed only then (a run that does not amend checkpoints
  as before). A referendum before any election has left ballots is not held.
- The exploration profile sets `petition`. Scripted amendments are an experiment's own and are
  never referred.

## Not settled

- The agents do not vote in it: the crowd's ballots decide. The chamber has already voted.
- A petition against other articles, or against a bill. Add it when a run shows agents amending
  articles the citizens visibly oppose.
- Stale ballots: the count is of the last election, not of today's opinions.
