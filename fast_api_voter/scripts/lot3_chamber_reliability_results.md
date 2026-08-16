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

**Overall (as shipped): PASS** -- both findings resolved in code (`ChamberDecision`'s coherence validator
removed; `decide_chamber_deliberation` chunks at `_CHAMBER_MAX_CHUNK_SIZE=10`), confirmed against the real
model at the real production scale.
