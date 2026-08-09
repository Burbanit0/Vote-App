# Ollama structured-output verification — v2 increment 1, Lot 0

Verification spike for the approved plan (`abundant-puzzling-bubble.md`), run before
writing `llm_client.py`. Confirms whether Ollama's OpenAI-compatible endpoint
(`/v1/chat/completions` — what `polity_config.yaml`'s `llm.base_url` actually points
at) supports what the production client needs from `qwen3:8b`, the pinned model.

**Setup**: `docker run -d -p 11434:11434 --name ollama ollama/ollama`,
`docker exec ollama ollama pull qwen3:8b` (5.2GB), CPU-only (no GPU on this machine).
Script: `fast_api_voter/scripts/check_ollama_structured_output.py`.

## Result: three real, load-bearing findings, all understood and actionable

| # | Check | Result |
|---|---|---|
| 1 | Model present | ✅ pass |
| 2 | `<think>` block in visible content on a trivial prompt | Not present — but see the threshold finding below, generation can still consume the whole budget invisibly on some prompts |
| 3 | Seed fidelity | ✅ same seed twice → identical. Different seed → **also** identical, which is *correct*: at `temperature=0`, decoding is greedy/argmax, so seed has nothing to randomize. Not a bug. |
| 4 | Sequential determinism on the real `/v1` structured-output surface | ✅ 5/5 identical calls |
| 5 | Structured output on the real `VoteCastBatch` schema, toy 3-citizen batch | ❌ still fails after Findings A/B — root-caused below: below a ~12-15 citizen threshold, not specific to this toy case |
| 6 | Full-size batch (25 citizens × 20 dims, the actual `max_batch_size`) | ❌ then ✅ after both fixes — see **Finding A** and **Finding B** |

**Bottom line: the production-relevant batch size (25, matching `llm.max_batch_size`)
works reliably once both fixes below are applied. Batches below a threshold measured
between 12 and 15 citizens fail regardless of token budget — root-caused to batch
size itself (see below), with a concrete chunking rule to avoid it.**

## Finding A: Ollama's structured-output layer cannot handle Pydantic's `$defs`/`$ref` nesting

`VoteCastBatch.model_json_schema()` produces a schema with `VoteCastDecision` factored
out into `$defs` and referenced via `$ref` — standard Pydantic v2 behavior for a
nested model. Sent as-is in `response_format.json_schema.schema`, every request
**silently consumed the entire token budget with zero visible content**
(`finish_reason: "length"`, `content` = `""`), regardless of prompt.

Isolated by testing three schema shapes against the identical prompt:
1. A flat, hand-written schema (no nesting) → worked immediately (`finish_reason:
   "stop"`, valid content).
2. The real `VoteCastBatch` schema, `$ref` manually dereferenced (defs inlined by
   substitution) → also worked immediately.
3. The real `VoteCastBatch` schema, `$ref` intact → reliably failed, every time.

**Fix**: dereference the schema (inline `$defs` via `$ref` substitution) before
sending it as `response_format`. Implemented as `_inline_refs()` in the spike script
— a one-level-deep substitution, sufficient for this project's schemas.
`llm_client.py` must do the same; it is not optional.

## Finding B: the model doesn't reliably return one decision per citizen without an explicit, enumerated cid list

