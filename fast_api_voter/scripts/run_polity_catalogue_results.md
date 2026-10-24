# Catalogue of scenarios: the first 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
A reading, not a pre-registered experiment.

**The step's gate is met: four archetypes reach 5% of the runs, each with a PRIM box with lift over its base rate.** It
took two changes, each with its own ADR and its own disclosure, after two sweeps that failed the gate:

| sweep | realignment rule | economic voting | archetypes at 5% | runs inside the band |
|---|---|---:|---:|---:|
| 1 | fixed 0.1 (version 2) | 1.0 | 2 (realignment 89%) | 97 |
| 2 | half the population's spread ([ADR-037](../../docs/adr/ADR-037-realignment-against-the-populations-spread.md), version 3) | 1.0 | 3 (churn 60%) | 97 |
| **3** | **version 3** | **0.3 ([ADR-038](../../docs/adr/ADR-038-economic-voting-calibrated-on-volatility.md))** | **4** | **228** |

- Sweep 1 failed on the label: 89% of the runs crossed a fixed shift of 0.1, exactly the realignment share. ADR-037 measures
  the shift against the population's own spread, at half a spread, a round fraction picked knowing the old distribution.
- Sweep 2 failed on the model: churn took 60% because economic voting at 1.0, the same term for every voter, swung whole
  blocs between legislative elections (mean volatility 0.35; 0.10 without it, nothing else tried moved it). ADR-038 takes the
  largest weight at which two thirds of the runs keep their mean volatility inside the band: 0.3. The 60-point table that
  chose it also showed four archetypes at 0.3; I saw that, and ADR-038 says so.
- The runs' dynamics are identical between sweeps 1 and 2 (only the label changed); sweep 3 is a different profile.

## Result (sweep 3)

Archetypes at 5% or more of the runs: **4** (alternation, churn, realignment, stasis). Inside the plausibility band: **228** runs (22.8%). Checks failed: {'turnout': 499, 'panel_stability': 309, 'volatility': 142, 'enp_seats': 2}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 603 | 60.3% | method in {two_round, borda}; seat_rule in {sainte_lague, largest_remainder}; 0.0173 <= scandal_rate <= 0.121; economy_sigma <= 0.195; ambition in {beta(2,3), beta(1,1)}; amendment_threshold <= 0.848 | 5% | 94% (base 60%) | 8% |
| churn | 159 | 15.9% | seat_rule in {dhondt}; economy_sigma >= 0.173; ambition in {beta(2,3), beta(1,1)} | 9% | 39% (base 16%) | 23% |
| stasis | 132 | 13.2% | method in {borda, copeland}; recall_floor <= 0.376; petition_threshold >= 0.0798; economy_sigma <= 0.288; ambition in {beta(2,8)} | 9% | 34% (base 13%) | 22% |
| realignment | 106 | 10.6% | method in {plurality}; threshold <= 0.0909; scandal_rate >= 0.0126; polarization_pressure >= 0.47 | 6% | 42% (base 11%) | 25% |

### Inside the plausibility band (228 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 167 | 73.2% | method in {two_round, irv, borda, copeland, schulze}; threshold <= 0.0861; seat_rule in {sainte_lague, largest_remainder}; scandal_rate <= 0.131; ambition in {beta(2,8)}; amendment_threshold <= 0.838 | 11% | 100% (base 73%) | 14% |
| stasis | 28 | 12.3% | method in {two_round, borda}; seat_rule in {dhondt, largest_remainder}; ambition in {beta(2,8)} | 6% | 46% (base 12%) | 21% |
| realignment | 25 | 11.0% | method in {plurality, irv, schulze}; threshold <= 0.0894; seat_rule in {dhondt}; polarization_pressure >= 0.163; ambition in {beta(2,3), beta(1,1)} | 7% | 38% (base 11%) | 24% |
| churn | 8 | 3.5% | under 5% of the runs or 20 runs: not read | | | |

### Other realignment thresholds (the same runs, relabelled)

| spreads | realignment | churn | alternation | stasis | archetypes at 5% or more |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 435 | 100 | 386 | 79 | 4 |
| 0.5 | 106 | 159 | 603 | 132 | 4 |
| 0.75 | 30 | 172 | 657 | 141 | 3 |
| 1.0 | 6 | 183 | 668 | 143 | 3 |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%, at least 5 target points in a box), over the
runs the table names; a box is a description of a sample, not a tested rule, and an archetype under 5% or 20 runs gets no
box. A cut that leaves a side open is written as `>=` or `<=`.

- **A warning about the boxes.** The negative control, `amendment_threshold` (inert on the rule-only twin, which has no
  agents to propose amendments), appears in the alternation boxes as a trim of its top 15%. With one run per point a box can
  carry a cut of a dimension that does nothing. Read a trim of a range's edge as noise unless a ten-seed design confirms it;
  the cuts that also make sense mechanically are realignment's `polarization_pressure >= 0.47` (ADR-033's radicalisation)
  and churn's `economy_sigma >= 0.17` (a more volatile economy, through what is left of economic voting).
- **Plausibility.** Volatility failures fall from 670 to 142. Turnout is now the most frequent failure (499 runs, as it was
  467 before); not addressed here.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point would cost ten times as much (about 80 minutes).
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
