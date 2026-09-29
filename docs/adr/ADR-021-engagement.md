# ADR-021: citizens who give up

**Status**: Accepted — built in Phase 4.4 of `docs/plan/polity/plan-polity-agency-roadmap.md`.
**Date**: 2026-09-28
**Context**: A citizen far from the sitting president could only act louder (petition, mobilise) or
vote blank. The roadmap wants them able to stop taking part, and to leave.

## Decision

- **A citizen has an `engagement`**: `active`, `disengaged` or `exited` (`None`, untracked, reads as
  active). It follows the citizen's anger (ADR-012), so it needs no new appraisal and no model call.
- **Hysteresis**: an active citizen whose anger reaches `emotions.disengage_anger` is disengaged; a
  disengaged one whose anger falls to `emotions.return_anger` is active again; at
  `emotions.exit_anger` a citizen has exited for good. `disengage_anger` 0 leaves everyone active
  (today's behaviour); validation wants `return_anger < disengage_anger <= exit_anger` and emotions on.
- **What giving up costs**: a disengaged or exited citizen abstains (`utility_ballot` returns None,
  and the LLM vote skips them, so they count in `abstained`) and signs no petition. They are still
  polled, still in the graph and still drawn for the chamber.
- **Exited is a state, not a deletion**: `apply_dynamics` requires citizen ids equal to `range(n)`.
- Each tick journals `engagement_updated` (how many are disengaged, how many exited), and
  `Citizen.engagement` is checkpointed only once set.
- The exploration profile sets 0.4 / 0.2 / 0.85. On a deterministic 12-year, 200-citizen run that
  gave at most 10-17% disengaged and 6-20% exited by the end, and turnout stayed inside the twin's 50-85% band.

## Not settled

- Agents cannot choose to quit, and a disengaged agent still posts on the forum.
- Exited citizens can still be drawn for the sortition chamber; disengaged ones can still mobilise.
- The thresholds are a first guess, not calibrated.
