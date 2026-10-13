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
  - The citizens rank the last election's candidates on today's opinions. These are the ballots ADR-027's
    stakes already forecast with (`ballots_today`): candidates stand where `declare_candidacy` would stand
    them, those who gave up are left out, and the sitting president is judged on their record.
  - Who votes is decided as at an election. A disengaged or exited citizen stays home (ADR-021), and so
    does one too indifferent to turn out (`turnout_cost`).
  - The petition threshold is counted against these ballots.
- **Only candidates who may stand again count.** A candidate the term limit bars is struck from every
  ballot: a method that would elect them elects no one. Unlike the stakes, which show the president their
  own win under each method and then say they are barred.
- **Each citizen votes for their own interest:** yes if they rank the new method's winner higher today, no
  if they rank the old method's winner higher. Nothing else enters, as at an election.
- **Unchanged from ADR-020:**
  - only the voting method is referred;
  - `never`, `petition` and `always`;
  - not held when both methods elect the same person;
  - passed on strictly more yes than no.
- **Without a sitting president,** no record is weighed.

## Measured

On the final states of the 25 finished exploration runs (phases 11–14), each of the 12 other methods was
put against the one in force, under the exploration profile's `petition` mode: 300 changes.

| | recount (ADR-020) | new vote |
|---|---:|---:|
| referendums held | 127 | 108 |
| changes refused | 23 | 8 |

- **The verdict differs in 31 of the 300.**
  - 23 changes the recount refused would stand: today both methods elect the same person.
  - 8 the recount let stand are refused.
- **Which changes are referred moves more than how many.**
  - 78 pairs of methods elected different people at the last election and no longer do: opinions have
    moved, and candidates have since given up.
  - 43 go the other way, mostly because a barred president is struck.

## Not settled

- **The crowd votes by rule, not by the model,** whatever `vote.mode` is. That is the exploration profile's
  election vote. A run that casts elections with the model (no profile amends today) would hold
  referendums on a different electorate model. The agents are not asked separately.
- **Nothing is journaled when there is nothing to vote on.** That happens when no candidate of the last
  election still takes part, or no one would turn out: the chamber's ratification stands, as it did
  before any election.
- **Only the candidates of the last election stand.** Who would be nominated next time is not forecast.
- **Other articles are still ratified by the chamber alone.** A threshold or a founding ratio has no winner
  to compare, and OBS-048's founding-ratio cuts were never put to the citizens.
