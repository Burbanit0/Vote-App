# Catalogue of scenarios: the first 1,000 runs

plan-scenarios-v1, step 6. Reproduced by `python scripts/run_polity_catalogue.py run --out <dir> --runs 1000 --seed 1`
(then `report`): the rule-only scenario twin, 15 years, 100 citizens, one run per point of a Latin hypercube over the ten
settings of `api/domain/polity/catalogue.py::DIMENSIONS`, a run seed of its own per point, 14 workers, about 8 minutes.
Run three times (two under the first label, one under ADR-037's): the runs agree point for point, and only the labels
differ between the labelling versions. A reading, not a pre-registered experiment.

**The step's gate is still not met: 3 archetypes reach 5% of the runs, not 4** (stasis is at 4.0%, 40 runs). It was
first not met because the realignment label fired on 89% of the runs (archetype version 2, a fixed 0.1); the owner
had the rule changed to half the population's own spread ([ADR-037](../../docs/adr/ADR-037-realignment-against-the-populations-spread.md),
version 3), which is the result below. The 5% for "non-trivial" is my reading; the plan does not number it.

## Result (archetype version 3)

Archetypes at 5% or more of the runs: **3** (alternation, churn, realignment). Inside the plausibility band: **97** runs (9.7%). Checks failed: {'volatility': 670, 'turnout': 467, 'panel_stability': 309, 'enp_seats': 71}.

### All runs (1000 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| churn | 603 | 60.3% | method in {plurality, irv, borda, copeland, schulze}; threshold >= 0.00866; seat_rule in {sainte_lague}; 0.118 <= economy_sigma <= 0.267; ambition in {beta(2,3)} | 6% | 87% (base 60%) | 8% |
| alternation | 219 | 21.9% | method in {plurality, two_round, borda, copeland, schulze}; threshold <= 0.0914; seat_rule in {dhondt, largest_remainder}; economy_sigma <= 0.14; ambition in {beta(2,3)} | 5% | 67% (base 22%) | 16% |
| realignment | 138 | 13.8% | method in {plurality, irv, schulze}; seat_rule in {dhondt, sainte_lague}; polarization_pressure >= 0.448; ambition in {beta(2,8)} | 6% | 41% (base 14%) | 18% |
| stasis | 40 | 4.0% | under 5% of the runs or 20 runs: not read | | | |

### Inside the plausibility band (97 runs)

| archetype | runs | share | box | support | density | coverage |
|---|---:|---:|---|---:|---:|---:|
| alternation | 61 | 62.9% | method in {plurality, two_round, borda, copeland, schulze}; threshold <= 0.092; recall_floor <= 0.363; petition_threshold >= 0.082; ambition in {beta(2,3)} | 18% | 100% (base 63%) | 28% |
| churn | 15 | 15.5% | under 5% of the runs or 20 runs: not read | | | |
| realignment | 12 | 12.4% | under 5% of the runs or 20 runs: not read | | | |
| stasis | 9 | 9.3% | under 5% of the runs or 20 runs: not read | | | |

PRIM here is peeling only (`catalogue.prim`: alpha 0.1, minimum support 5%, at least 5 target points in a box), over the
runs the table names; a box is a description of a sample, not a tested rule, and an archetype with fewer than 20 runs gets
no box (stasis, 40 runs and 4.0%, is under the 5% cutoff and gets none). A cut that
leaves a side open is written as `>=` or `<=`. Three boxes have a real lift over the base rate:

- **alternation** (22% of the runs): a box at 67% density names a low electoral threshold, a low economy sigma and the
  middling ambition distribution, with the proportional seat rules (D'Hondt, largest remainder);
- **realignment** (14%): 41% density for `polarization_pressure >= 0.45`, Sainte-Lague or D'Hondt, and a skewed ambition
  distribution, which is the radicalisation of ADR-033 doing what it should;
- **churn** (60%): 87% density for Sainte-Lague, a mid-to-high economy sigma and a middling ambition distribution. With
  60% as its base rate it is the new dominant label, not a finding by itself.

Inside the plausibility band (97 runs, 9.7%) alternation is 63% of the runs and a box with 100% density (18% support)
names a low threshold, a low recall floor and a high petition threshold.

## The label's history, and its sensitivity

Version 2 labelled 89% of the runs as realignment: the rule was "the population's mean moved 0.1 or more", which 89%
crossed, exactly. Even with almost no polarization pressure (below 0.1) 71% did. ADR-037 measures the shift in units of the
first census's own spread (its median over the runs is 0.82) at a threshold of half a spread, a round fraction that I picked knowing the old distribution (ADR-037 says so; judge it by this table). `report` prints this table from the stored fields (`catalogue.relabel`). Relabelling the same runs at other thresholds (the first five
rules never fire in these runs; relabelling at 0.5 reproduces the run's own labels, 1,000 of 1,000):

| threshold | realignment | churn | alternation | stasis | archetypes at 5% or more |
|---:|---:|---:|---:|---:|---:|
| 0.1 fixed (version 2) | 890 | 76 | 29 | 5 | 2 |
| 0.25 spreads | 462 | 363 | 151 | 24 | 3 |
| **0.5 spreads** | **138** | **603** | **219** | **40** | **3** |
| 0.75 spreads | 41 | 678 | 238 | 43 | 2 |
| 1.0 spreads | 7 | 705 | 244 | 44 | 2 |

**No threshold of the realignment rule gives four archetypes at 5%**: stasis tops out at 4.4%. The next bottleneck is the
churn rule (a volatility of 0.4 in any legislative election), another fixed threshold; I did not retune it. The negative
control behaves: `amendment_threshold` is in no box.

## What this does not show

- One run per point: the seed is a nuisance variable that PRIM is not told about, so a box mixes a setting's effect with
  seed noise. Ten seeds per point (the earlier sweeps' design) would cost ten times as much (about 80 minutes).
- 15 years is one block of the block-wise label (blocks of 8 to 16 years), so a run is read as one story whatever its
  length; the 30-year runs of ADR-035 read as three blocks.
- "Electorate polarization" has no knob (nothing sets the initial spread of views): the dimension is the pressure that
  pushes angry citizens away from the president, which is the radicalisation of ADR-033, not a polarised electorate.
- The model arm (the plan's "then the GPU on the most original cells") has not run; the GPU is shared and no vLLM is up.
