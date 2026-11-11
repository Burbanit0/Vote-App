# Catalogue of scenarios: five sweeps of 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
A reading, not a pre-registered experiment. That command reproduces sweep 5 only; the earlier sweeps need the code they ran
on: sweep 1 at commit 7c1d3a3e, sweep 2 at 5c6c3133, sweep 3 at 3c4760a0 (the merge of #995) and sweep 4 at fe7b1a1 (the merge of #999).

**The step's gate is met: four archetypes reach 5% of the runs, each with a PRIM box with lift over its base rate.** It
took two changes, each with its own ADR and its own disclosure, after two sweeps that failed the gate; a third
(ADR-039) then fixed the most frequent plausibility failure, turnout:

| sweep | realignment rule | profile | archetypes at 5% | runs inside the band |
|---|---|---|---:|---:|
| 1 | fixed 0.1 (version 2) | economic voting 1.0 | 2 (realignment 89%) | 97 |
| 2 | half the population's spread ([ADR-037](../../docs/adr/ADR-037-realignment-against-the-populations-spread.md), version 3) | economic voting 1.0 | 3 (churn 60%) | 97 |
| 3 | version 3 | economic voting 0.3 ([ADR-038](../../docs/adr/ADR-038-economic-voting-calibrated-on-volatility.md)) | 4 | 228 |
| 4 | version 3 | economic voting 0.3, and a turnout cost of 0.02 ([ADR-039](../../docs/adr/ADR-039-turnout-cost.md)) | 4 | 342 |
| **5** | **version 3** | **as 4, with the leader rule and step as two more dimensions ([ADR-040](../../docs/adr/ADR-040-party-leaders-move-their-platform.md); other points)** | **4** | **308** |

- Sweep 1 failed on the label: 89% of the runs crossed a fixed shift of 0.1, exactly the realignment share. ADR-037 measures
  the shift against the population's own spread, at half a spread, a round fraction picked knowing the old distribution.
- Sweep 2 failed on the model: churn took 60% because economic voting at 1.0, the same term for every voter, swung whole
  blocs between legislative elections (mean volatility 0.35; 0.10 without it, nothing else tried moved it). ADR-038 takes the
  largest weight at which two thirds of the runs keep their mean volatility inside the band: 0.3. The 60-point table that
  chose it also showed four archetypes at 0.3; I saw that, and ADR-038 says so.
- Sweep 3 left turnout as the most frequent band failure (499 runs, all above 0.85): the profile had no indifference
  abstention. ADR-039 adds a turnout cost of 0.02, the smallest at which two thirds of the runs keep their mean turnout
  inside the band, chosen from a table that prints no archetypes; at scale 66.8% do, barely over the line.
- Sweep 5 adds ADR-040's party-leader rules as two dimensions of the hypercube (twelve now, so its points are not
  sweep 4's); by rule, hunters make churn and aggregators lean toward stasis (ADR-040 has the table).
- The runs' dynamics are identical between sweeps 1 and 2 (only the label changed); sweeps 3 to 5 are different profiles
  or points.

## Result (sweep 5)

Archetypes at 5% or more of the runs: **4** (alternation, churn, realignment, stasis). Inside the plausibility band: **308** runs (30.8%). Checks failed: {'panel_stability': 336, 'turnout': 335, 'volatility': 155, 'enp_seats': 5}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 590 | 59.0% | method in {irv, borda, copeland, schulze}; seat_rule in {dhondt}; economy_sigma <= 0.213; ambition in {beta(1,1)} | 5% | 88% (base 59%) | 7% |
| churn | 160 | 16.0% | seat_rule in {sainte_lague, largest_remainder}; economy_sigma >= 0.152; ambition in {beta(2,3), beta(1,1)}; leader_rule in {hunter} | 5% | 49% (base 16%) | 16% |
| stasis | 132 | 13.2% | method in {plurality, irv, borda, schulze}; threshold >= 0.0103; seat_rule in {largest_remainder}; leader_rule in {aggregator, explorer} | 9% | 26% (base 13%) | 18% |
| realignment | 118 | 11.8% | method in {plurality, two_round}; seat_rule in {dhondt}; polarization_pressure >= 0.338 | 7% | 36% (base 12%) | 21% |

### Inside the plausibility band (308 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 229 | 74.4% | method in {irv, borda, copeland, schulze}; seat_rule in {dhondt}; recall_floor >= 0.133; economy_sigma <= 0.243; polarization_pressure >= 0.152; leader_rule in {sticker, hunter, explorer} | 11% | 100% (base 74%) | 15% |
| realignment | 35 | 11.4% | method in {plurality, two_round, borda}; seat_rule in {sainte_lague, largest_remainder}; scandal_rate >= 0.025; polarization_pressure >= 0.168; ambition in {beta(2,8), beta(1,1)}; leader_rule in {sticker, explorer} | 6% | 47% (base 11%) | 26% |
| stasis | 33 | 10.7% | seat_rule in {largest_remainder}; petition_threshold <= 0.348; ambition in {beta(2,3)}; leader_rule in {aggregator, hunter, explorer} | 6% | 35% (base 11%) | 21% |
| churn | 11 | 3.6% | under 5% of the runs or 20 runs: not read | | | |

### Other realignment thresholds (the same runs, relabelled)

| spreads | realignment | churn | alternation | stasis | archetypes at 5% or more |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 446 | 90 | 376 | 88 | 4 |
| 0.5 | 118 | 160 | 590 | 132 | 4 |
| 0.75 | 33 | 175 | 651 | 141 | 3 |
| 1.0 | 7 | 183 | 667 | 143 | 3 |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%, at least 5 target points in a box), over the
runs the table names; a box is a description of a sample, not a tested rule, and an archetype under 5% or 20 runs gets no
box. A cut that leaves a side open is written as `>=` or `<=`.

- **A warning about the boxes.** The negative control, `amendment_threshold` (inert on the rule-only twin, which has no
  agents to propose amendments), appeared in sweep 3's alternation boxes as a trim of its top 15% (it is in no box in
  sweeps 4 and 5). With one run per point a box can carry a cut of a dimension that does nothing. Read a trim of a range's
  edge as noise unless a ten-seed design confirms it; the cuts that also make sense mechanically are realignment's
  `polarization_pressure >= 0.34` (ADR-033's radicalisation), churn's `leader_rule` hunter (ADR-040: vote-chasing leaders
  move their parties) and churn's `economy_sigma >= 0.15` (a more volatile economy, through what is left of economic voting).
- **Plausibility.** Volatility failures fell from 670 to 142 (sweep 3) and turnout failures from 499 to 332 (sweep 4).
  In sweep 4, turnout (332) and panel stability (310) were the two most frequent failures, every one on the high side
  (turnout above 0.85, panel stability above 0.90; none below 0.5 or 0.70). Each check alone kept at least two thirds
  of the runs inside its range; all four at once, 34.2%. In sweep 5 (other points), panel stability (336) and turnout
  (335) are the two most frequent failures, again every one on the high side; 308 runs pass all four checks.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point would cost ten times as much (about 80 minutes).
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
