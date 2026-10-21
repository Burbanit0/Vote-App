# ADR-033: radicalisation: angry citizens, once events have shaken the polity, step away from the president

**Status**: Accepted — built in the scenario profile only (plan-scenarios-v1, step 3a; owner's direction, 2026-10-21). Off everywhere else: both settings ship at 0.
**Date**: 2026-10-21
**Context**: Until now an event changed a citizen's attention (`event_salience`) and feeling (anger, anxiety),
never their position. A scandal or a bad economy could mobilise a crowd and still leave every citizen where
they stood, so a society could be shaken and come back to the same place. The owner asked for citizens who
"become more radical after some events". ADR-032 measured the other half of the problem: opinion relaxes to a
fixed anchor, so even a move that happens does not last.

The calibration of ADR-012 had already fixed the one external check this needs. D1: across citizens, the
four-year correlation of each latent factor lies in [0.70, 0.90]. The scenario profile's drift of 0.02 scored
0.996 on it (ten seeds, 8 years, 100 citizens, the rule-only twin): citizens who never change their minds.

## What `event_salience` is, because the push reads it

`event_salience` is **event-driven**: `update_event_salience` runs when a scandal or an economic shock fires
and sets it to 0.85 x its previous value plus the reaction's delta; nothing changes it between events. It
therefore starts at 0, jumps at the first event, **does not fade** until the next one, and under repeated
events climbs towards about 2 (a delta of 0.3 over a decay of 0.85). With the rule path (`llm.crowd: false`)
the reaction is `deterministic_reaction_to_event`: one flat delta, **the same for every citizen**. With the
model's reactions the deltas differ by citizen. So on the rule path salience selects nobody; it only
switches the push on, from the first event.

## Decision

Inside the opinion-dynamics update (`opinion_dynamics.update_latent_factors`), two couplings, both 0 by
default (then the update is ADR-012's, bit for bit, and the mood is not even built; a property test holds
it):

- **`dynamics.radical_step`**: a citizen angry at the president steps, per update, along the latent space
  *away from the president's factors*, by `radical_step x anger x salience`, in the unit direction away from
  them. The president is the one the emotions phase appraises (the sitting president with a revealed
  position), so the push and the anger agree on who that is. No such president, or the president themself:
  no push. It goes through the same `susceptibility` as the neighbours' pull, so the anchor draws it back.
  Anger gates it: a calm citizen does not move.
- **`dynamics.anger_narrows_bound`**: at anger 1 a citizen's confidence bound is `(1 - this)` of
  `confidence_bound`: an angry citizen listens only to the like-minded (Deffuant et al.'s extremist pull).

Config rules: both need `dynamics.enabled` and `emotions.enabled`; `radical_step` also needs `events.enabled`
(without events salience stays 0 and the push never fires) and `susceptibility` < 1 (with no anchor a pushed
citizen would walk off without limit). `opinion_dynamics_step` journals `radicalised`, the citizens pushed by
at least 1% of the step, while `radical_step` > 0 (anger is an exponential blend that never reaches exactly
0, and a push of 1e-9 is not a radicalised citizen).

**The scenario profile sets** `radical_step` 0.5, `anger_narrows_bound` 0.3 and `drift_std` 0.18. The drift is
what brings panel stability into D1's band; the push is what makes the movement correlated, so that a
minority of citizens ends somewhere else.

## Measured

Ten seeds, 8 years, 100 citizens, `--engine deterministic --profile scenario` with the three settings of each
row, the rule-only twin; D1 is the digest's `trajectory.panel_stability`, D2 the spread of each factor at year
8 over year 1's (the year-0 census carries no factors), "in band" the seeds with no plausibility check failed.
Not pre-registered: a reading, from an uncommitted probe that sets the three settings and calls
`run_simulation` and `build_digest`; the shipped row is what `run_polity_seed_sweep.py --engine deterministic
--profile scenario` reports.

| drift | push | narrowing | D1 | D2 | mean opinion shift | pushed per update | archetypes (entropy) | pairwise distance, year 0 to 8 | in band |
|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
| 0.02 | 0 | 0 | 0.996 | 0.96 | 0.013 | 0 | stasis 7, alternation 3 (0.88) | 2.26 to 3.68 | 0/10 |
| 0.20 | 0 | 0 | 0.851 | 1.00 | 0.037 | 0 | stasis 6, alternation 4 (0.97) | 2.26 to 3.67 | 2/10 |
| 0.02 | 1.0 | 0.5 | 0.947 | 1.71 | 0.101 | 15.4 | realignment 5, stasis 5 (1.00) | 1.73 to 4.19 | 0/10 |
| 0.15 | 1.0 | 0.5 | 0.891 | 1.70 | 0.112 | 16.9 | realignment 6, stasis 3, alternation 1 (1.30) | 1.75 to 4.39 | 3/10 |
| 0.15 | 2.0 | 0.5 | 0.876 | 2.66 | 0.154 | 17.2 | the same (1.30) | 1.53 to 4.35 | 5/10 |
| 0.15 | 0.5 | 0.5 | 0.904 | 1.28 | 0.078 | 16.6 | the same (1.30) | 1.95 to 4.31 | 2/10 |
| 0.15 | 0.5 | 0 | 0.905 | 1.26 | 0.077 | 16.6 | the same (1.30) | 1.97 to 4.30 | 2/10 |
| **0.18** | **0.5** | **0.3** | **0.877** | **1.30** | **0.093** | **17.6** | **realignment 6, stasis 3, alternation 1 (1.30)** | **1.88 to 4.19** | **4/10** |

- **The push has a dial.** At the old drift, a push of 0 to 1 takes the mean shift from 0.013 to 0.101, with
  about 15 of 100 citizens pushed per update.
- **Drift alone reaches D1 only at 0.2**, and then moves nobody as a group (mean shift 0.037, no new
  archetype). The push alone does not reach it at 0.02 (D1 0.947): both are needed.
- **Narrowing did nothing measurable** (D1 0.904 against 0.905): at `confidence_bound` 1.0 a neighbour is
  rarely out of earshot. It is kept small, as a knob for a graph where it would bite.
- **The ten-seed divergence test at the shipped values** moves from varied no (0.88 bits, stasis 7 of 10) to
  varied yes (1.30 bits); the runs still drift apart; four of ten seeds sit inside the whole plausibility
  band (none did before). Still failing: no dominant story (realignment, 6 of 10) and turnout below 0.5 in
  five seeds.

## Not settled

- **The push has no ceiling and a feedback.** Moving away from the president raises the gap, hence anger
  (clamped at 1), hence the push; and salience is unclamped. A single update moves a citizen by at most about
  2 x `radical_step`, and with an anchor (`susceptibility` s) the displacement is at most about
  s x push / (1 - s), which is large at s = 0.9. Exited citizens, the angriest, are pushed like the rest, and
  for ever. The spread of views at year 8 is 1.3 times year 1's at the shipped values and 2.7 times at a push
  of 2; D2 guards against collapse, not against this. A cap, or a push that weakens with distance, is the
  next thing to try if the spread matters.
- **A shock reaches nobody in particular on the rule path** (above). Making the rule-based reaction judge
  each citizen (who is exposed, who cares) is step 3b's welfare channel; the model's reactions already vary.
- **The push does not fade with the event**, only with anger: salience stays until the next event. A fading
  push needs a per-tick shock memory, which would be state.
- **Hysteresis is not here.** A pushed citizen drifts back when the anger fades, because the anchor does not
  follow: that is ADR-032 option D, step 4.
- **The strengths are a reading, not a calibration.** One population size, one seed set, the rule-only twin;
  the model engine's turnout and anger differ. D1's band is this project's choice (ADR-012), not a derived
  figure.
- **"Realignment"** in the archetype rules is the population's mean moving 0.1 from the first census, which
  the push can now produce; whether that is what a political scientist would call one is open.
