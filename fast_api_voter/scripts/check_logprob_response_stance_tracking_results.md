# representative_response's collapse, made continuous — plan-llm-protocol-and-theory-program.md §5.C

## What was already known

`decide_representative_response`'s own RELIABILITY WARNING
(`plan-adversarial-framing-collapse.md`, 2026-08-30) found a collapse SIGNATURE: two
structurally opposite ctx poles (crisis: L=0.05/mandate_dev=0.8/street=3.0/ticks_left=2;
no-problem: L=0.95/mandate_dev=0.0/street=0.0/ticks_left=20), 3 different holders each,
size=1/think=False (the real production shape — this decision type never chunks). All 4
successfully-decoded calls returned the exact same `stance`, shift count, and motif at both
poles. A real finding, but a 2-point, 4-sample categorical measurement leaves open whether the
response is flat EVERYWHERE between those poles, or whether there's some narrower region of
real sensitivity a 2-point probe would simply miss.

## Method

`check_logprob_response_stance_tracking.py`, second production application of the §5.C
instrument (after `pressure_action`). Reuses the SAME two poles verbatim — not re-chosen, for
direct comparability with the existing finding — and linearly interpolates 9 points between
them (L, mandate_dev, street each interpolated; `ticks_left` rounded; `lame_duck` held fixed
at `False`, not one of the original two poles' own axes). Real
`build_response_system_prompt`/`build_response_user_prompt`, real `RESPONSE_JSON_SCHEMA`,
`think=False` (this type's own production value), every call solo (`size=1`) — matching both
production (this decision type never batches: 0-or-1 sitting president) and the original
diagnostic's own methodology, so no separate batching control was needed here. Read
`candidate_probability(token, "1")` — P(stance=1, CONCESSION) — at each point via
`locate_decision_field_logprobs`.

## Result: P(stance=1) is flat at ≈1.000000 across the entire spectrum

| t | L | street | P(stance=1) |
|---|---|---|---|
| 0.000 (no-problem) | 0.95 | 0.00 | 1.000000 |
| 0.125 | 0.84 | 0.38 | 0.999999 |
| 0.250 | 0.72 | 0.75 | 1.000000 |
| 0.375 | 0.61 | 1.12 | 1.000000 |
| 0.500 | 0.50 | 1.50 | 1.000000 |
| 0.625 | 0.39 | 1.88 | 1.000000 |
| 0.750 | 0.28 | 2.25 | 1.000000 |
| 0.875 | 0.16 | 2.62 | 1.000000 |
| 1.000 (crisis) | 0.05 | 3.00 | 0.999999 |

9/9 aligned. Full spread across all 9 points: **0.000001** — indistinguishable from floating-
point noise in the logprob computation itself. This is not "mostly flat with some real
movement at the extremes" the way `pressure_action`'s reading was (0.976→1.0, a small but
non-zero gradient): here there is, to six decimal places, no detectable gradient anywhere
between an officeholder with near-perfect legitimacy and zero street pressure, and one with
near-zero legitimacy, deep mandate deviation, and sustained mass mobilization. The model
returns CONCESSION with near-certainty regardless.

## Reading this carefully

This sharpens rather than merely repeats the existing collapse-signature finding: where the
original 4/4-identical measurement could not rule out a narrow sensitive region between two
widely-spaced sample points, a 9-point continuous sweep across the full documented range now
can, and finds none. Both extremes of the officeholder's own institutional position — "you are
doing great, no one is upset" and "you are failing badly and a mob has formed" — receive the
identical, near-certain response. This is the most decisive single collapse measurement
produced by the §5.C instrument so far (more extreme than `pressure_action`'s own 0.976-1.0
range), consistent with — and now quantitatively confirming — the mechanism §4.A's own audit
already flagged as a live candidate explanation for the design doc's own open question (a
president conceding to a population with `inaction_rate=1.0`: not a real behavioral finding
about passive populations, but this exact collapse surfacing in the aggregate).

## Disposition

Extends `decide_representative_response`'s own RELIABILITY WARNING with a dated note. No
config or prompt change — diagnostic-only, same discipline as every §5.C application so far.
