# pressure_action's closed-menu {0,4} choice does not track self_gap — plan-llm-protocol-and-theory-program.md §5.C

## The question, verbatim from the code that flagged it as open

`decide_pressure_actions`'s own docstring (`llm_behavior_engine.py`): *"Under the SHIPPED
(closed) menu, pressure_action's real task is only choosing between 0 and 4; whether it
tracks self_gap across that pair has not been measured either."* Everything measured before
now used the OPEN menu (`petition_enabled`/`mobilization_enabled` forced on via
`dataclasses.replace`), which is not what any real flagship run actually ships — the shipped
default (`polity_config.yaml`, `pressure_menu.electoral_only: true`) legally restricts `act`
to exactly `{0=NOTHING, 4=WAIT_FOR_ELECTION}` (`menu_acts()`), a genuine binary choice at the
schema level.

## Method

`check_logprob_pressure_action_gap_tracking.py`, first production application of the §5.C
instrument validated in `check_logprob_blank_calibration_results.md`. Real
`build_pressure_system_prompt`/`build_pressure_user_prompt`, real `PRESSURE_JSON_SCHEMA`,
`think=False` (this decision type's own real production value — no `<think>` block, so no
reasoning-parser offset to solve here, unlike vote_cast), unmodified shipped config. 17
synthetic citizens, `self_gap` spanning 0.02→2.20 against a fixed `blank_threshold=0.5`
(`mandate_dev`/`ticks_to_election` held constant so only `self_gap` varies) — six clearly
satisfied, four near the threshold boundary (the specific gap the vote_cast calibration's own
results doc flagged as untested), seven clearly discontented. P(act=4) read via
`locate_decision_field_logprobs` + `binary_probability`.

## Result: P(act=4) is uniformly ≈1.0, independent of self_gap

| self_gap range | mean P(act=4) | n |
|---|---|---|
| < blank_threshold (satisfied) | 0.9961 | 8 |
| ≥ blank_threshold (discontented) | 0.9999 | 9 |

Separation: **+0.0039**. Pearson correlation(self_gap, P(act=4)): **+0.31**, driven almost
entirely by the single lowest point (self_gap=0.02 → P=0.9756, still >97%) rather than any
real gradient — every other point sits at P≥0.9966. The MOST satisfied citizen possible in
this probe (self_gap=0.02, essentially co-located with the officeholder) still returns
P(act=4)=0.976 — nowhere close to favoring `NOTHING`, despite the deterministic proxy
(`simple_rules.deterministic_pressure_action`) calling `NOTHING` correct for every citizen
below threshold.

## Ruled out: not a batching artifact

This project has an established, real precedent for batching-specific collapse (vote_cast's
own historical "chunk 4+ stops reading each voter's own distances" finding). Re-ran the two
most extreme self_gap values (0.02 and 2.20) completely alone, `chunk_size=1` — matching
`decide_pressure_actions`'s own `min_batch_size=1` floor:

| self_gap | P(act=4), solo |
|---|---|
| 0.02 | 0.999992 |
| 2.20 | 1.000000 |

Solo separation: **+0.000008** — flatter than the batch, not less. The collapse is not an
artifact of asking about 17 citizens in one call; it reproduces, if anything more strongly,
when a single citizen is asked completely alone.

## Reading this carefully

This is a DIFFERENT flavor of collapse than the OPEN-menu measurement previously found (29/70
acting codes emitted, spread across four different values, "NO content-blind collapse" —
`decide_pressure_actions`'s own docstring). That measurement never exercised the shipped
closed menu at all. This one does, and answers the specific question left open: no, the
{0,4} choice does not track self_gap under the shipped config — it appears to pick
`WAIT_FOR_ELECTION` almost unconditionally, previously invisible because nobody had reason to
suspect a genuinely restricted 2-option menu would behave differently from the already-tested
5-option one, and because a flat rate of `act=4` under the closed menu produces a
`mobilization_rate` of exactly what the closed menu already predicts by construction (0 for
the levers that matter) — this collapse would never surface as an anomaly in aggregate
mobilization metrics, only in a citizen-level P(act) reading like this one.

Not yet explained mechanistically — that is §2's job, not this measurement's. Worth noting
without overclaiming: unlike §2's original "act/response landing on another agent" framing,
BOTH `NOTHING` and `WAIT_FOR_ELECTION` are non-assertive (neither is a petition or
mobilization lever); the finding here is a strong, uniform preference for the more
procedurally-legitimate-sounding of two passive options, not a preference for inaction per se.
Whether that fits, extends, or sits outside the existing collapse hypothesis is future work.

## Disposition

Corrects `decide_pressure_actions`'s own docstring, which explicitly marked this "STILL
UNVERIFIED, do not assume either way" — now measured, with a clear negative answer. Every real
flagship run ships the closed menu; this means `pressure_action`'s already-known unreliability
extends to the ONE case every production run actually exercises, previously the least-tested
of all of them precisely because it looked the simplest (a 2-option choice).
