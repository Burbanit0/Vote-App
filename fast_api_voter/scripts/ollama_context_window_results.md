# Ollama context window (`num_ctx`) — a real, previously-undocumented reliability bug

Run 2026-08-18 (dated 2026-08-17 in local logs), during the v6b Lot 4 acceptance run
(`sortition-llm-8y`, seed=42, `chunk_voters(..., 3)`, `_VOTE_THINK_TOKEN_ALLOWANCE=4000`).
Root-caused directly against `ollama-polity`'s own container logs — not inferred, not
guessed.

## Symptom

`vote_cast` (dt=1, `think=True`, OpenAI-compat `/v1/chat/completions`) failed with
`finish_reason='length'` on one specific chunk, 3/3 attempts in a row, exhausting
`max_batch_replays=2` and aborting the run. A fresh, independent sweep of all 34 real
chunks from that exact tick (1 pass, then 3 reps — 136 total attempts) reproduced **zero**
truncations, ruling out a systemic per-chunk content bug and pointing at something
environmental.

## Root cause, confirmed via `docker logs ollama-polity`

Every request in the failure window shows:

```
slot   operator(): id  0 | task 37335 | new prompt, n_ctx_slot = 4096, n_keep = 4, task.n_tokens = 2277
...
slot   operator(): id  0 | task 37335 | slot context shift, n_keep = 4, n_left = 4091, n_discard = 2045
...
slot   operator(): id  0 | task 37335 | slot context shift, n_keep = 4, n_left = 4091, n_discard = 2045
...
slot print_timing: id  0 | task 37335 | n_decoded =   5532, ...
slot      release: id  0 | task 37335 | stop processing: n_tokens = 3902, truncated = 1
```

**`n_ctx_slot = 4096` on every single request** — Ollama's own hard-coded default when no
`num_ctx` is specified, confirmed identical across every request in this whole project's
history (`llm_client.py` never sets `num_ctx` anywhere). `compute_max_tokens(3) +
_VOTE_THINK_TOKEN_ALLOWANCE = 1716 + 4000 = 5716` — combined with a real prompt of
~2277 tokens, this **structurally exceeds** a 4096-token context the moment the model's
own reasoning runs past ~1800 tokens.

When that happens, llama.cpp's own "context shift" mechanism silently evicts the oldest
2045 tokens (`n_keep=4` — everything is discardable except the first 4 tokens) to keep
generating — which discards the system prompt's own instructions and the model's earlier
reasoning mid-generation. The model then loses track of its task, never emits a valid stop
token, and burns the entire `num_predict` budget (`n_decoded=5716` exactly, both failing
calls), returning `finish_reason='length'`.

This is why the bug is **rare but real**: most completions finish in 85-360 tokens, well
under the ~1800-token headroom before a context shift would trigger — but any call whose
reasoning runs long enough hits the ceiling, gets its context corrupted, and reliably fails
every retry (since the same input, same 4096 ceiling, and a now-corrupted mid-generation
state make the pathology likely to recur).

## The fix, and what did NOT work

- **`options.num_ctx` on the OpenAI-compat endpoint (`/v1/chat/completions`) is silently
  ignored.** Confirmed directly: sending `"options": {"num_ctx": 16384}` at the top level of
  the request body — even against a freshly-unloaded model — left `ollama ps`/`n_ctx_slot`
  at 4096. Ollama's OpenAI compatibility layer does not forward this field.
- **`options.num_ctx` on the native endpoint (`/api/chat`) works correctly** — confirmed via
  `ollama ps` showing `CONTEXT 16384` after a request with it set. But `vote_cast` needs
  `think=True`, which this project's own `OllamaJsonClient` docstring already documents as
  requiring the OpenAI-compat endpoint (the native endpoint's `think=True` combination was
  separately found, earlier this session, to produce diverse-but-incorrect batch-collapse
  behavior — not a usable substitute).
- **Resolved fix: `OLLAMA_CONTEXT_LENGTH` as a container-level environment variable.**
  Context length is a model-*load*-time parameter of the underlying llama.cpp server
  process, not a per-request one — it applies uniformly to every request against that
  loaded model regardless of which API surface (`/v1/chat/completions` or `/api/chat`)
  issues it. Setting it server-wide is therefore the only lever that reaches the
  OpenAI-compat path `vote_cast` (and every other `think=True` decision type) depends on.

**`ollama-polity` was recreated 2026-08-17 with `OLLAMA_CONTEXT_LENGTH=16384`** (up from
the implicit default of 4096), preserving the existing `ollama-polity-data` named volume
(model weights, no re-download) and every other existing setting
(`OLLAMA_FLASH_ATTENTION=false`, `--gpus all`, port `11434`):

```
docker rm -f ollama-polity
docker run -d --name ollama-polity --gpus all \
  -p 11434:11434 \
  -v ollama-polity-data:/root/.ollama \
  -e OLLAMA_FLASH_ATTENTION=false \
  -e OLLAMA_CONTEXT_LENGTH=16384 \
  ollama/ollama
```

Confirmed post-fix, replaying the exact chunk that had reliably reproduced the failure:
`n_ctx_slot = 16384`, `stop processing: n_tokens = 5784, truncated = 0`, no context-shift
event, `finish_reason='stop'`.

## Consequence for every prior finding in this project

**This is a container-level setting, not a code change** — no line in `llm_client.py` or
anywhere under `api/domain/polity/` changed. It applies uniformly to every decision type,
both `think=True` (OpenAI-compat) and `think=False` (native) paths, since context length is
a property of the loaded model instance, not of which endpoint a given request happens to
use. Every prior live-LLM finding this session and earlier (batching determinism,
`campaign_positioning`'s misalignment bug, `chamber_deliberation`'s own chunk-size finding,
`vote_cast`'s batch-collapse fix) was measured against an Ollama instance silently capped
at 4096 tokens of context — none of those findings are invalidated by this fix (they were
about batch-size/content reliability, a separate axis from context truncation), but a
config with a large system prompt, a large batch, and/or a large `think`-token allowance
that previously "worked" may simply not have been exercised past the 4096-token ceiling.
If `ollama-polity` is ever recreated without `OLLAMA_CONTEXT_LENGTH` set, this exact bug
returns silently — there is no code-level guard against it, since Ollama gives no error
when a request's effective budget exceeds context; it degrades into the context-shift
pathology described above instead.

## Recommendation for a future lot

`polity_config.yaml`'s own `llm:` comment block should carry a note that `ollama-polity`
requires `OLLAMA_CONTEXT_LENGTH` set server-side (not expressible as a per-request option
on the OpenAI-compat path this project's `think=True` decision types depend on). Not
applied as a code change in this session — this results doc plus the inline comment added
alongside `llm.base_url` are the record for now.
