# ADR-012: dynamic citizens — opinion dynamics and emotions

**Status**: Accepted — built in S4.3 (`plan-polity-build-order.md`). Both mechanisms ship off, at
neutral settings, until the calibration below.
**Date**: 2026-09-13
**Context**: decision D6 (2026-09-13) chose dynamic citizens as one of four levers against
elections that repeat themselves.

## Context

A citizen's issue positions were drawn once, by `generate_population`, and never moved. Only
officeholders' stated positions moved: pledges, revealed positions and chamber positions. Nothing
that candidacy and nomination read changed between two elections, so the model received
byte-identical requests at each election and returned the same field (`observations.md` OBS-001,
OBS-003).

The awakening gate, which decides who is asked about pressure, read a citizen's gap to the
president, the president's deviation from their pledges, how close the election is, event salience
and neighbours' mobilization. It had no internal state of the citizen's own. The build order asks
for:

- a pure update of positions over the social graph: Friedkin–Johnsen with bounded confidence, in
  the two-factor latent space;
- anger, anxiety and enthusiasm driving awakening and mobilization;
- a step size pre-registered against measured panel stability;
- the static population kept as the control arm.

## Decision

### Opinion dynamics (`opinion_dynamics.py`, `dynamics:`)

A factor_structure population's positions are
`sigmoid(factors · loadings + residuals)`, with two latent factors per citizen.
`citizen.LatentStructure` keeps that model. It is redrawn from the seed on a run's start and on
resume, and it rebuilds the generated positions exactly.

Once per tick, after every other phase, each citizen's factors move. The update for citizen i
(Friedkin and Johnsen's social influence model, with Hegselmann–Krause-style bounded confidence):

    B_i  = { j ∈ N(i) : |f_j − f_i| ≤ confidence_bound }
    m_i  = mean of f_j over B_i, or f_i when B_i is empty
    f_i' = (1 − susceptibility)·a_i + susceptibility·(f_i + influence_step·(m_i − f_i))
           + drift_std·e_i

Here N(i) is i's social-graph neighbours, a_i their initial factors, and e_i ~ N(0, I).

- **Positions follow the factors.** Positions are then recomputed from the moved factors with the
  same loadings and residuals, so a citizen's issues stay correlated the way they were drawn.
- **Where movement comes from.** A citizen's view changes through their neighbours (bounded
  confidence: only neighbours close enough in the latent space count), through a pull back toward
  their starting view, and through idiosyncratic drift.
- **Who moves.** Every citizen, officeholders included. Pledges, revealed positions and chamber
  positions stay their own fields, moved only by their own mechanisms.
- **Randomness.** Drift draws from a fifth random stream (`dynamics_rng`), one draw per citizen and
  factor on every update whatever `drift_std` is. That stream is checkpointed.
- **Settings the rules refuse.** Dynamics require `citizens.position_dist: factor_structure`, and
  an `influence_step` above zero requires the social graph.
- **Journal and snapshots.** Each update journals one `opinion_dynamics_step` with the mean shift,
  the largest shift and the number of citizens with a neighbour within bound. The yearly snapshot
  carries each citizen's `latent_factors` once they have moved.

### Emotions (`emotions.py`, `emotions:`)

Each emotion is in [0, 1] and moves every tick `1 − decay` of the way toward its appraisal,
starting from 0. The appraisals follow the affective intelligence account (Marcus, Neuman and
MacKuen 2000): anger at a responsible agent, anxiety at threat, enthusiasm at things going one's
way.

- **Anger** toward the sitting president: `gap / blank_threshold − 1`, clamped. It rises with how
  far past the citizen's own tolerance the president's revealed position stands.
- **Enthusiasm**: `1 − gap / blank_threshold`, clamped. It rises with how far inside that tolerance
  the president stands. Anger and enthusiasm both decay toward 0 with no president, and for the
  president themself.
- **Anxiety**: `|economy_x| / economy_shock_threshold`, clamped, the economy's distance from
  normal.

The appraisal runs after the tick's elections, so a new president is the one appraised, and before
accountability. It journals one `emotions_updated` event with the population's mean emotions. The
yearly snapshot carries each citizen's three emotions.

They act in two places, each through a weight that ships at 0:

- **Awakening.** `awakening_anger`, `awakening_anxiety` and `awakening_enthusiasm` form a pull
  inside the threshold's existing modulation, which stays bounded to [1 − amp, 1 + amp]. Anger and
  anxiety lower the threshold, so more citizens are consulted; enthusiasm raises it.
