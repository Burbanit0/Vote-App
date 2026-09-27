# coalition_decision's collapse, made continuous AND tested at real batch size — plan-llm-protocol-and-theory-program.md §5.C

## What was already known, and the two gaps it left open

`decide_coalition`'s own RELIABILITY WARNING (`plan-adversarial-framing-collapse.md`,
2026-08-30) found the collapse signature at two opposite poles — join-obvious (identical
platform to initiator, pushes comfortably past majority, initiator needs it) vs decline-obvious
(maximum platform distance across all 20 issue dimensions, initiator already has a majority
alone) — 3 responder parties each, size=1. All 6 calls returned JOIN, including at the
decline-obvious pole. That docstring itself names two things this measurement never covered:
a categorical 2-point/6-sample reading can't rule out a real gradient between the poles, and
*"Not tested at real production batch size: decide_coalition batches seated non-initiator
parties directly (up to ~4 in the shipped config), and this test used size=1 ... an open
gap."*

## Method

`check_logprob_coalition_action_tracking.py`, third production application of the §5.C
instrument. 5 responder parties with FIXED platforms interpolated along the same distance axis
the original poles used (0 → √20≈4.472, identical to maximally distant across all 20
dimensions). 5 calls, one per point on the OTHER original axis — the initiator's own
institutional shortfall, interpolated from 25 seats short (needs this party badly) to 0 short
(already has a majority alone). Every call batches **all 5 responders together** — real
production batch shape, closing the "never tested at batch size" gap directly, since this
project has an established precedent (pressure_action, vote_cast) that a batching artifact must
be checked, not assumed absent. Each call's reading is the one responder whose own fixed
distance matches that call's own institutional t — the "diagonal", so both axes move together
for the party actually being measured, exactly like the original two-pole design. Real
`build_coalition_system_prompt`/`build_coalition_user_prompt`, real `COALITION_JSON_SCHEMA`,
`think=False` (this decision type's own production value — previously "the same guess ...
flagged for live verification rather than assumed" per `decide_coalition`'s own docstring, now
exercised for the first time under a real batched multi-party completion).

## Result: P(action=1, JOIN) stays near-ceiling across the entire spectrum

| t | distance | shortfall | P(action=1) |
|---|---|---|---|
| 0.00 (join-obvious) | 0.000 | 25.0 | 0.999374 |
| 0.25 | 1.118 | 16.0 | 0.992539 |
| 0.50 | 2.236 | 8.0 | 0.964855 |
| 0.75 | 3.354 | 0.0 | 0.999015 |
| 1.00 (decline-obvious) | 4.472 | 0.0 | 0.996777 |

5/5 aligned. Pole-to-pole difference: **-0.0026** (directionally sensible — very slightly
lower at decline-obvious — but negligible). Full spread across all 5 points: **0.0345**
(the low point sits at the t=0.5 midpoint, not the decline-obvious extreme — no monotonic
trend). Every reading sits within 4% of certainty on JOIN, regardless of platform distance or
institutional need, at real multi-party batch size.

## Reading this carefully

Confirms and extends the original "6/6 identical JOIN" finding rather than contradicting or
narrowing it: not only does the categorical collapse hold at both original poles, the
continuous reading between them shows no real gradient anywhere, and — new information the
original diagnostic could not provide — the same flatness holds when 5 parties are asked about
their own coalition decision simultaneously in one call, not in isolation. The "not tested at
real batch size" gap is closed with a negative result: batching does not rescue whatever
signal a real, content-sensitive decision would show.

## Disposition

Extends `decide_coalition`'s own RELIABILITY WARNING with a dated note. No config or prompt
change — diagnostic-only, same discipline as every §5.C application so far. Three of the four
originally "collapse confirmed" decision types (`pressure_action`, `representative_response`,
`coalition_decision`) are now measured continuously via logprobs; `reaction_to_event` (SCANDAL
branch) remains the one not yet re-measured this way.
