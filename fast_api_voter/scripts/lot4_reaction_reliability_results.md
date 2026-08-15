# reaction_to_event (dt=8, §8) reliability spike (v5 Lot 4)

Real llm_schemas.ReactionBatch / llm_behavior_engine.build_reaction_*_prompt, real EventType/ReactionMotif enums from the start (shipped since v5 Lot 1) -- no toy schema stage, unlike the pre-v4-Lot-6 spike. Sweeps the one real production chunk size (25, since 100/25 divides evenly with no remainder) plus smaller sizes for a margin.

| event_type | size | rep | ok | elapsed(s) | out_of_menu | over_cap | incoherent | motif counts | detail |
|---|---|---|---|---|---|---|---|---|---|
| SCANDAL | 1 | 1 | True | 18.5 | 0 | 0 | 0 | {401: 1, 403: 0} |  |
| SCANDAL | 1 | 2 | True | 5.0 | 0 | 0 | 0 | {401: 1, 403: 0} |  |
| SCANDAL | 5 | 1 | True | 18.9 | 0 | 0 | 0 | {401: 5, 403: 0} |  |
| SCANDAL | 5 | 2 | True | 16.9 | 0 | 0 | 0 | {401: 5, 403: 0} |  |
| SCANDAL | 25 | 1 | True | 87.8 | 0 | 0 | 0 | {401: 21, 403: 4} |  |
| SCANDAL | 25 | 2 | True | 79.9 | 0 | 0 | 0 | {401: 25, 403: 0} |  |
| ECONOMIC_SHOCK | 1 | 1 | True | 8.8 | 0 | 0 | 0 | {402: 1, 403: 0} |  |
| ECONOMIC_SHOCK | 1 | 2 | True | 5.0 | 0 | 0 | 0 | {402: 1, 403: 0} |  |
| ECONOMIC_SHOCK | 5 | 1 | True | 21.8 | 0 | 0 | 0 | {402: 5, 403: 0} |  |
| ECONOMIC_SHOCK | 5 | 2 | True | 19.9 | 0 | 0 | 0 | {402: 5, 403: 0} |  |
| ECONOMIC_SHOCK | 25 | 1 | True | 86.7 | 0 | 0 | 0 | {402: 25, 403: 0} |  |
| ECONOMIC_SHOCK | 25 | 2 | True | 80.0 | 0 | 0 | 0 | {402: 25, 403: 0} |  |

## Summary

failures: 0/12

**Overall: PASS**

## Findings

- **`think=False` on the native path is clean for this schema at every swept size, for both
  event types** — 12/12, zero out-of-menu motifs, zero over-cap `salience_delta`s, zero
  incoherent `salience_delta==0`/`motif` pairs. This is the third schema shape (after
  `ResponseBatch`/`PressureBatch`) confirmed reliable under `think=False`, and the first
  confirmed clean on its very first attempt with the real enums from the start — no toy-schema
  detour, no wrong-motif-set correction needed.
- **The model does reach `403 EVENT_PERSONALLY_IRRELEVANT`, not just the grounding motif** — one
  `SCANDAL` batch at size 25 (rep 1) produced 4 `403`s out of 25 citizens, alongside 21 `401`s.
  This confirms `EVENT_PERSONALLY_IRRELEVANT` is a genuinely reachable branch on the LLM path
  (unlike the deterministic baseline, where it is structurally unreachable by construction) —
  the palier's own "no per-citizen judgment on the deterministic path, real per-citizen judgment
  on the LLM path" contrast is visible in this spike's own raw output, not just asserted.
- **Wall-clock at size 25 (~80-90s) lands in the same range as dt=10's own measured `size=25`
  rows** (95.8-117.0s, `lot6_batch_reliability_results.md`) — consistent with `compute_max_tokens`'s
  flat, chunk-size-independent reasoning allowance dominating completion time for both schemas.
  This confirms the Volume/cost forecast in the Lot 4 plan (~16-24 total scandal calls per full
  30-year run at shipped defaults) translates to roughly 20-30 minutes of live wall-clock for a
  full acceptance-scale scandal-only run, well within the "minutes per firing tick" budget the
  plan anticipated.
- This satisfies the roadmap's own Principal Risks pre-flight gate for Lot 4: `decide_reaction_to_event`'s
  engine code (chunking, validation, wiring) is written only after these numbers landed, per this
  project's standing "spike before you build on it" discipline.
