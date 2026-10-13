# ADR-029: a referendum is a new vote, each citizen for their own interest

**Status**: Accepted — amends ADR-020's count (owner, 2026-10-13).
**Date**: 2026-10-13
**Context**: ADR-020's referendum did not ask anyone. It recounted the last presidential election's
ballots under the old and the new method, and listed "stale ballots" as unsettled. In phase14 a change
to plurality was refused 40-51 and then 24-56, on the ballots of the last election (OBS-048). The owner: "A
referendum is a new vote asking everyone yes or no, not based on the previous vote. Everyone should
defend their interest."

## Decision

- **The referendum is cast when it is held.**
  - Every engaged citizen ranks the last election's candidates on today's opinions. A disengaged or exited
    citizen stays home, as at every vote (ADR-021).
  - These are the ballots ADR-027's stakes already forecast with (`ballots_today`). The candidates stand
    where `declare_candidacy` would stand them, those who gave up are left out, and the sitting president
    is judged on their record.
- **Each citizen votes for their own interest:** yes if the new method's winner is the one they rank higher
  today, no if the old method's winner is. Nothing else enters, as at an election.
- **Unchanged from ADR-020:**
  - only the voting method is referred;
  - `never`, `petition` and `always`, with the petition counted on the same new ballots;
  - not held when both methods elect the same person;
  - passed on strictly more yes than no.
- **Without a sitting president,** no record is weighed.

## Measured

On the final states of the 25 finished exploration runs (phases 11–14), each of the 12 other methods was
put against the one in force, under the exploration profile's `petition` mode: 300 changes.

| | recount (ADR-020) | new vote |
|---|---:|---:|
| referendums held | 127 | 53 |
| changes refused | 23 | 7 |

- **The verdict differs in 30 of the 300.**
  - 23 changes the recount refused would stand: today both methods elect the same person, so there is
    nothing to refer.
  - 6 the recount passed are refused.
  - 1 the recount would not have held is refused.
- **Most of the drop in referendums** comes from the same convergence: on today's ballots, 92 of the
  pairs that elected different people at the last election no longer do. The ballots drop the candidates
  who have since given up, and opinions have moved.

## Not settled

- **The crowd votes by rule, not by the model,** as in elections (the exploration profile's utility vote).
  The agents are not asked separately, and an LLM-cast electorate is not polled.
- **Only the candidates of the last election stand.** Who would be nominated next time is not forecast.
- **Other articles are still ratified by the chamber alone.** A threshold or a founding ratio has no winner
  to compare, and OBS-048's founding-ratio cuts were never put to the citizens.
