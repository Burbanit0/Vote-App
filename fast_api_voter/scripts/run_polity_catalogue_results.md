# Catalogue of scenarios: the first 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
Run twice: the two sweeps agree on the archetype and the failed checks of all 1,000 points. A reading, not a
pre-registered experiment.

**The step's gate is not met: 2 archetypes reach 5% of the runs, not 4.** The sweep works (1,000 of 1,000 runs read, none
errored; PRIM runs and finds boxes), but the runs are one story: 89% read as realignment.

## Result

Archetypes at 5% or more of the runs: **2** (churn, realignment). Inside the plausibility band: **97** runs (9.7%). Checks failed: {'volatility': 670, 'turnout': 467, 'panel_stability': 309, 'enp_seats': 71}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| realignment | 890 | 89.0% | method in {plurality, two_round, irv, borda, schulze}; threshold >= 0.0122; seat_rule in {dhondt}; scandal_rate >= 0.0165; polarization_pressure >= 0.265; ambition in {beta(2,8), beta(1,1)} | 11% | 100% (base 89%) | 12% |
| churn | 76 | 7.6% | method in {plurality, two_round, irv, borda, schulze}; threshold <= 0.0902; seat_rule in {sainte_lague}; polarization_pressure <= 0.721; ambition in {beta(2,3)} | 6% | 21% (base 8%) | 17% |
| alternation | 29 | 2.9% | under 5% of the runs or 20 runs: not read | | | |
| stasis | 5 | 0.5% | under 5% of the runs or 20 runs: not read | | | |

### Inside the plausibility band (97 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| realignment | 86 | 88.7% | method in {two_round, irv, borda, copeland, schulze}; seat_rule in {dhondt, sainte_lague}; ambition in {beta(2,8), beta(1,1)} | 36% | 100% (base 89%) | 41% |
| alternation | 8 | 8.2% | under 5% of the runs or 20 runs: not read | | | |
| churn | 2 | 2.1% | under 5% of the runs or 20 runs: not read | | | |
| stasis | 1 | 1.0% | under 5% of the runs or 20 runs: not read | | | |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%, at least 5 target points in a box), over the
runs the table names; a box is a description of a sample, not a tested rule, and an archetype with fewer than 20 runs gets
no box. A cut that leaves a side open is written as `>=` or `<=`. The realignment box is nearly empty of information: its
density (100%) is only 11 points above the 89% every run has. The churn box (21% against 8%) is the one with some lift,
and it names the seat rule (Sainte-Lague), a middling ambition distribution and low electoral thresholds; read it as a
lead, not a result.

## What drives the realignment share: the label, not the settings

The realignment rule is "the population's mean moved 0.1 or more from the first census at some census"
(`trajectory._is_realignment`, the largest `mean_shift` of the run). In these 1,000 runs **89% have a largest shift of
0.1 or more, which is exactly the realignment share**: the label is the threshold. Slicing the same rows (the numbers are
from the rows file, not from the PRIM boxes):

| polarization pressure (`dynamics.radical_step`) | runs | realignment | churn | alternation | median largest shift |
|---|---:|---:|---:|---:|---:|
| 0 - 0.1 | 100 | 71% | 20% | 8% | 0.124 |
| 0.1 - 0.25 | 150 | 77% | 20% | 2% | 0.137 |
| 0.25 - 0.5 | 250 | 92% | 3% | 4% | 0.193 |
| 0.5 - 0.75 | 250 | 92% | 5% | 2% | 0.236 |
| 0.75 - 1 | 250 | 97% | 2% | 1% | 0.269 |

- **Pressure moves the share, as ADR-033 says it should** (71% to 97%), and a scandal rate above 0.03 moves churn from 14%
  down to 5-6%. But even with almost no pressure (below 0.1) the median run's largest shift is 0.124, over the rule's 0.1,
  and with almost no pressure and few scandals (28 runs) 82% still read as realignment. The tenth percentile of the
  largest shift over all runs is 0.097: nearly every 15-year run crosses the line.
- **This is the finding ADR-035 recorded and did not act on**: a shift of 0.1 in the Euclidean mean over twenty issues is
  exceeded in most runs of this profile. I did not move the threshold: choosing it to get four archetypes would be tuning
  the measure to the result. A threshold per issue, or a shift measured against the population's own spread, is the better
  rule ADR-035 pointed at; that is a decision for the owner.
- **The negative control behaves**: `amendment_threshold` appears in no box (the twin has no agents that propose
  amendments, so it is inert by construction).
- **The plausibility band is a filter that keeps about one run in ten** (97 of 1,000). The failed checks are volatility
  (670 runs), turnout (467) and panel stability (309): the same three the earlier sweeps fail.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point (the earlier sweeps' design) would cost ten times as much (about 80 minutes).
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
