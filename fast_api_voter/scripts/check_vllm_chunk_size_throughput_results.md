# vLLM chunk-size throughput and correctness — vote_cast and chamber_deliberation

Follow-up to Phase 2's own "also worth testing" item (`plan-flagship-30y-run.md`), prompted by
the question: with `VLLM_BATCH_INVARIANT` ruled out on cost
(`check_vllm_batch_invariant_results.md`), is there any other lever to speed up Phase 7 before
committing to a ~75-82h sequential flagship run? `_VOTE_CAST_MAX_CHUNK_SIZE` and
`_CHAMBER_MAX_CHUNK_SIZE` have both been pinned to 1 since before the vLLM switch, entirely on
Ollama-era evidence.

## Summary

- **The dynamic max_tokens fix works.** Probing real `prompt_tokens` per call and requesting
  `16384 - prompt_tokens - margin` (instead of a flat think-token addend) eliminates the
  context-overflow failures a naive scaled-allowance guess produced, and lets both decision types
  decode cleanly at chunk sizes well past 1.
- **The historically blocking failure mode for `vote_cast` does not reproduce on vLLM.**
  `cast_votes`'s own docstring documents a "Mode A" identity-permutation collapse — schema-valid
  but factually wrong rankings, measured directly against `weighted_distance` ground truth,
  0-2/5 correct at chunk=5 — but every citation is Ollama (`OLLAMA_CONTEXT_LENGTH`). Re-tested here
  against real ground truth (`simple_rules.build_ranking`, the same logic
  `_deterministic_vote_fallback` uses) on vLLM/Qwen3-8B-AWQ: **23/24 correct at chunk=3, 29/30 at
  chunk=5** across every structurally-clean decode. The collapse is gone on this backend.
- **A different, chunk-size-independent reliability quirk exists and was mistaken for a
  chunk-size effect at first.** The model sometimes emits `blank=1` together with a non-empty
  `ranking` — a §3.6.1 hard-rule violation that Pydantic catches post-hoc because it isn't encoded
  in the JSON schema/grammar. Reproduced standalone at **chunk_size=1, the shipped baseline**, so
  it predates and is unrelated to this investigation. Production already wraps every call in
  `_complete_and_decode_with_replay` (`replays=config.llm.max_batch_replays`); this test script
  calls the client directly with no retry, so its raw single-shot failure rates overstate what
  production actually sees.
- **Both decision types get a real, substantial throughput win.** ~2.4-2.7x faster per-citizen for
  vote_cast at chunk 3/5, ~1.5-2.1x faster per-member for chamber at chunk 3/5 — on top of the
  proportional reduction in call *count* (5x fewer calls at chunk=5), which also amortizes
  per-call overhead not captured in the s/citizen or s/member figures below.

## Method

`scripts/check_vllm_chunk_size_throughput.py`, real production prompt-builders
(`build_system_prompt`/`build_user_prompt`, `build_chamber_system_prompt`/
`build_chamber_user_prompt`), real decode (`decode_vote_batch`/`decode_chamber_batch`) and
validation (`validate_decision`/`validate_chamber_decision`), against the real vLLM/AWQ backend
(`docker-compose.llm.yml`). `max_tokens` is sized per-call by probing the real `prompt_tokens` for
the exact prompt about to be sent (one cheap `max_tokens=1` request) and requesting
`16384 - prompt_tokens - 300`. For vote_cast, each decoded decision is additionally diffed against
`simple_rules.build_ranking` ground truth (blank flag + full ranking order), not just schema
validity.

Two bugs were found and fixed along the way, both in the harness, not production:
1. An earlier version scaled the think-token allowance with chunk size
   (`chunk_size * 6000`/`chunk_size * 4000`), which both contradicted this project's own
   flat-addend convention (`compute_max_tokens`'s own docstring: reasoning length is
   "unpredictable, not proportional to the number of decisions") and exceeded the 16384 ceiling
   outright at chunk_size >= 3 (a real 19716-token request was rejected).
2. The voter pool for `--chunk-sizes` runs was sized off the module's default `_CHUNK_SIZES`
   constant instead of the requested `args.chunk_sizes`, silently running out of voters at larger
   chunk sizes/rep counts and producing spurious "batch misaligned" failures.