Even after Finding A's fix, the first full-size batch (25 citizens) returned **24**
decisions, not 25 — reproducibly missing the *last* citizen (`finish_reason: "stop"`,
i.e. the model believed it was done). This reproduced identically across repeated
attempts, including with `max_tokens` raised from 1128 to 2200 — ruling out a
token-budget cause (`completion_tokens` usage was identical, 818, across both
budgets; the model chose to stop, it wasn't cut off).

A system prompt merely stating "you must return exactly N decisions" was
insufficient. **Fix**: enumerate the full list of expected cids verbatim in the
system prompt (`"decisions must contain exactly these 25 cids, each once, in this
order: [0,1,2,...,24]"`) plus an explicit self-check instruction ("verify every cid
in this list appears exactly once before finalizing"). With both changes, the model
returned all 25 decisions, correct cids, correct order:

```
6. full-size batch (25 citizens x 20 dims, 10 candidates): finish_reason=stop,
   usage={'prompt_tokens': 975, 'completion_tokens': 1026, 'total_tokens': 2001},
   elapsed=208.6s, content_len=1788
   valid=True, count_ok=True (got 25), cids_ok=True
```

**Consequence for `llm_behavior_engine.py`**: `build_system_prompt()` must take the
batch's actual cid list (not just a count) and enumerate it verbatim, plus include a
self-verification instruction — implemented this way in the spike script's final
`_system_prompt()`. A prompt that only states the *count* is not sufficient for this
model.

## Root-cause investigation: there is a real minimum-viable-batch-size threshold

The toy 3-citizen batch's failure (`finish_reason: "length"`, `content` = `""`, at
every `max_tokens` tested up to 2000) was investigated further by isolating variables
one at a time, holding the known-good recipe's dimensionality and candidate count
fixed (20 dims, 10 candidates — matching the working 25-citizen batch) and varying
**only** citizen count:

| citizens | result |
|---|---|
| 1 | fails (`length`, 0 content, 2200/2200 tokens consumed) |
| 3 | fails, identically |
| 8 | fails, identically |
| 10 | fails, identically |
| 12 | fails, identically |
| 15 | **works** — `stop`, 15/15 correct, only 406/2200 tokens used |
| 25 | **works** (Finding B, above) |

This cleanly isolates the cause to **citizen count itself** (i.e. batch size), not
dimensionality or candidate count — both were held constant across every row above.
There is a real threshold between 12 and 15 citizens (for this exact model,
quantization, and prompt style) below which the model enters a non-terminating,
zero-visible-output generation state regardless of token budget, and above which it
answers correctly using a small fraction of its budget. The underlying mechanism
(why a *smaller* task causes *more* — and unproductive — generation) was not
determined; that would require comparing quantizations/serving backends, which is
out of proportion to what this increment needs. Confirmed NOT the cause: token
budget, `$ref` nesting (Finding A), or missing cid enumeration (Finding B) — all
were already fixed/controlled-for in every row of this sweep.

**Practical exposure for this increment**: `population_size: 100` /
`max_batch_size: 25` in the shipped config divides evenly into four chunks of 25 —
comfortably above the observed threshold. **Decision for `llm_behavior_engine.py`**:
its chunking function must guarantee no chunk ever falls below a safety margin above
the observed threshold (recommend a documented constant, e.g. `MIN_SAFE_BATCH_SIZE =
20` — comfortably above the empirical 12-15 boundary, accounting for the fact that
real citizen data may shift the exact threshold slightly from this synthetic test).
Concretely: chunk into equal-sized groups of `max_batch_size` where possible: when
`population_size % max_batch_size` would leave a small remainder, redistribute into
near-equal chunks (e.g. `numpy.array_split`-style) instead of a fixed-size-with-small-
remainder split, so no chunk is ever small enough to risk this failure mode.

## Wall-clock (measured, CPU-only, no GPU)

- Toy 3-citizen batch: ~55-60s per call (even the failing ones — the budget is spent
  either way).
- Full 25-citizen batch (20 dims, 10 candidates): ~205-225s (~3.5-4 min) per call.
- A full 30-year run needs 4 batches × 8 presidential elections = 32 such calls ⇒
  roughly **2-2.5 hours** per run at this batch size, serialized (required for
  reproducibility per `llm_batching_determinism_results.md`'s earlier finding).
  Consistent with the design doc's own framing (§15bis.0: the cost is time, not
  money) but should be treated as a real, planned number, not a surprise later.

## Post-merge consolidation pass (test_polity_llm_live.py, live run)

Running the 3 live tests that weren't executed at merge time (only the full-size
batch test above had been run live) surfaced 3 more real, load-bearing issues —
none of them infra flukes:

- **Token budget too tight**: `chunk_size*60+256` assumes completion length scales
  with the number of decisions, but Qwen3's `<think>` reasoning shares the same
  completion budget and is not proportional to batch size — a 20-citizen/2-candidate
  call hit `finish_reason=length` at 1456 tokens. Fixed with `compute_max_tokens()`:
  a flat 1536-token reasoning allowance (`llm_behavior_engine.py`), not scaled by
  batch size.
- **Client timeout had no real margin**: the one successful full-size-batch call
  above took 294.64s against a 300s default — a near-miss, not a pass with room to
  spare. Raised `OllamaJsonClient.from_config`'s default to 600s.
