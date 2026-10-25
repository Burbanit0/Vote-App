# ADR-039: voters who see no difference stay home (turnout cost 0.02)

**Status**: Accepted — the scenario profile's `vote.turnout_cost` goes from 0 to 0.02 **on the deterministic engine**. The model engine keeps its own `LLM_TURNOUT_COST` (0.04); every other profile and the default (0) are unchanged.
**Date**: 2026-10-24
**Context**: After ADR-038, the catalogue of scenarios (plan-scenarios-v1, step 6) had turnout as its most frequent plausibility failure: 499 of 1,000 runs. Every one of them was **too high** (a mean turnout above the band's 0.85; none below 0.5). The band's generic European range is 0.5 to 0.85, and real turnouts run about 0.6 to 0.8.

## Cause

A voter abstains for one of two reasons on the utility ballot: anger has disengaged them (ADR-021), or their best candidate is within `turnout_cost` of the blank ballot (OBS-042; `simple_rules.abstains`). The scenario profile had `turnout_cost` at 0, so the second path never fired and nobody stayed home out of indifference. ADR-011 had found that the band needs a cost of 0.02 to 0.04 and left it at 0 because turnout and partisanship pulled against each other; partisanship is 0 in this profile, so that conflict does not arise here.

**Two earlier decisions on this cost, and why this one differs.** OBS-042's study (`scripts/calibrate_turnout_rule_results.md`) calibrated the same rule on a twin **without disengagement** against four facts at once (retrospective voting, turnout, partisanship, repeat winners) and selected 0.15; it was not adopted, because 0.15 keeps 44% home with two candidates. The model engine's `LLM_TURNOUT_COST` (0.04, `run_polity_flagship.py`) was kept on 2026-10-06 for keeping about a tenth home whatever the field's size. This ADR is narrower: the scenario profile has ADR-021's disengagement (at cost 0 it already keeps about 17% home), and the rule below targets turnout alone. It leaves the model engine's 0.04 alone, so the twin and the model arm of the scenario profile now differ in this cost (0.02 against 0.04).

## Decision

The scenario profile's `turnout_cost` is **0.02**: **the smallest cost at which at least two thirds of the runs (`DIVERGENCE_PLAUSIBLE_SHARE`) have their mean turnout inside the band.** The rule was fixed before the sweep was run, and the table it was read from prints no archetypes (`scripts/probe_turnout_cost.py`), so the choice did not see them.

| `turnout_cost` | mean turnout | runs with their mean inside the band | above it | mean volatility | volatility in band | re-election share |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (before) | 0.832 | 58% | 42% | 0.185 | 90% | 0.34 |
| 0.01 | 0.823 | 62% | 38% | 0.186 | 90% | 0.33 |
| **0.02** | **0.812** | **72%** | **28%** | **0.187** | **90%** | **0.33** |
| 0.03 | 0.801 | 80% | 20% | 0.187 | 90% | 0.33 |
| 0.04 | 0.792 | 85% | 15% | 0.187 | 90% | 0.32 |
| 0.06 | 0.771 | 90% | 10% | 0.188 | 90% | 0.32 |

(60 catalogue points, one run each; `python scripts/probe_turnout_cost.py --points 60 --out <dir>` reproduces it.) Volatility and re-election do not move: the cost removes indifferent voters, not a bloc.

## Measured: the catalogue under it

The fourth 1,000-run sweep (`python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`), read only after the choice:

- **Turnout failures fall from 499 to 332**, all still above the band; **668 of 1,000 runs (66.8%) have their mean turnout inside it**, just over the two-thirds line that the 60-point table put at 72%. The smallest cost passes the rule on the sample it was chosen on and only barely at scale; 0.03 would have more room. Not changed, since moving it now would be choosing on the large sweep.
- **Runs inside the whole plausibility band go from 228 to 342.** Panel stability (310 failures) is now nearly as frequent a failure as turnout (332).
- **The gate still holds**: four archetypes at 5% or more (alternation 60%, churn 15%, stasis 13%, realignment 11%), each with a PRIM box with lift; the negative control (`amendment_threshold`) is in no box this time.

## Not settled

- **The two engines differ** (0.02 on the twin, 0.04 on the model): a twin-to-model comparison of the scenario profile carries that difference.
- **Indifference is the same threshold for everyone.** A citizen-specific cost (habit, age, education) is the realistic shape and was not built.
- **The margin at scale is thin** (see above).
- **Earlier tables used 0**: ADR-033 to ADR-038's measurements and the scenario-profile probes ran without the cost.
