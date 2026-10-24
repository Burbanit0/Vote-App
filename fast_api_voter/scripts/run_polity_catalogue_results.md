# Catalogue of scenarios: the first 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
A reading, not a pre-registered experiment.

**The step's gate is not met: 2 archetypes reach 5% of the runs, not 4.** The sweep works (1,000 of 1,000 runs read, none
errored; PRIM runs and finds boxes), but the runs are one story: 89% read as realignment.

## Result

Archetypes at 5% or more of the runs: **2** (churn, realignment). Inside the plausibility band: **97** runs (9.7%). Checks failed: {'volatility': 670, 'turnout': 467, 'panel_stability': 309, 'enp_seats': 71}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| realignment | 890 | 89.0% | method in {plurality, two_round, irv, borda, schulze}; 0.0122 <= threshold <= 0.1; seat_rule in {dhondt}; 0.0165 <= scandal_rate <= 0.15; 0.265 <= polarization_pressure <= 1; ambition in {beta(2,8), beta(1,1)} | 11% | 100% (base 89%) | 12% |
| churn | 76 | 7.6% | method in {plurality, two_round, irv, borda, schulze}; 0 <= threshold <= 0.0902; seat_rule in {sainte_lague}; 0 <= polarization_pressure <= 0.721; ambition in {beta(2,3)} | 6% | 21% (base 8%) | 17% |
| alternation | 29 | 2.9% | below 5%: not read | | | |
| stasis | 5 | 0.5% | below 5%: not read | | | |

### Inside the plausibility band (97 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| realignment | 86 | 88.7% | method in {two_round, irv, borda, copeland, schulze}; seat_rule in {dhondt, sainte_lague}; ambition in {beta(2,8), beta(1,1)} | 36% | 100% (base 89%) | 41% |
| alternation | 8 | 8.2% | method in {plurality, irv, copeland, schulze}; seat_rule in {largest_remainder}; ambition in {beta(2,3)} | 5% | 40% (base 8%) | 25% |
| churn | 2 | 2.1% | below 5%: not read | | | |
| stasis | 1 | 1.0% | below 5%: not read | | | |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%), over the runs the table names; a box is a
description of a sample, not a tested rule. The realignment box is nearly empty of information: its density (100%) is
only 11 points above the 89% every run has. The churn box (21% against 8%) is the one with some lift, and it names the
seat rule (Sainte-Laguë), a middling ambition distribution and low electoral thresholds; read it as a lead, not a result.

## What drives the realignment share: the label, not the settings

Slicing the same 1,000 rows (the numbers are from the rows file, not from the PRIM boxes):

| polarization pressure (`dynamics.radical_step`) | runs | realignment | churn | alternation | mean shift of views | in band |
|---|---:|---:|---:|---:|---:|---:|
| 0 - 0.1 | 100 | 71% | 20% | 8% | 0.087 | 9% |
| 0.1 - 0.25 | 150 | 77% | 20% | 2% | 0.119 | 12% |
| 0.25 - 0.5 | 250 | 92% | 3% | 4% | 0.188 | 10% |
| 0.5 - 0.75 | 250 | 92% | 5% | 2% | 0.251 | 9% |
| 0.75 - 1 | 250 | 97% | 2% | 1% | 0.298 | 9% |

- **Pressure moves the share, as ADR-033 says it should** (71% to 97%), and a scandal rate above 0.03 moves churn from 14%
  down to 5-6%. But even with almost no pressure and few scandals (28 runs), 82% still read as realignment: the median
  run's mean shift is 0.156 against the label's threshold of 0.1, so nearly every 15-year run crosses it.
- **This is the finding ADR-035 recorded and did not act on**: the realignment rule asks for a shift of 0.1 in the
  Euclidean mean over twenty issues, which this profile exceeds in most runs. I did not move the threshold: choosing it to
  get four archetypes would be tuning the measure to the result. A threshold per issue, or a shift measured against the
  population's own spread, is the better rule ADR-035 pointed at; that is a decision for the owner.
- **The negative control behaves**: `amendment_threshold` appears in no box (the twin has no agents that propose
  amendments, so it is inert by construction).
- **The plausibility band is a filter that keeps about one run in ten** (97 of 1,000). The failed checks are volatility
  (670 runs), turnout (467) and panel stability (309): the same three the earlier sweeps fail.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point (the earlier sweeps' design) would cost ten times as much.
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
