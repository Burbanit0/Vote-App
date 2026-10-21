# ADR-033: radicalisation: angry citizens a shock reached step away from the president

**Status**: Accepted — built in the scenario profile only (plan-scenarios-v1, step 3; owner's direction, 2026-10-21). Off everywhere else: both settings ship at 0.
**Date**: 2026-10-21
**Context**: Until now an event changed a citizen's attention (`event_salience`) and feeling (anger, anxiety),
never their position. A scandal or a bad economy could mobilise a crowd and still leave every citizen where
they stood, so a society could be shaken and come back to the same place. The owner asked for citizens who
"become more radical after some events". ADR-032 measured the other half of the problem: opinion relaxes to a
fixed anchor, so even a move that happens does not last.

The calibration of ADR-012 had already fixed the one external check this needs. D1: across citizens, the
four-year correlation of each latent factor lies in [0.70, 0.90]. The scenario profile's drift of 0.02 scored
0.996 on it (ten seeds, 8 years, 100 citizens, the rule-only twin): citizens who never change their minds.

## Decision

Inside the opinion-dynamics update (`opinion_dynamics.update_latent_factors`), two couplings, both read off
the citizens at the update and both 0 by default (then the update is the one ADR-012 built, bit for bit):

- **`dynamics.radical_step`**: an angry citizen steps, per update, along the latent space *away from the
  sitting president's factors*, by `radical_step x anger x salience`, in the unit direction away from them.
  Salience is the one a shock left (decaying 0.85 a tick), so the push moves only the citizens a shock
  reached, and only while the memory lasts. No president, or the president themself: no push. The push goes
  through the same `susceptibility` as the neighbours' pull, so the anchor draws it back.
- **`dynamics.anger_narrows_bound`**: at anger 1 a citizen's confidence bound is `(1 - this)` of
  `confidence_bound`: an angry citizen listens only to the like-minded (Deffuant et al.'s extremist pull).

Both need `emotions.enabled`: anger is tracked there, and nothing else reads it. A `radicalised` field on
`opinion_dynamics_step` counts the citizens the push moved, present while `radical_step` > 0.

**The scenario profile sets** `radical_step` 0.5, `anger_narrows_bound` 0.3 and `drift_std` 0.18. The drift is
what brings panel stability into D1's band; the push is what makes the movement correlated, so that a
minority of citizens ends somewhere else.

## Measured

Ten seeds, 8 years, 100 citizens, `--engine deterministic --profile scenario`, the rule-only twin; D1 and D2
from the yearly census (`latent_factors`), D2 against year 1 (the year-0 census carries no factors). Not
pre-registered: a reading.

| drift | push | narrowing | D1 four-year correlation | D2 spread kept | mean opinion shift | archetypes |
|---:|---:|---:|---:|---:|---:|---|
| 0.02 | 0 | 0 | 0.996 | | 0.013 | stasis 7, alternation 3 |
| 0.20 | 0 | 0 | 0.851 | 1.004 | 0.037 | stasis 6, alternation 4 |
| 0.15 | 1.0 | 0.5 | 0.891 | 1.70 | 0.112 | realignment 6, stasis 3, alternation 1 |
| 0.15 | 2.0 | 0.5 | 0.876 | 2.66 | 0.154 | realignment 6, stasis 3, alternation 1 |
| 0.15 | 0.5 | 0.5 | 0.904 | 1.28 | 0.078 | realignment 6, stasis 3, alternation 1 |
| 0.15 | 0.5 | 0 | 0.905 | 1.26 | 0.077 | the same |
| **0.18** | **0.5** | **0.3** | **0.877** | **1.30** | **0.093** | realignment 6, stasis 3, alternation 1 |

- **The push works and has a dial.** At 0.02 drift, a push of 0 to 1 takes the mean shift from 0.013 to
  0.101, about 17 citizens a tick pushed.
- **Drift alone reaches D1 only at 0.2**, and then moves nobody as a group (mean shift 0.037).
- **Narrowing did nothing measurable** (0.904 against 0.905): at `confidence_bound` 1.0 a neighbour is
  rarely out of earshot. It is kept small, as a knob for a graph where it would bite.
- **The ten-seed divergence test at the shipped values** moves from varied no, 0.88 bits (stasis 7 of 10)
  to varied yes, 1.30 bits; the runs still drift apart (mean pairwise distance 1.88 at year 0, 4.19 at year
  8); four of ten seeds now sit inside the whole plausibility band, none did before. Still failing: no
  dominant story (realignment, 6 of 10) and turnout below 0.5 in five seeds.

## Not settled

- **The push has no ceiling.** Only the anchor draws a pushed citizen back, so the spread of views at year 8
  is 1.3 times year 1's at the shipped values and 2.7 times at a push of 2. D2 guards against collapse, not
  against this; a cap, or a push that weakens with distance, is the next thing to try if the spread matters.
- **Hysteresis is not here.** A pushed citizen drifts back when the anger fades, because the anchor does not
  follow: that is ADR-032 option D, step 4.
- **The strengths are a reading, not a calibration.** One population size, one seed set, the rule-only twin;
  the model engine's turnout and anger differ. D1's band is this project's choice (ADR-012), not a derived
  figure.
- **"Realignment"** in the archetype rules is the population's mean moving 0.1 from the first census, which
  the push can now produce; whether that is what a political scientist would call one is open.
