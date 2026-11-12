# ADR-037: a realignment is a shift against the population's own spread

**Status**: Accepted — the owner chose to change the rule (2026-10-24); `ARCHETYPE_VERSION` 3.
**Date**: 2026-10-24
**Context**: ADR-035 recorded that the realignment rule (the population's mean moved 0.1 or more from the first census, Euclidean over twenty issues) fired on most runs of the scenario profile and left it alone, "so as not to tune the measure to its result". The catalogue of scenarios (plan-scenarios-v1, step 6) then ran 1,000 points of a Latin hypercube over ten settings: **89% of the runs read as realignment, which is exactly the share whose largest shift reached 0.1**, and 71% still did with almost no polarization pressure. The step's gate (at least four archetypes with a non-trivial frequency) could not be judged on a label that does not discriminate. ADR-035 had named the better rule: a shift measured against the population's own spread.

## Decision

`trajectory.REALIGNMENT_SPREADS = 0.5` replaces `REALIGNMENT_SHIFT = 0.1`. A block is a **realignment** when the largest `mean_shift` of its censuses, divided by the `dispersion` of the block's first census, is at least 0.5. `dispersion` is the standard deviation of the citizens' scores along the population's first principal axis, so the unit is "one standard deviation of where the population stood, along its main axis, when the block began" and the threshold is **half of it**. A first census narrower than 0.01 (positions run from 0 to 1) or with no spread cannot be measured against, so it never realigns. `largest_relative_shift` is the one function the rule and the catalogue's rows both call. `archetype_version` is 3, written to every digest as before and now also to the catalogue's `settings.json`, so a sweep written under other rules is not resumed into.

**The threshold is a round fraction, not a derived one, and not pre-registered.** I first described it as a "medium effect (Cohen's d)", which it is not: the numerator is the Euclidean norm of the mean's displacement over twenty issues (which two latent factors drive, so the population is nearly two-dimensional) and the denominator is the spread along one axis, so the ratio is not a univariate effect size. I also knew the old distribution when I picked 0.5 (the largest absolute shift had a median of 0.14 and the first census's spread a median of 0.82, so the median run moved about 0.24 spreads), so 0.5 was never going to label most runs. The sensitivity below is the evidence on offer, and the reader should judge 0.5 by it. A consistent multivariate unit (the root-mean-square distance of the citizens from their mean, the same norm as the numerator) would be tidier and would need its own threshold; it was not built, so as not to start a second round of choosing one.

Nothing else in the rules moves. In particular the other eight rules, the block-by-block reading (ADR-035) and the plausibility band are as they were, and a run's dynamics are unchanged: the 1,000 catalogue runs had the same turnout and the same office holders under both labels.

## Measured

The catalogue's 1,000 runs (`scripts/run_polity_catalogue.py`, 15 years, 100 citizens, the rule-only twin; the first five rules never fired, so a run can be relabelled at another threshold from the stored largest relative shift, the largest volatility and the alternations). Relabelling at 0.5 reproduces the labels of the run under version 3 exactly (1,000 of 1,000); `catalogue.relabel` does it and `run_polity_catalogue.py report` prints the table.

| `REALIGNMENT_SPREADS` | realignment | churn | alternation | stasis | archetypes at 5% or more | entropy |
|---:|---:|---:|---:|---:|---:|---:|
| 0.1 in issue units (version 2) | 890 | 76 | 29 | 5 | 2 | 0.62 bits |
| 0.25 | 462 | 363 | 151 | 24 | 3 | 1.59 |
| **0.5** | **138** | **603** | **219** | **40** | **3** | **1.50** |
| 0.75 | 41 | 678 | 238 | 43 | 2 | 1.26 |
| 1.0 | 7 | 705 | 244 | 44 | 2 | 1.10 |

- **The label now discriminates.** At 0.5, realignment is 14% of the runs and is explained by something: a PRIM box with `polarization_pressure >= 0.45` holds it at 41% against a base of 14% (it was a box with 100% density at an 89% base, no information).
- **It does not give four archetypes at any threshold tried.** Stasis never exceeds 4.4% and is 4.0% at 0.5; with the threshold for "non-trivial" at 5% the count is 3 at 0.25 and 0.5 and 2 beyond. The gate is not met by this change, and the 5% cutoff is my reading of "non-trivial", which the plan does not number.
- **The bottleneck moved to churn.** A volatility of 0.4 in any legislative election now labels 60% of the runs. It is another fixed threshold of the same kind, and I did not touch it: a second retune to reach four would be tuning the measure to the gate.

## Not settled

- **Earlier tables are version 2.** ADR-033, ADR-034 and ADR-035 report archetypes and entropy under the fixed 0.1; the code that produced them is the one before this change, so those tables are not reproduced by the current rules (the sweeps' run dynamics are unchanged; only the labels differ). They are left as written.
- **Churn at 0.4 and the other thresholds** (`CHURN_VOLATILITY`, `ALTERNATION_COUNT`) have the same shape of problem and are open.
- **The unit is the first census's spread of a block**, not the whole run's, so a long run's blocks each reset it; a population whose spread itself collapses or grows reads shifts against the starting width, not the current one.
