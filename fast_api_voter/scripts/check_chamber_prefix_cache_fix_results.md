# Prefix-cache continuity fix, chamber — plan-llm-protocol-and-theory-program.md §3.B.7

Follow-up to `check_vote_cast_prefix_cache_fix_results.md`, applying the same fix and the
same measurement discipline to `decide_chamber_deliberation`, as that doc's own
"Disposition" section flagged as not yet done.

## The fix

Same restructuring as vote_cast: the per-chunk `cid_list` moved out of
`build_chamber_system_prompt` (now a fixed reference to `expected_cids` by name) into
`build_chamber_user_prompt`'s own `expected_cids` field.

One structural difference worth naming precisely: `build_chamber_system_prompt` takes a
`members` parameter but, after this fix, **never reads it** — the function's output depends
only on `config`. Unlike vote_cast (whose system prompt still varies across elections with a
different candidate count/bounds), chamber's system prompt is now a **process-wide constant**
for a fixed config, not just constant within one chunk burst. Confirmed structurally by
`test_chamber_system_prompt_is_identical_across_different_chunks` (two disjoint member sets,
byte-identical output) — not just by inspection.

## Verified live — correctness unaffected

`check_chamber_prefix_cache_fix.py`, 6 consecutive chamber chunks (chunk_size=5, the shipped
vLLM chamber chunk size): 30 synthetic members, every one seeded with `chamber_position ==
issue_positions` — deliberately the exact state `build_chamber_system_prompt`'s own docstring
documents as the historical Mode-A trigger (2.6% baseline failure rate, unbounded repeated
"wait, maybe they differ" reasoning). Result: **30/30 decisions motif=701 (sincere), 0
llm_fallback, 0 retry_sampling_varied** — the correct ground truth for this state, and zero
Mode-A recurrences despite deliberately maximizing exposure to the known trigger. Consistent
with the fix being a pure relocation of the cid data with no semantic change to the
instruction, as intended — not assumed safe without a live check.

## Verified live — the actual cache-hit signal

vLLM's own periodic log line, read directly during the burst:

| sample | Prefix cache hit rate |
|---|---|
| 1 | 70.3% |
| 2 | 68.6% |
| 3 | 68.0% |

Only 3 samples for 6 chunks/34.9s — vLLM logs on its own periodic cadence (~10-12s), not
per-request, so this is coarser resolution than vote_cast's 8-sample burst. More importantly,
the shape is **different in kind**, not just noisier: vote_cast's hit rate climbed
monotonically through its burst (65.2%→73.0%) as more chunks of the *same election* warmed a
cache that starts cold for each new election. Chamber's here starts already high (68-70%) and
stays roughly flat.

That is consistent with, and expected from, the structural point above: since the chamber
system prompt is now a fixed constant for this config, it was almost certainly already fully
cached from earlier chamber traffic in this same server session (the container had been up 21
minutes, and prior scripts this session — `check_precision_and_logprobs_live.py` among them —
already sent this exact string) *before this script ever ran*. The burst here isn't warming
the cache; it's exercising an already-warm one. That is a **stronger** structural property
than vote_cast's, not a weaker one — vote_cast's system prompt still re-diverges per election
(different candidate count/bounds), so it must re-warm each time; chamber's does not, for as
long as `config.sortition_chamber.*` is unchanged. Not independently isolated with a
cold-cache control in this pass, so reported as the plausible explanation consistent with the
structural fact already proven by the identical-output test, not as an independently measured
number.

## Disposition

**Shipped.** Both `vote_cast` and `chamber_deliberation` now carry the §3.B.7 fix, closing
the item vote_cast's own results doc left open.
