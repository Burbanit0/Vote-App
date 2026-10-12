# ADR-028: a president's goal follows their ambition

**Status**: Accepted — supersedes decision D8's single goal for the president (owner, 2026-10-12).
**Date**: 2026-10-12
**Context**: D8 gave every president the same implicit goal: "You want to govern by your convictions and to
keep office; how you weigh the two is yours to decide." The owner: like any person, a president may put their
own interest before the country's, for any reason, and then anticipates where opinion is heading and acts on
it. Every citizen already has an `ambition_score`, the drive for office that decides who runs. Every persona
showed it as a bare number ("ambition from 0 to 1: 0.24"), with no scale (contract C3).

## Decision

- **The goal comes from ambition** (`agents.president_goal`):
  - **0.4 and above:** "Keeping office matters more to you than your convictions or the country's interest,
    and you watch where opinion is heading so as not to be caught out by it."
  - **0.2 to 0.4:** D8's sentence.
  - **Below 0.2:** "Your convictions and the country's interest matter more to you than keeping office."
- **The bands come from the population.** 0.4 and 0.2 sit at about the population's 92nd and 70th
  percentiles (phase13: median 0.16, max 0.68). Presidents run from 0.07 to 0.62, so all three bands
  hold.
- **Ambition gets its scale in every persona:** "high: few citizens want office as much as you do",
  "moderate: more than most citizens", "low, like most citizens'".
- **A motive (C1), never an act (C4).** No goal names an amendment or any other act; a test holds it.

## Measured

`check_amendment_stakes.py` on the 39 sitting presidents of every finished exploration run, 3 turns each
(117 per cell), with ADR-026/027's stakes. Before is fb819f76; after is this commit. By band, 5 presidents
are high, 26 middle and 8 low.

| with the stakes | before | after |
|---|---:|---:|
| high-ambition turns with a proposal | 7 of 15 | 12 of 15 |
| low-ambition turns with a proposal | 12 of 24 | 6 of 24 |
| voting-method proposals | 10 | 13 |
| … that would elect the proposer at the next election | 7 of 10 | 12 of 13 |
| term-limit extensions | 3 | 10 |

The reasons now say the self-interest outright: "To ensure re-election by simplifying the electoral
process", "Extend my term limit to secure re-election", "Lowering the threshold would reduce the risk of
confidence votes, safeguarding my re-election prospects".

## Not settled

- **Thin samples:** five high-ambition presidents, final states, a few turns each.
- **Ambition is static.** Power does not grow it.
- **Only the president's goal changed.** Nominees and party leaders keep their own sentences.
- **The scale reaches every agent, unmeasured.** It sits in `persona`, which nominees, forum posters,
  chamber members and party leaders share. None of their behaviour has been probed under it.
