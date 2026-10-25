# Catalogue of scenarios: four sweeps of 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
A reading, not a pre-registered experiment.

**The step's gate is met: four archetypes reach 5% of the runs, each with a PRIM box with lift over its base rate.** It
took two changes, each with its own ADR and its own disclosure, after two sweeps that failed the gate; a third
(ADR-039) then fixed the most frequent plausibility failure, turnout:

| sweep | realignment rule | profile | archetypes at 5% | runs inside the band |
|---|---|---:|---:|---:|
| 1 | fixed 0.1 (version 2) | economic voting 1.0 | 2 (realignment 89%) | 97 |
| 2 | half the population's spread ([ADR-037](../../docs/adr/ADR-037-realignment-against-the-populations-spread.md), version 3) | economic voting 1.0 | 3 (churn 60%) | 97 |
| 3 | version 3 | economic voting 0.3 ([ADR-038](../../docs/adr/ADR-038-economic-voting-calibrated-on-volatility.md)) | 4 | 228 |
| **4** | **version 3** | **economic voting 0.3, and a turnout cost of 0.02 ([ADR-039](../../docs/adr/ADR-039-turnout-cost.md))** | **4** | **342** |

- Sweep 1 failed on the label: 89% of the runs crossed a fixed shift of 0.1, exactly the realignment share. ADR-037 measures
  the shift against the population's own spread, at half a spread, a round fraction picked knowing the old distribution.
- Sweep 2 failed on the model: churn took 60% because economic voting at 1.0, the same term for every voter, swung whole
  blocs between legislative elections (mean volatility 0.35; 0.10 without it, nothing else tried moved it). ADR-038 takes the
  largest weight at which two thirds of the runs keep their mean volatility inside the band: 0.3. The 60-point table that
  chose it also showed four archetypes at 0.3; I saw that, and ADR-038 says so.
- Sweep 3 left turnout as the most frequent band failure (499 runs, all above 0.85): the profile had no indifference
  abstention. ADR-039 adds a turnout cost of 0.02, the smallest at which two thirds of the runs keep their mean turnout
  inside the band, chosen from a table that prints no archetypes; at scale 66.8% do, barely over the line.
- The runs' dynamics are identical between sweeps 1 and 2 (only the label changed); sweeps 3 and 4 are different profiles.

## Result (sweep 4)

Archetypes at 5% or more of the runs: **4** (alternation, churn, realignment, stasis). Inside the plausibility band: **342** runs (34.2%). Checks failed: {'turnout': 332, 'panel_stability': 310, 'volatility': 138, 'enp_seats': 2}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 604 | 60.4% | method in {irv, borda}; threshold <= 0.0896; seat_rule in {dhondt, largest_remainder}; scandal_rate <= 0.135; economy_sigma <= 0.214 | 11% | 85% (base 60%) | 16% |
| churn | 154 | 15.4% | seat_rule in {dhondt}; economy_sigma >= 0.167; ambition in {beta(2,3), beta(1,1)} | 10% | 34% (base 15%) | 23% |
| stasis | 134 | 13.4% | method in {copeland}; scandal_rate >= 0.018; ambition in {beta(2,8)} | 5% | 32% (base 13%) | 12% |
| realignment | 108 | 10.8% | method in {plurality}; threshold <= 0.0894; recall_floor >= 0.128; economy_sigma >= 0.082; polarization_pressure >= 0.406 | 6% | 40% (base 11%) | 24% |

### Inside the plausibility band (342 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 259 | 75.7% | method in {two_round, irv, schulze}; threshold <= 0.0807; seat_rule in {largest_remainder}; scandal_rate <= 0.129 | 8% | 100% (base 76%) | 11% |
| stasis | 45 | 13.2% | method in {two_round, borda}; seat_rule in {dhondt, largest_remainder}; petition_threshold <= 0.368; polarization_pressure >= 0.261; ambition in {beta(2,8)} | 5% | 44% (base 13%) | 18% |
| realignment | 24 | 7.0% | method in {plurality, schulze}; threshold <= 0.0816; seat_rule in {dhondt} | 9% | 20% (base 7%) | 25% |
| churn | 14 | 4.1% | under 5% of the runs or 20 runs: not read | | | |

### Other realignment thresholds (the same runs, relabelled)

| spreads | realignment | churn | alternation | stasis | archetypes at 5% or more |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 438 | 97 | 387 | 78 | 4 |
| 0.5 | 108 | 154 | 604 | 134 | 4 |
| 0.75 | 33 | 169 | 653 | 145 | 3 |
| 1.0 | 6 | 179 | 666 | 149 | 3 |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%, at least 5 target points in a box), over the
runs the table names; a box is a description of a sample, not a tested rule, and an archetype under 5% or 20 runs gets no
box. A cut that leaves a side open is written as `>=` or `<=`.

- **A warning about the boxes.** The negative control, `amendment_threshold` (inert on the rule-only twin, which has no
  agents to propose amendments), appeared in sweep 3's alternation boxes as a trim of its top 15% (it is in no box in sweep 4). With one run per point a box can
  carry a cut of a dimension that does nothing. Read a trim of a range's edge as noise unless a ten-seed design confirms it;
  the cuts that also make sense mechanically are realignment's `polarization_pressure >= 0.41` (ADR-033's radicalisation)
  and churn's `economy_sigma >= 0.167` (a more volatile economy, through what is left of economic voting).
- **Plausibility.** Volatility failures fell from 670 to 142 (sweep 3) and turnout failures from 499 to 332 (sweep 4).
  Turnout (332) and panel stability (310) are now the two most frequent failures.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point would cost ten times as much (about 80 minutes).
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
