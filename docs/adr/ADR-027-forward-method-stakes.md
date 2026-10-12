# ADR-027: a president weighs a voting method by the next election, not the last

**Status**: Accepted — exploration profile (owner, 2026-10-12).
**Date**: 2026-10-12
**Context**: ADR-026's method line recounted the election the president had just won, so it nearly always
said "you win under nearly every method": no reason to change. The owner wants presidents who anticipate
losing a second mandate and push for a method that would keep them. In phase13 (ADR-024 to 026 on, 5 seeds
× 8 years) presidents proposed 31 amendments and not one voting method.

## Decision

- **Today's ballots, not the last election's.** `ballots_today` builds the ballots the citizens would cast
  today if the last election's candidates stood again. It uses the utility vote (`utility_ballot`, the
  exploration profile's `vote.mode`), with the president judged on their record, on today's opinions.
  - **Platforms:** each candidate stands where `declare_candidacy` would stand them: a former officeholder
    on their conduct in office under `incumbent_keeps_record` (on in the exploration profile), anyone
    else on their own views. These are copies; no citizen's state is touched.
  - **Who:** candidates and voters who gave up are left out (ADR-021).
  - **The term limit:** a president it bars from standing again is told so beside the methods.
- **The president's own position first.** The line opens with "would elect you under: …" (or "no
  method"), then the other winners, and marks the method in force.
  - Grouped by winner, the old line buried "you" among thirteen methods. An at-risk president
    (`capped-8y-seed3`, losing under IRV, winning under plurality) proposed two-round 10 times in 10,
    which elects the rival.
- **The seat line is unchanged (ADR-026).** It stays the last legislative election re-seated.

## Measured

`check_amendment_stakes.py --at-risk` keeps presidents whom today's ballots defeat under the method in force
but elect under another: 4 of the 39 finished runs' final states (28 still win, 7 lose under every method).

| wording (4 at-risk presidents, 10 turns each, with the stakes) | method proposals | that elect the proposer |
|---|---:|---:|
| backward line (ADR-026) | 0 | – |
| forward, grouped by winner | 10 | 0 |
| forward, "you" first | 0 | – |

- **Unstable on its own:** one president's turn decides most of the column, and reruns of the same turns
  flip.
- **With ADR-028 on all 39 presidents,** 12 of 13 method proposals would elect the proposer, against 7 of
  10 without it (see ADR-028).

## Not settled

- **The field may differ.** Today's ballots assume the last election's candidates, minus those who gave
  up. Who the parties would nominate, and new rupture candidates, are not forecast.
- **The referendum counts other ballots.** It (ADR-020) still re-counts the last election's ballots, so
  a change the president proposes on today's ballots can still be referred and lost on the old ones.
- **No forecast for an LLM-cast electorate.** With `vote.mode` "llm" the citizens' ballots are the
  model's; the forecast stays the utility rule.
- **Final states only.** All the probe states are final states. The 39-president comparison ran before
  the platforms followed `declare_candidacy`; for presidents under `incumbent_keeps_record` it is the
  same platform.
