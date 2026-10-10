# ADR-024: strategic voting at legislative elections

**Status**: Accepted — built in the exploration profile; parked in decision D11 of
`docs/plan/polity/plan-polity-agency-roadmap.md` as the lever for fragmentation.
**Date**: 2026-10-10
**Context**: Every legislative vote was sincere: `choose_party` gives each citizen their nearest
party, or a blank. Nothing in the vote looked at whether that party could win a seat, so a citizen
backing a party bound to fall under the electoral threshold wasted the vote every time. In the
literature that waste is what holds the number of parties down (Duverger; Cox 1997, *Making Votes
Count*), and D11 reports the effective number of parties rather than gating on it because this model
lacked it. The founders do not supply it either: told the seat threshold, they found at the same
rate whatever it is (OBS-045). At the end of phase11, 3 to 75 of each seed's roughly 80 party votes
went to parties below the threshold.

## Decision

- **The wasted vote, at legislative elections only.** A voter whose sincere party falls below the
  electoral threshold votes instead for the best party above it, when that costs them at most
  `vote.strategic_margin` in utility and the party is still within their tolerance
  (`blank_threshold`). A blank ballot, a party above the threshold, or a margin of 0 leaves the
  sincere choice (`simple_rules.strategic_party`).
- **The poll is the sincere vote itself.** `simple_rules.viable_parties` measures the threshold as
  `allocate_seats` does: a share of the votes cast for parties, blanks left out, at least one vote.
  It is one round, with no iteration toward an equilibrium: voters react to the sincere vote, not to
  each other's desertions.
- **Utility is `choose_party`'s own.** That is the distance, plus the governing parties' policy gain
  when `policy_retrospection` is on, so the strategic vote never disagrees with the sincere one about
  which party a voter prefers. Only the threshold enters.
- **`vote.strategic_margin`** is the one knob (0 = the sincere vote, every run before this). The
  exploration profile sets **0.07**, the median cost of deserting to the 377 voters stranded with a
  viable party within reach in phase11's final populations (deciles 10/50/90: 0.01, 0.072, 0.21,
  against a median tolerance of 0.36 in seed 1's population). About half of them desert.
- `legislative_result` journals `deserted`, the number of voters who changed party, while the margin
  is above 0.

## Measured

Applied once to phase11's final populations, with each seed's threshold and seat method in force at
the end and its engaged voters only (OBS-046):

| | sincere | strategic (0.07) |
|---|---:|---:|
| voters who deserted, median of 10 seeds | – | 20 (2 to 28) |
| effective parties by votes, median | 18.86 | **11.02** |
| effective parties by seats, median | 7.58 | 7.33 |
| inside 1.5–8 by seats | 7 of 10 | 7 of 10 |

The vote consolidates, and the assembly barely moves. Parties below the threshold already held no
seats, so a deserter moves a vote from a party with no seats to one that has some, and the seat
shares among the parties that clear the bar change little.

## Not settled

- **The dynamic channel is not modelled.** Duverger's mechanical effect is the threshold, which the
  seat allocation already applies. His psychological effect works over elections: parties that win no
  votes lose members and stop being founded. Here membership and founding do not see the vote
  (OBS-045), so a deserted party lives on. Whether that changes the count over a run needs a run.
- **No presidential counterpart.** Strategic ranking depends on the presidential method, one of 13
  ranked rules, and is left out.
- **One round.** Voters react to the sincere vote, not to each other.
- **The margin is a first guess,** calibrated on one ensemble's final populations, not on an
  observed rate of strategic voting.
