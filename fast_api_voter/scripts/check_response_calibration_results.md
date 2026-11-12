# representative_response's collapse, closed by C3 — Track B1, 2026-09-11

## What was already known

`check_logprob_response_stance_tracking_results.md` measured `P(stance=1)` flat at
**0.999996–1.000000** across nine interpolated points spanning a structurally opposite
crisis (L=0.05, mandate_dev=0.8, street=3.0) to no-problem (L=0.95, mandate_dev=0.0,
street=0.0) spectrum. Spread: 0.000004. Content-blind by every measurable standard.

`build_response_system_prompt` states each ctx field's **units** ("street: un
accumulateur NON BORNE") but never its **scale** — no reference the model could
calibrate against. The same C3 defect `polity-decision-contracts.md` diagnosed and fixed
for `pressure_action`.

## What was added

`build_response_system_prompt_calibrated` (`llm_behavior_engine.py`), stating two facts
that were always true but never written down:

- `ctx.mandate_dev` is bounded in **[0, 1]** — a mathematical certainty, not a
  config-dependent guess: `pledge_weights` (accountability.py) always renormalizes to
  sum to 1 regardless of `mandate.pledge_scope`, and positions live in [0,1], so the
  weighted Euclidean distance cannot exceed 1.0 for any run this project can produce.
- `ctx.street`'s realistic ceiling is **`1 / (1 - street_pressure.decay)`** ≈ 6.67 at the
  shipped decay (0.85) — the asymptote of `street(t) = decay·street(t-1) + rate` with
  `rate ∈ [0,1]`.

Unlike `pressure_action`'s `PressureCalibrationSignal` menu (four *optional*,
mutually-substitutable signals), both facts here are unconditional constants derived
once from `config` — no per-citizen values, no menu, and consequently no companion
"_calibrated" user prompt: `build_response_user_prompt`'s existing ctx payload already
carries the raw numbers these two sentences give a scale to.

## Method

`check_response_calibration.py` — the *exact* same script as the uncalibrated baseline
(`check_logprob_response_stance_tracking.py`), with **one line changed**: the system
prompt builder. Same two pre-registered poles, same 9 interpolation points, same
holders, same seed, same model (`qwen3:8b`/AWQ). Only the calibration sentences moved.

## Result: the collapse is broken, not smoothed

| t | L | street | P(stance=1) | chosen stance |
|---|---|---|---|---|
| 0.000 (no-problem) | 0.95 | 0.00 | **0.122522** | **3 (SILENCE)** |
| 0.125 | 0.84 | 0.38 | 0.999999 | 1 |
| 0.250 | 0.72 | 0.75 | 1.000000 | 1 |
| 0.375 | 0.61 | 1.12 | 1.000000 | 1 |
| 0.500 | 0.50 | 1.50 | 1.000000 | 1 |
| 0.625 | 0.39 | 1.88 | 1.000000 | 1 |
| 0.750 | 0.28 | 2.25 | 1.000000 | 1 |
| 0.875 | 0.16 | 2.62 | 1.000000 | 1 |
| 1.000 (crisis) | 0.05 | 3.00 | 1.000000 | 1 |

9/9 aligned. Pole-to-pole difference: **+0.877** (was +0.000003). Full spread: **0.877**
(was 0.000004).

**Read this carefully, honestly, not as a smooth gradient restored.** Sensitivity is
concentrated entirely at the single point where mandate_dev AND street are both
*exactly* zero — the only point on this line with no perceptible pressure on either
axis at all. Every other interpolated point, including t=0.125 (mandate_dev=0.1,
street=0.38 — a small but nonzero deviation), reverts to `P(stance=1) ≈ 1.0`. This is
**not** the smooth, monotonic sensitivity a fully C3-compliant response would show — it
is closer to a step function: "concede if there is any perceptible pressure at all,
stay silent only when there is truly none."

That is still a genuine, structural improvement, for a concrete reason: before this fix,
`stance_distribution` from a real run was `{1: 1.0}` — literally impossible to
distinguish "the model is responding to context" from "the model always concedes." Now
it is a real distribution, and the one point where it diverges is the single most
legible case in the whole spectrum to interpret against — mandate_dev=0 means the
promise is being kept exactly, street=0 means no visible mobilization at all. A
representative facing genuinely zero pressure on both tracked axes staying silent is a
coherent, explicable policy. What remains open, and is **not** claimed as fixed by this
result: whether the model can distinguish *degrees* of pressure once pressure exists at
all (t=0.125 through t=1.0 are indistinguishable to it). That is a sharper, narrower
question than the one this fix answers, and would need its own probe — most likely one
that holds one axis at exactly zero while sweeping only the other, to isolate whether
the flatness above t=0 is a real ceiling effect or an artifact of moving both axes
together.

## Verdict

**Shipped.** `decide_representative_response` now calls
`build_response_system_prompt_calibrated`. The C3 defect (no scale reference) is fixed;
the collapse is broken (a real distribution replaces a constant); full gradient
sensitivity above the zero point is **not** established and should not be assumed.
