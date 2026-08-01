# Ollama structured-output verification — v2 increment 1, Lot 0

Verification spike for the approved plan (`abundant-puzzling-bubble.md`), run before
writing `llm_client.py`. Confirms whether Ollama's OpenAI-compatible endpoint
(`/v1/chat/completions` — what `polity_config.yaml`'s `llm.base_url` actually points
at) supports what the production client needs from `qwen3:8b`, the pinned model.

**Setup**: `docker run -d -p 11434:11434 --name ollama ollama/ollama`,
`docker exec ollama ollama pull qwen3:8b` (5.2GB), CPU-only (no GPU on this machine).
Script: `fast_api_voter/scripts/check_ollama_structured_output.py`.

## Result: two real, load-bearing problems found, both fixed and verified; one open risk documented

| # | Check | Result |
|---|---|---|
| 1 | Model present | ✅ pass |
| 2 | `<think>` block in visible content on a trivial prompt | Not present — but see Finding B, hidden generation still consumes budget on some prompts |
| 3 | Seed fidelity | ✅ same seed twice → identical. Different seed → **also** identical, which is *correct*: at `temperature=0`, decoding is greedy/argmax, so seed has nothing to randomize. Not a bug. |
| 4 | Sequential determinism on the real `/v1` structured-output surface | ✅ 5/5 identical calls |
| 5 | Structured output on the real `VoteCastBatch` schema, toy 3-citizen batch | ❌ still fails after both fixes below — see **open risk** |
| 6 | Full-size batch (25 citizens × 20 dims, the actual `max_batch_size`) | ❌ then ✅ after both fixes — see **Finding A** and **Finding B** |

**Bottom line: the production-relevant batch size (25, matching `llm.max_batch_size`)
works reliably once both fixes below are applied. A smaller, non-representative toy
batch does not, for reasons not yet root-caused — see the open risk section.**

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

## Open risk (unresolved): a specific small batch reproducibly fails regardless of token budget

A 3-citizen / 3-candidate toy batch, built the same way as the working 25-citizen
batch (same schema fix, same enumerated-cid-list prompt), **reliably fails**:
`finish_reason: "length"`, `content` = `""`, at `max_tokens` = 512, 1024, **and**
2000 — the failure is identical (same `completion_tokens` count exhausted) at every
budget tested, so this is not a sizing problem. The working 25-citizen batch needed
only ~1026 of a 2200-token budget; this 3-citizen batch exhausts every budget offered
without emitting a single visible character.

Not root-caused. Confirmed NOT the cause: token budget, the `$ref` nesting (already
fixed), or missing cid enumeration (present in this test's prompt too). Candidate
explanations, none confirmed: a degenerate/repetitive generation state specific to
this exact token sequence (fully reproducible at temperature=0 + fixed seed, so not a
fluke); some interaction between short prompts and this model/quantization's hidden
generation behavior that a trivial one-line prompt (check 2) doesn't trigger.

**Practical exposure for this increment**: `population_size: 100` /
`max_batch_size: 25` in the shipped config divides evenly into four equal chunks of
25 — the exact size shown to work reliably. A *different* population size that
leaves a small trailing chunk (e.g. 110 citizens → chunks of 25,25,25,25,10) would
land in untested, possibly-pathological territory. **Recommendation for
`llm_behavior_engine.py`, not yet implemented**: either (a) reject configs where
`population_size % max_batch_size` leaves a small remainder, or (b) chunk into
near-equal groups instead of fixed-size-with-remainder, so no chunk is ever much
smaller than `max_batch_size`. Needs a decision before increment 1's chunking lot,
not just for this spike.

## Wall-clock (measured, CPU-only, no GPU)

- Toy 3-citizen batch: ~55-60s per call (even the failing ones — the budget is spent
  either way).
- Full 25-citizen batch (20 dims, 10 candidates): ~205-225s (~3.5-4 min) per call.
- A full 30-year run needs 4 batches × 8 presidential elections = 32 such calls ⇒
  roughly **2-2.5 hours** per run at this batch size, serialized (required for
  reproducibility per `llm_batching_determinism_results.md`'s earlier finding).
  Consistent with the design doc's own framing (§15bis.0: the cost is time, not
  money) but should be treated as a real, planned number, not a surprise later.

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