- **Mobilization.** `mobilization_anger` scales the blank threshold that the deterministic pressure
  rule and the LLM path's fallback act past. At anger 1 the rule acts past
  `(1 − mobilization_anger) × blank_threshold`. Anger is the emotion found to mobilize costly
  participation (Valentino et al. 2011).
- **On the LLM path.** A tracked citizen's three emotions are sent in `pressure_action`'s context
  as calibration signals. Their definitions state what each number measures and prescribe no
  reaction (the C4 contract, enforced by the existing no-if-then test).

Emotions require `awakening.enabled`.

## Control arm and first acceptance

- **Neutral settings.** With `susceptibility: 1`, `influence_step: 0` and `drift_std: 0`, an update
  moves nobody at all (a Hypothesis property over 300 random graphs, factors and bounds). With
  every emotion weight at 0, emotions change no decision.
- **Whole run at neutral settings.** A run with both mechanisms enabled at those settings journals
  exactly what the static run journals, plus the two new event types.
- **Shipped state.** Both mechanisms ship disabled. The two golden references and the bake-off
  case bank do not move, and a static run's checkpoints and snapshots gain no keys.
- **Resume.** A dynamic run killed mid-tick and resumed reproduces the uninterrupted run's journal
  and snapshots byte for byte.
- **Update correctness.** An update matches a hand-computed Friedkin–Johnsen step. Without drift,
  every citizen stays within the span of the population's current and initial factors (property).
- **Cost.**
  - p500: the update takes 1.4 ms per tick and the appraisal 1.6 ms.
  - p100 deterministic twin: an 8-year run takes 0.15–0.17 s with either mechanism on or off.

## Pre-registered facts for the calibration

**Setup.** Measured on the p100 deterministic twin (`run_polity_flagship.py`'s full-mechanism
config, social graph on), seeds 1–10, 8 years, before any setting leaves neutral. Each fact is also
reported for the static arm.

**Search.** Dynamics are calibrated first, over:

- `susceptibility` ∈ {0.90, 0.95, 0.98}
- `influence_step` ∈ {0.1, 0.2, 0.4}
- `confidence_bound` ∈ {0.5, 1.0, 2.0}
- `drift_std` ∈ {0.02, 0.05, 0.10}

**Selection.** Among the settings where D1–D4 hold, the one whose D1 correlation is closest to
0.80 is adopted. Emotion weights are calibrated next, with that dynamics setting, over
{0, 0.25, 0.5} for each of the four weights. Among the weight sets where E1–E3 hold, the smallest
by total weight is adopted.

**If nothing qualifies.** The mechanism stays off, and the failing facts are reported.

### Dynamics

1. **D1 — panel stability.** Across citizens, the correlation of each latent factor between yearly
   snapshots four years apart (years 1→5 through 4→8), averaged over pairs and seeds, lies within
   [0.70, 0.90]. The band is this project's choice, not a derived figure. Panel studies find that
   issue scales built from many items are about as stable over a four-year panel as party
   identification (Ansolabehere, Rodden and Snyder 2008). A static population scores 1.0, and
   churn with no memory scores near 0.
2. **D2 — no consensus collapse.** Each factor's standard deviation across citizens at year 8 is at
   least 80% of year 0's.
3. **D3 — a local signature of influence.** The mean latent distance between graph neighbours,
   divided by the mean distance between all pairs, is lower at year 8 than at year 0.
4. **D4 — elections differ (D6's purpose).** The mean number of distinct presidents per run is
   higher than under the static arm.

### Emotions

1. **E1 — discontent mobilizes.** Ticks in the top third by mean anger have a higher mobilization
   count (`pressure_action` events with act 3) than ticks in the bottom third.
2. **E2 — hard times draw people in.** Ticks in the top third by mean anxiety have more
   `pressure_action` events, i.e. more citizens consulted, than ticks in the bottom third.
3. **E3 — honeymoon decline.** Mean enthusiasm in a presidential term's first year exceeds its last
   year's in a majority of full terms (the decline in presidential popularity over a term, Mueller
   1970).

## Consequences

- **Config hash.** The two new config sections enter `config_hash`, so a run started before S4.3
  resumes only under the code it started with.
- **Model coverage.** Emotions in the `pressure_action` prompt are unmeasured on the model. Before
  an LLM run turns emotions on, the bake-off needs a pressure family whose cases carry them.
- **Deterministic path.** A president's revealed position moves only on the LLM path (through
  `representative_response`). On the deterministic twin, a citizen's gap to the president therefore
  changes through the citizen's own moving view, and through elections.
- **Legacy flag.** `citizens.static_population` is unrelated: it is about births and deaths, and
  stays true.