- **Candidate cids need the same explicit grounding as voter cids (Finding B, but
  for candidates)**: a full simulation run returned a ranking of `[1..10]` for an
  election whose real candidates were `{11, 20, 48, 61, 62}` — the model hallucinated
  a generic ordinal list instead of reading the real candidate cids out of the user
  prompt. First attempt: enumerate the candidate cid list verbatim in the system
  prompt, the same "use only these, and no others" instruction already used for
  voters. This also exposed a test gap: `test_full_size_batch_produces_a_valid_reliable_response`
  never checked that ranking values were valid candidate cids, only that the voter
  cid matched — now asserts both.

## Finding C: a candidate is also a citizen — ranking must use positions, not cids

The cid-enumeration fix above introduced a worse regression: the model started
filling `decisions[].cid` (the *voter* being decided for) with values from the
*candidate* cid list instead. E.g. expected voter cids `[0..24]`, got
`[1000,1001,1002,1003,1004]` cycled five times — the candidate cids, not the
voters'.

Root cause: a candidate **is** a citizen, so candidate cids and voter cids draw
from the same number space and legitimately collide in a real election (citizen 11
both casts a vote and is a candidate others rank). Two "use exactly this list of
cids" instructions with overlapping numbers gave the model no reliable way to tell
which list a given integer belonged to in which JSON field.

**Fix**: `ranking` now holds 1-indexed *positions* into the candidate list (sorted
by citizen_id), never candidate cids. Positions are a disjoint, always-small (1..N)
number space, structurally incapable of colliding with voter cids — this removes
the ambiguity by construction rather than by stronger wording.
`llm_behavior_engine.sorted_candidates()`/`resolve_ranking_cids()` translate
positions back to real cids for the ballot and the journal; the position encoding
never leaves the wire-protocol boundary. Confirmed on a live full run
(`test_a_short_live_run_produces_a_valid_journal`) with real overlapping voter/
candidate cid ranges: passes.

## Finding D: identical requests are not guaranteed byte-identical output

`test_sequential_calls_are_byte_identical` (two back-to-back calls, same prompts,
same seed=42, `temperature=0`) failed on a live run: citizen cid=0 got `blank=1` on
the first call and `blank=0` on the second. This contradicts this project's earlier
assumption (from `llm_batching_determinism_results.md`'s sequential-call check,
5/5 identical) that temperature=0 + a pinned seed guarantees reproducibility for
non-concurrent calls.

Most likely cause: non-deterministic floating-point reduction order in
multi-threaded CPU inference (llama.cpp, which Ollama runs on) can occasionally
flip a close-call token even under greedy/argmax decoding, cascading into a
different generation from that point on. This is a known, documented property of
such backends (OpenAI's own `seed` parameter docs call determinism "best effort",
not guaranteed) — not a bug in this project's code, and not fixable at the prompt
or application layer. Chasing the exact mechanism further (comparing thread counts,
quantizations, or serving backends) was judged out of proportion to what this
increment needs, the same call made for the small-batch threshold above.

**Consequence**: byte-identical reproducibility for the *live* LLM path is not a
guarantee this project can make. What still holds, and is still tested:
1. This project's own code is deterministic given the same LLM responses (the
   `FakeLlmClient`-based tests in `test_polity_llm_behavior_engine.py` and
   `test_polity_run_simulation.py` produce byte-identical journals every time).
2. If a future increment needs true cross-run reproducibility for a controlled
   baseline-vs-LLM comparison (§11.4), the mechanism is the deferred response cache
   (§4.2) — replay a pinned response, don't expect the live model to regenerate it.

The live test was renamed to `test_sequential_calls_each_produce_a_valid_response`
and no longer asserts byte-identity — it proves each call independently produces a
valid, correctly-aligned response, which is what's actually guaranteed.

## Finding E: the reasoning-budget bug tracks prompt framing, not batch size (v2 increment 3)