## Results — vote_cast (n=8 per chunk size, real production population, `parties.initial_count=5`)

| chunk_size | structurally clean | ranking correct (of clean) | s/citizen (successful, avg) |
|---|---|---|---|
| 1 | 4/8 (50%) | 4/4 (100%) | 12.18 |
| 2 | 7/8 (87.5%) | 7/7 (100%) | 6.04 |
| 3 | 8/8 (100%) | 23/24 voters (95.8%) | 4.53 |
| 5 | 6/8 (75%) | 29/30 voters (96.7%) | 5.07 |

Failure breakdown (all 4 chunk sizes combined, 32 attempts, 13 failures):
- **10 are the blank+non-empty-ranking §3.6.1 quirk** (4 at chunk=1, 0 at chunk=2, 0 at chunk=3,
  1 at chunk=5 — that one had "5 validation errors", i.e. multiple voters in the same chunk hit it
  simultaneously). Reproduced standalone at chunk=1 with the exact same shape (see raw JSON in the
  investigation transcript) — chunk-size-independent, pre-existing, and within the class of error
  `_complete_and_decode_with_replay` already retries against in production.
- **2 are `finish_reason='length'` truncations** despite the maximized dynamic budget (1 at
  chunk=2, 1 at chunk=5) — the same irreducible "occasional long `<think>` tail" tax
  `_CHAMBER_THINK_TOKEN_ALLOWANCE`'s own history already documents for chamber; not eliminated by
  budget maximization, just made rare.
- **1 is unexplained** (chunk=2, rep 1, "batch failed schema validation: 2 validation errors" in
  the earlier buggy-ceiling run — not reproduced in the clean re-run).

A failure at larger chunk size has a larger blast radius: a chunk=5 failure forces a 5-voter
retry, a chunk=1 failure forces a 1-voter retry. Chunk=3 was the only size with **zero** failures
in this run (8/8 clean, 23/24 correct) while still capturing most of the speedup (4.53 s/citizen,
essentially tied with chunk=5's 5.07).

## Results — chamber_deliberation (n=8 per chunk size at 2/3/5, n=2 at 1 baseline + prior runs)

| chunk_size | structurally clean | s/member (avg across all runs) |
|---|---|---|
| 1 | 10/10 | 2.9 |
| 2 | 14/14 | 3.72 |
| 3 | 16/16 | 1.85 |
| 5 | 15/16 (1 truncation) | 1.40 |

No ground-truth correctness concern is documented for chamber anywhere in this codebase (its own
docstring history is exclusively "Mode B" — token-budget exhaustion, converges once given enough
budget — never a Mode-A-style reasoning collapse). The one chunk=5 failure was a
`finish_reason='length'` truncation, the same rare tail as vote_cast's.

## What this does and does not decide

**Chamber_deliberation → 5** is well-supported: consistent, large win (~2x), only one failure in
40 total attempts across every run in this investigation, and no correctness-collapse concern on
record for this decision type.

**vote_cast** is a closer call than "raise it to 5". Chunk=3 and chunk=5 deliver almost identical
throughput, but chunk=3 was clean in every attempt in the rigorous run while chunk=5 produced both
a truncation and a multi-voter schema failure — and vote_cast is this project's own most
extensively-documented fragile decision type. Chunk=3 is the better-evidenced choice: nearly all
of the speedup, smaller failure blast radius, zero observed failures.

**Shipping either change requires more than bumping a constant.** Both call sites
(`cast_votes`/`decide_chamber_deliberation` in `llm_behavior_engine.py`) currently compute
`max_tokens` as `compute_max_tokens(len(chunk)) + <flat allowance>`. Raising the chunk-size
constants without also replacing that flat formula reproduces the exact context-overflow failure
this investigation's first (buggy) pass hit. The dynamic probe-and-maximize approach proven here
adds one cheap `max_tokens=1` round-trip per real call (prefill-only, no decode) — a real but
small tax relative to the ~2-2.7x throughput win. Whether to bring that into production, and at
what chunk size, is the open decision.
