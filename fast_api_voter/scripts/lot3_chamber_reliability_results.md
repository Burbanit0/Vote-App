# chamber_deliberation (dt=11, §6bis.3) reliability spike (v6b Lot 3)

Real llm_schemas.ChamberBatch / llm_behavior_engine.build_chamber_*_prompt from the start (this lot's own first commit) -- no toy schema stage. Original sweep below covers the planned production cohort size (30, sortition_chamber.seats shipped, originally intended to run UN-chunked) plus smaller sizes for a margin. Two real, load-bearing findings came out of this pass, both resolved in code -- see "Resolution" below, which is the part that actually shipped.

| size | rep | ok | elapsed(s) | out_of_menu | over_cap | incoherent | motif counts | detail |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | True | 17.2 | 0 | 0 | 0 | {701: 1, 702: 0} |  |
| 1 | 2 | True | 4.6 | 0 | 0 | 0 | {701: 1, 702: 0} |  |
| 10 | 1 | False | 79.5 | 0 | 0 | 9 | {701: 1, 702: 9} |  |
| 10 | 2 | False | 79.5 | 0 | 0 | 9 | {701: 1, 702: 9} |  |
| 30 | 1 | False | 139.9 | n/a | n/a | n/a | n/a | decode failed: batch misaligned with the request: expected cids [700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729], got [724, 725, 726, 727, 728, 729] |
| 30 | 2 | False | 118.6 | n/a | n/a | n/a | n/a | decode failed: batch misaligned with the request: expected cids [700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729], got [724, 725, 726, 727, 728, 729] |

## Summary (original sweep)

failures: 4/6

**Overall: FAIL** (against the original, since-corrected design and success criterion -- see Resolution)

## Finding 1 — the shifts<->motif coherence rule fails at a high rate against the real model

At size 10, both reps succeeded at returning all 10 aligned decisions, but 9/10 were flagged "incoherent" by
`ChamberDecision`'s own model_validator at the time (shifts non-empty iff motif==702): the model frequently
labelled a small shift (e.g. `{"dimension": 4, "delta": 0.05}`) with `motif=701` (SINCERE_POSITION) anyway.
At size 30 (before the batch-size finding below made that call fail for an unrelated reason), 6/6 decisions
were similarly incoherent.

**Resolution**: `ChamberDecision`'s `_check_motif_coherence` validator was removed. This mirrors the exact
precedent already set for `PressureDecision`'s own act<->motif pairing (v6 Lot 3): the intended pairing is
stated in the system prompt as guidance only, `motif` is a stated-but-unverified label, and Lot 4's own
`chamber_deviation` metric reads `shifts`/`chamber_position` directly, never `motif` -- so an incoherent
label costs nothing downstream. The realized shifts x motif pairing is a Lot 4 measurement, not an
invariant. See `ChamberDecision`'s own docstring (`llm_schemas.py`).

## Finding 2 — one call of 30 (and even a chunk of 15) silently drops all but the last 6 decisions

The original design assumed `chamber_deliberation` never needs `chunk_voters` at all -- the cohort is
capped at `sortition_chamber.seats` (shipped 30), "a handful", the same category as dt=5/dt=6. This table's
own size=30 rows show that assumption was wrong: with `max_tokens` raised to 8000 (well above
`compute_max_tokens(30)=3336`, ruling out a token-budget cutoff), the model still returned a complete,
well-formed JSON batch containing only 6 decisions -- always the numerically LAST 6 cids of whatever range
was requested, regardless of the range's own size or starting point. A follow-up diagnostic confirmed this
is NOT a `chunk_voters`/`MIN_SAFE_BATCH_SIZE`-shaped problem either: re-chunking the same 30-member cohort
into two chunks of 15 reproduced the identical failure on BOTH chunks (each chunk of 15 returned only its
own last 6). Only at chunk size 10 did every chunk return complete and aligned -- confirmed 3/3 on the real
30-member cohort split into three chunks of 10.

The likely root cause: unlike `PressureContext`'s own deliberate choice to send only scalar summaries
(`self_gap`, never a 20-dim position vector) specifically to keep dt=10's per-citizen batches light,
`ChamberContext`'s own user prompt sends TWO full 20-dimension float arrays per member
(`sincere_position`, `chamber_position`) -- unavoidable here, since choosing which dimension to shift needs
the actual position vectors, unlike dt=10's accept/reject decision. That per-member weight appears to be
what collapses this particular schema's reliable batch ceiling well below `MIN_SAFE_BATCH_SIZE=20`
(calibrated on the much lighter `vote_cast` prompt shape) or dt=8/dt=10's own 25-citizen ceiling.

**Resolution**: `decide_chamber_deliberation` chunks via `chunk_voters` at a new, dedicated constant,
`_CHAMBER_MAX_CHUNK_SIZE=10` (`llm_behavior_engine.py`), with `min_batch_size=1` (since
`sortition_chamber.seats` can be configured below 10, and `MIN_SAFE_BATCH_SIZE`'s own floor doesn't apply
to this prompt shape either way). At the shipped `seats=30`, this produces exactly three chunks of 10 per
tick -- confirmed reliable, not assumed.

## Confirmatory diagnostics (informal, not part of the automated sweep above)

Run directly against the real `build_chamber_*_prompt`/`decode_chamber_batch` after both fixes above landed
in code, using the real 30-member cohort (cids 700-729):

| chunking | chunk sizes | result |
|---|---|---|
| none (1 call) | [30] | 1 call: only 6/30 decisions returned (last 6 cids) |
| `chunk_voters(., 15)` | [15, 15] | both chunks: only 6/15 decisions returned each (last 6 cids) |
| `chunk_voters(., 10)` | [10, 10, 10] | all 3 chunks: 10/10 decisions returned, fully aligned |

**Overall (as shipped at the time): PASS** -- both findings resolved in code (`ChamberDecision`'s coherence
validator removed; `decide_chamber_deliberation` chunks at `_CHAMBER_MAX_CHUNK_SIZE=10`), confirmed against
the real model at the real production scale. **Superseded below** -- 10 was not a stable ceiling either.

## Lot 4 correction — chunk_size=10 was not a stable ceiling; 5 tried and disproven; 1 shipped

A real v6b acceptance run (2026-08-21/22, GPU, `sortition-llm-8y`, tick 18) hit `finish_reason='length'` on
a `chamber_deliberation` chunk-of-10 call, 3/3 attempts (original + both replays), aborting the run.
Correlated against the ollama container logs: all three attempts landed on **exactly** `n_decoded=10136`
tokens generated -- `compute_max_tokens(10) + _CHAMBER_THINK_TOKEN_ALLOWANCE = 2136 + 8000 = 10136`,
byte-for-byte identical across attempts. `n_ctx_slot=16384`, `truncated=0`, prompt=4754 tokens (11630
tokens of real headroom to the actual context ceiling) -- not a context-window artifact, the deterministic
"hits the configured ceiling on the nose" signature (Mode B: budget too tight), the same signature
`_VOTE_CAST_MAX_CHUNK_SIZE`'s own history already documents. The failed run's own journal (1258 events, one
real `recalled` event) was preserved, renamed aside rather than deleted.

**Diagnostic methodology**: reconstructed ground truth directly from the crashed run's own journal (no
re-run) -- regenerated the population deterministically (seed=42, `generate_population`), identified the
30 seated sortition members from the last `sortition_rotation` event (tick 16), and replayed each member's
own journaled `chamber_deliberation` shifts (ticks 16-17) via `apply_shifts` to reconstruct the real
`chamber_position` state at tick 18, the crash tick. Called the real production prompt builders
(`build_chamber_system_prompt`/`build_chamber_user_prompt`) and `OllamaJsonClient` directly against this
reconstructed state -- the same "replay from the journal, call the real production path" methodology used
for the same-day `cast_votes` retry-mitigation validation.

