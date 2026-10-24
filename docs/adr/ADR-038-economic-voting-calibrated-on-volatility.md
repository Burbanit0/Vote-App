# ADR-038: economic voting at 0.3, calibrated on legislative volatility

**Status**: Accepted — changes the scenario profile's `vote.economic_voting` from ADR-034's 1.0 to 0.3. The engine and every other profile are unchanged (the default is still 0).
**Date**: 2026-10-24
**Context**: Under ADR-037's realignment rule the catalogue of scenarios (plan-scenarios-v1, step 6) read 60% of its 1,000 runs as churn (a legislative volatility of 0.4 at some election), and the plausibility band failed volatility in 670 of them. Unlike realignment, this was not the label: the mean Pedersen volatility between consecutive legislative elections was 0.35 (the band's generic European range is 0.05 to 0.30). The owner asked for the cause and a fix.

## Cause

Measured on the same catalogue points (15 years, the rule-only twin), each time against the shipped profile:

- **Not party entry or exit.** The five parties run at every election (none founded or dissolved): the part of volatility from parties appearing or disappearing is 0.000.
- **Not the size of the electorate.** 40 points at 100 and at 400 citizens: mean volatility 0.354 and 0.365.
- **Economic voting, and nothing else tried.** One setting changed at a time on 40 points: economic voting 0 brings the mean from 0.354 to 0.103 (every run's mean inside the band, no election at 0.4); approval 0, strategic margin 0, partisanship 0.03 or 0.05 and a drift of 0.02 leave it at 0.346-0.359.

ADR-034's term adds `economic_voting * x(t)` to every voter's utility for the incumbent's and the governing parties, the same for everyone (sociotropic, and no per-citizen perception). At 1.0 it outweighs the policy differences between parties and partisanship (0.05) by about an order of magnitude, so a turn of the economy moves every marginal voter at once and the assembly swings between elections.

## Decision

The scenario profile's weight is **0.3**, the largest of the weights tried at which at least two thirds of the runs (`trajectory.DIVERGENCE_PLAUSIBLE_SHARE`) keep their mean legislative volatility inside the band. The rule uses only the band and that share, two constants already in the code; it does not read the archetypes.

| `economic_voting` | mean volatility | runs with their mean inside the band | presidential re-election share | mean turnout |
|---:|---:|---:|---:|---:|
| 0 | 0.107 | 100% | 0.38 | 0.84 |
| 0.1 | 0.121 | 97% | 0.35 | 0.83 |
| 0.2 | 0.144 | 100% | 0.33 | 0.84 |
| **0.3** | **0.185** | **90%** | **0.34** | **0.83** |
| 0.5 | 0.263 | 60% | 0.31 | 0.83 |
| 0.75 | 0.310 | 48% | 0.29 | 0.83 |
| 1.0 (ADR-034) | 0.358 | 35% | 0.28 | 0.83 |

(60 catalogue points, one run each.) The economy still costs incumbents at 0.3 (a re-election share of 0.34 against 0.38 without it), less than at 1.0. The term is linear in the weight, so a scenario's scripted recession should move the vote about a third as much as under ADR-034; that was not measured.

**Disclosed:** the same 60-point table also printed each weight's archetype counts, and at 0.3 four archetypes were above 5% of those 60 runs. I saw that before choosing. The choice follows the rule above, which 0.2 and 0.1 also pass and 0.5 does not; 0.3 is the largest that passes.

## Measured: the catalogue under it

1,000 runs (`python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`, archetype version 3):

- **The step's gate is met: four archetypes reach 5% of the runs, each with a PRIM box with lift over its base rate.** Alternation 60% (a box at 94%), churn 16% (39%), stasis 13% (34%), realignment 11% (42%). It holds at realignment thresholds of 0.25 and 0.5 spreads and not at 0.75 or 1.0.
- **Plausibility**: runs inside the whole band go from 97 to 228 of 1,000; volatility failures from 670 to 142. Turnout is now the most frequent failure (499 runs), the same order as before (467); it is not addressed here.
- **A warning about the boxes**: the negative control (`amendment_threshold`, inert on the rule-only twin) appears in the alternation box as a cut of its top 15%. With one run per point a box can carry a trim of a dimension that does nothing; read the trims of a range's edge as noise unless a ten-seed design confirms them.

## Not settled

- **Economic voting is still the same for every voter.** The cause of the swings is that homogeneity as much as the weight; a per-citizen perception of the economy (ADR-034's "not done" list) would let the weight stay larger without moving whole blocs. Not built, so as not to add a mechanism for a calibration.
- **Earlier tables used 1.0.** ADR-034's and ADR-035's tables, the scenario-profile probes (and ADR-036's, in #993) were measured at 1.0; the current profile does not reproduce them.
- **The grid is coarse** (0.3 and 0.5 bracket the two-thirds line) and the rule takes the largest grid value that passes, not an interpolated one.
