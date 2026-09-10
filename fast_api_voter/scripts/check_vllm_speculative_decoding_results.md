# n-gram speculative decoding — plan-llm-protocol-and-theory-program.md §3.B.6

Zero mentions anywhere in this project's history before this — untested, not rejected. vLLM 0.28.0
supports `--speculative-config` with `method: "ngram"` (prompt-lookup speculation, no separate draft
model needed): looks for repeated n-grams in the prompt/generated text so far and proposes the next
few tokens from that match; the real model verifies every proposal in one forward pass and only
accepts matches. **Lossless by construction at temperature=0** — an accepted token is one the real
model would have emitted anyway, a rejected one falls back to normal decoding for that position.

## Config shipped

```json
{"method": "ngram", "num_speculative_tokens": 5, "prompt_lookup_max": 4, "prompt_lookup_min": 2}
```

Added to `docker-compose.llm.yml`. Clean restart, `docker inspect` reports `healthy`, no traceback.
GPU memory after startup: 12,404 MiB (within the existing `--gpu-memory-utilization 0.80` budget,
not a separate draft-model allocation — n-gram speculation needs no extra weights). Three benign,
informational-only warnings at startup: async scheduling disabled for ngram speculation, a
`max_num_scheduled_tokens=2048` capacity note (vLLM's own suggestion to raise
`max_num_batched_tokens`, not investigated further here), and "Model Runner V2 does not yet support
ngram... using V1" (a compatibility fallback, not an error).

## Losslessness — verified directly, not assumed

`check_vllm_speculative_decoding.py`, chamber_deliberation (5 members, `think=True`), same prompt
and seed both times:

- **Before** (no speculative config): 3 reps, 13.4–13.7s each, byte-identical to each other.
- **After** (speculative config live): 3 reps, byte-identical to each other, **and byte-identical to
  the before run's own content** — confirmed by direct string comparison, not inference.

This is the property that actually matters before shipping anything server-side: the change cannot
silently alter any decision this project has already measured, tuned, or shipped a constant around.

## Throughput — real, but content-dependent, not a flat multiplier

| Decision type | Before | After (first call) | After (warm) |
|---|---|---|---|
| chamber_deliberation (5 members, uniform sincere-position test fixture) | 13.4–13.7s | 38.6s (one-time JIT/cudagraph warmup) | **5.4s (~2.5x faster)** |
| vote_cast (3 voters, varied per-voter reasoning) | ~13.6s (chunk-size investigation's own 4.53s/citizen × 3) | 8.6s | 12.5s (roughly neutral) |

The warmup cost (38.6s) happens once per server start, not per call — irrelevant for a long-running
server processing thousands of calls. The throughput gain itself is **not uniform**: it tracks how
repetitive the actual generated content is. The chamber fixture used here has all 5 members in an
identical "nothing to decide" state (`chamber_position == issue_positions` for every member), so the
model's own reasoning repeats very similar phrasing member to member — exactly the pattern n-gram
lookup exploits. vote_cast's own reasoning is more voter-specific (different distances, different
thresholds each time), giving n-gram matching less to find. **Real production chamber/vote_cast
traffic sits somewhere between these two synthetic extremes** — this was not re-measured against a
diverse population here.

## Disposition

**Shipped.** Losslessness is a hard, verified guarantee, not a probabilistic one — there is no
downside-risk scenario where this makes a decision wrong, only a floor on how much it helps (a
decision type with little repeated structure sees close to zero benefit, never a regression, since
an unmatched speculation just falls back to ordinary decoding for that token). Worth revisiting
`max_num_batched_tokens` per vLLm's own startup suggestion if a later measurement shows the
`max_num_scheduled_tokens=2048` cap actually binding — not investigated in this pass.