**Step 1 -- reproduce at chunk_size=10**: called all three original chunk-of-10 groups (sorted citizen_id,
exactly what `decide_chamber_deliberation` built under the then-shipped constant) against the real model.
None reproduced the crash this time (22.2s/26.6s/30.0s, all clean) -- consistent with this backend's own
already-documented finding that temperature=0 + a pinned seed is NOT a reproducibility guarantee here
(`llm_client.py`'s own module docstring), not evidence the overflow doesn't happen.

**Step 2 -- try chunk_size=5**: split each chunk-of-10 into two chunk-of-5 halves (six calls total) for
margin evidence. Five of six completed cleanly (13.0-35.0s). The sixth -- `chunk3-half-A`, cids
`[59, 61, 65, 75, 90]` -- **reproduced the identical failure**: `finish_reason='length'`, 99.1s to fail.
Docker logs confirmed `eval time = 96931.95 ms / 9836 tokens` -- **exactly**
`compute_max_tokens(5) + _CHAMBER_THINK_TOKEN_ALLOWANCE = 1836 + 8000 = 9836`, the new configured ceiling,
zero margin, not merely close to it. **chunk_size=5 does not hold** -- it relocates the same failure to a
different sub-chunk. This mirrors `_VOTE_CAST_MAX_CHUNK_SIZE`'s own history precisely: intermediate chunk
sizes (there, 3 and then 2) can still occasionally overflow.

**Step 3 -- chunk_size=1 on the same failing group**: called each of the five failing citizens
(`[59, 61, 65, 75, 90]`) individually, same reconstructed context, `max_tokens = compute_max_tokens(1) +
8000 = 9596`. All five completed cleanly: 7.7s, 11.7s, 5.9s, 4.3s, 5.1s -- an order of magnitude faster
than the 99-108s overflow calls, real margin rather than a near-miss.

| step | chunk_size | result |
|---|---|---|
| 1 | 10 (all 3 original chunks) | 3/3 clean this pass (did not reproduce the live crash -- backend non-determinism) |
| 2 | 5 (6 halves of the above) | 5/6 clean; `chunk3-half-A` [59,61,65,75,90] failed at exactly the new ceiling (9836/9836) |
| 3 | 1 (the 5 failing citizens, individually) | 5/5 clean, 4.3-11.7s each, real margin |

**Resolution (v6b Lot 4 correction, 2026-08-22)**: `_CHAMBER_MAX_CHUNK_SIZE` cut from 10 to **1** --
`vote_cast`'s own endpoint, for the same reason. `min_batch_size=1` (already passed) is now a no-op but
left in place, harmless. Cost consequence, stated honestly: `chamber_deliberation` runs every tick, so this
is 30 calls/tick instead of 3 (chunk=10) or 6 (chunk=5) -- but per-call wall clock dropped sharply at the
smaller chunk size (heavy prompt-cache reuse across near-identical system prompts, and less content to
reason about per call), partially offsetting the call-count increase; the real net effect is reported by
the acceptance run itself, not estimated here.