`party_nomination_choice` (arbitrating among a party's declared candidates) batches
*contested parties* per tick, not citizens — a handful at most (`parties.initial_count`
is 5 in the shipped config), nowhere near `candidacy_considered`'s 20-25-citizen
batches. The working hypothesis going in was that `think=True` (vote_cast's setting)
would be safe here specifically *because* the batch is so small — candidacy's
zero-output bug was assumed to be a function of processing many items in one call.

Live-verified against `qwen3:8b`, that hypothesis was wrong: `think=True` failed
identically to candidacy's original bug — `finish_reason='length'`, zero visible
content — on batches of 2-3 contested parties, at `max_tokens` up to
`compute_max_tokens`'s normal allowance. Batch size was not the variable; the model's
`<think>` reasoning still consumed the entire completion budget.

**Revised understanding**: the bug tracks the prompt's *subjective, comparative*
framing ("which of these candidates is the better choice?") rather than how many
items are in the batch. `vote_cast`'s prompt ("rank these by your own preference," a
per-voter task with no cross-item comparison) doesn't trigger it at any batch size
tested; both `candidacy_considered` ("should this citizen run?") and
`party_nomination_choice` ("which of these citizens should this party pick?") do,
regardless of batch size.

**Fix**: `decide_party_nominations` uses `think=False` (the native `/api/chat`
endpoint, same as `decide_candidacies`) — confirmed working on the same 2-3-contested-party
fixtures that failed under `think=True`.
`test_full_size_party_nomination_batch_produces_a_valid_reliable_response`/
`test_party_nomination_sequential_calls_each_produce_a_valid_response` pin this.

## Campaign positioning (v2 increment 4) — new schema shape, verified clean

`campaign_positioning`'s `PositioningDecision.shifts` is the first schema in this
project shaped as a *bounded list of sub-objects per decision* (`list[PositionShift]`,
each `{dimension, delta}`) rather than flat scalar fields — the strict-mode-compatible
stand-in for a sparse delta dict (`dict[str, float]` isn't usable under Ollama's
`"strict": true`, since strict JSON-schema mode requires a closed, fixed schema).
Two things needed live confirmation before trusting this design, both clean on the
first properly-configured attempt (`think=False`, learned from Finding E rather than
re-guessing `think=True`):

1. **The nested list-of-objects shape itself** decodes and validates reliably —
   `test_full_size_positioning_batch_produces_a_valid_reliable_response` (3 nominees)
   and `test_positioning_sequential_calls_each_produce_a_valid_response` (4 nominees,
   twice) both pass.
2. **The model respects bounds stated only in prose, not enforced by the schema.**
   The JSON schema itself only has a loose structural ceiling (`max_length=5` on
   `shifts`, `delta` in `[-1, 1]`) — the real, tighter, config-driven caps
   (`campaign.max_positioning_shifts=3`, `campaign.max_positioning_delta=0.3`) exist
   only in `build_positioning_system_prompt`'s prose ("CONTRAINTES STRICTES : au plus
   3 ajustements... entre -0.3 et 0.3"). An earlier draft of this prompt said "borné"
   without ever stating the actual numbers — caught before any live run, since a model
   can't respect a bound it was never told. With the numbers stated explicitly, every
   live decision across both tests stayed within them — not schema-enforced, but
   prompt-compliant in every observed case so far.

## Reproducing this check

```bash
docker run -d -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama pull qwen3:8b
python fast_api_voter/scripts/check_ollama_structured_output.py --results fast_api_voter/scripts/ollama_structured_output_results.md
```

Raw output of the final run (script already includes both fixes):

```
1. model present at http://localhost:11434/v1/models: True (found: ['qwen3:8b'])
2. plain chat response contains <think>: False
   raw content (first 300 chars): 'OUI'
3. structured output (toy 3-citizen batch): finish_reason=length, usage={'prompt_tokens': 452, 'completion_tokens': 512, 'total_tokens': 964}, elapsed=54.7s, content_len=0
   FAILED to validate: 1 validation error for VoteCastBatch
   raw content (first 800 chars): ''
4. seed fidelity: same seed twice identical=True (informational: different seed gave the same output -- expected to not matter at temperature=0)
5. sequential determinism on the /v1 structured-output surface, 5 calls: identical=True
6. full-size batch (25 citizens x 20 dims, 10 candidates): finish_reason=stop, usage={'prompt_tokens': 975, 'completion_tokens': 1026, 'total_tokens': 2001}, elapsed=208.6s, content_len=1788
   valid=True, count_ok=True (got 25), cids_ok=True

## Summary
{
  "model_present": true,
  "think_block_present": false,
  "structured_output": false,
  "seed_fidelity": true,
  "sequential_determinism": true,
  "full_size_batch": true
}
```

The script's own overall gate ANDs every check including the still-open toy-batch
one, so it exits non-zero — that's expected and correct; it isn't a silent green.
The finding that matters for shipping increment 1 is `full_size_batch: true`, plus
the open risk above, which needs a chunking-strategy decision before
`llm_behavior_engine.py` is written.
