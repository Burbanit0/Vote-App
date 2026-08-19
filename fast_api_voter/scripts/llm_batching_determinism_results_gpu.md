# LLM batching determinism — protocol result (GPU)

Verification protocol for design doc §15bis.5 / DEMARRAGE-polity-v0.md §5.
Run 2026-08-17, immediately after recreating `ollama-polity` with
`--gpus=all` (RTX 5070 Ti, driver 591.86) — the first time this exact
protocol has been run against a GPU-backed Ollama instance. Directly
comparable to `llm_batching_determinism_results.md` (CPU, run 2026-07-31):
same script, same model, same options, same batch sizes. **This document
does not replace or invalidate the CPU one** — both measurements stand,
each describing the backend it was run against.

**Setup**: Ollama, GPU (`--gpus all`, RTX 5070 Ti), `OLLAMA_FLASH_ATTENTION=false`
(disabled as a separate, already-applied fix earlier this session — see the
`campaign_positioning` reliability investigation for why), `OLLAMA_NUM_PARALLEL=8`
(matching the CPU protocol's concurrency setup so the comparison is
apples-to-apples), model `qwen2.5:0.5b` (pinned, not `:latest`),
`temperature=0`, fixed `seed=42`, one fixed prompt (the same mock
citizen-vote-factors prompt), `num_predict=64`.
Script: `fast_api_voter/scripts/check_llm_batching_determinism.py` (reused
unmodified — no new tooling needed).

## Result: the B2 concern reproduces on GPU too, unchanged in kind

| Check | CPU (2026-07-31) | GPU (2026-08-17) |
|---|---|---|
| batch_size=1, 10 consecutive runs | identical | **identical** |
| batch_size=1, before vs. after a full container restart | identical | **identical** |
| batch_size=5 | NOT identical | **NOT identical** |
| batch_size=25 | NOT identical | **NOT identical** |
| batch_size=50 | NOT identical | **NOT identical** |
| **Overall** | FAIL | **FAIL** |

**The non-determinism does not disappear on GPU, and it does not change in
kind** — sequential, unbatched calls (`batch_size=1`) remain perfectly
reproducible, including across a cold container restart; concurrent
batching (`batch_size>=5`) still produces divergent completions from
otherwise-identical requests. This is the same qualitative shape as the CPU
result, on the same script, same model, same seed.

What is new information this run, not available from the CPU doc alone —
the **degree** of divergence, measured as distinct outputs per batch:

| Batch size | Distinct outputs (of N) |
|---|---|
| 5 | 4 |
| 25 | 5 |
| 50 | 12 |

Divergence does not scale linearly with batch size (12/50 is a *smaller*
fraction than 4/5), consistent with batching-induced numerical
non-associativity being a property of *how many requests happen to land in
the same forward pass together*, not a fixed per-request corruption rate.

Example (batch_size=5, same prompt, same options, only the batch differs —
first ~180 characters of each):

```
[0] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. Understanding the
     candidates' positions on issues such as social justic"
[1] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. Understanding these
     differences can help the voter make an informed dec"
[2] (identical to [1])
[3] (identical to [1])
[4] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. If the voter is
     influenced by their beliefs and values, they might be m"
```

Likely cause: unchanged from the CPU finding — floating-point
non-associativity in batched matrix multiplication, where concurrent
requests change the numerical reduction order inside the same forward
pass. This is a documented property of batched inference generally
(llama.cpp/Ollama on either backend), not a CPU-specific artifact and not
something the GPU switch introduced. Flash attention was disabled for this
run (see Setup); whether flash attention *on* changes the degree of
batching divergence was not tested here — this protocol tests concurrent
identical-content batching, a different mechanism from the single-call
content-degeneracy issue flash attention was disabled to fix.

## Consequence for the design

Unchanged from the CPU result — both decisions in `polity_config.yaml`
remain correctly conservative, now confirmed on the backend the project
actually runs on:

- `batch_sharding: static` (§15bis.4a) — still correct; this result shows
  *any* concurrent batching breaks reproducibility on GPU too, not just
  dynamic reassignment.
- `parallel.intra_run_workers: 1` (§15bis.3) — still correct; intra-run LLM
  call parallelism would still break byte-for-byte reproducibility (Lot 8)
  on GPU, exactly as it would on CPU.

**Open question, still not resolved by this run** (carried over verbatim
from the CPU doc, unchanged): whether a *fixed-size* static batch (same
citizens, same batch composition, called the same way every run) is
internally deterministic even though *concurrent* calls aren't. This run,
like the CPU one, only tested identical-content concurrent batches — it
does not test the actual v2+ scenario (same composition, different
per-citizen content, called the same way run over run).

## Reproducing this check

```bash
docker exec ollama-polity ollama pull qwen2.5:0.5b   # if not already present
python fast_api_voter/scripts/check_llm_batching_determinism.py --save before.json
docker restart ollama-polity   # wait for it to come back up
python fast_api_voter/scripts/check_llm_batching_determinism.py --compare before.json
```

Requires `ollama-polity` running with `--gpus=all` and
`OLLAMA_NUM_PARALLEL=8` (the shipped production container does not set
`NUM_PARALLEL`, which defaults to 1 — that's correct for production, where
`intra_run_workers: 1` means only one request is ever in flight at a time,
but it would mask this protocol's batching test, which needs the server
able to accept concurrent requests to exercise the failure mode at all).

## Cold start vs. warm: a second, distinct determinism gap (2026-08-18)

Everything above tests `qwen2.5:0.5b`, `num_predict=64`, no `think`, no
structured output — a materially different regime from what production
actually runs (`qwen3:8b`, `think=True` for most decision types, long
chain-of-thought before the JSON answer, `response_format` strict). This
section covers a gap the protocol above never exercised: is a single,
**isolated, non-concurrent** production call — the "batch_size=1: identical"
case above — actually reproducible for the real model and the real
`think=True` request shape? It is not, but only for the first call after a
cold model load.

**How this was found**: the v6b acceptance run failed a third time in
`cast_votes` with the same `finish_reason='length'` signature already fixed
once for `decide_campaign_positioning` (§A.3 of the working session), this
time exhausting all `max_batch_replays` attempts on the same chunk. An
attempt to replay the chunk that had originally failed — 170 attempts across
the 34 real dumped chunks, 3 reps each plus a fresh single pass — reproduced
it zero times. Investigating why turned up something more fundamental:
running the identical config twice from a fresh process and hashing every
`complete_json` call showed that **call 1 — the very first LLM call of the
pipeline (`candidacy_considered`) — has byte-identical system/user prompt
hashes between the two runs, but a different raw response.** Calls 2-5
(other citizens' independent candidacy decisions) then matched exactly
between both runs; from call 6 (`decide_campaign_positioning`) onward the
two runs had genuinely diverged in both prompt content and outcome —
consistent with call 1's differing decision changing the final nominee
count (observed directly: one fresh run produced 4 nominees, another
produced 5, for the same seed/config).

**Isolated confirmation** (`test_isolated_think_determinism.py`, ad hoc,
not committed as a script — reused two already-dumped real production
prompts, `decide_campaign_positioning`'s and `cast_votes`'s, called 8×
sequentially with `think=True`, raw output hashed each time):

| Prompt | Model state at rep 1 | Result |
|---|---|---|
| positioning | cold (`ollama ps` empty just before) | rep 1 differs; reps 2-8 all identical to each other |
| vote_chunk0 | already warm (positioning's own reps just ran) | 8/8 identical |
| positioning, re-run | already warm (from the run above) | 8/8 identical, and the stable hash matches reps 2-8 of the cold run exactly |

Once warm, the model is perfectly, repeatedly deterministic for identical
input — 16/16 matched hashes across every warm call observed. Only the
first call after a genuinely cold model load diverges. This is a known
class of GPU-inference behavior (kernel-selection/autotuning heuristics
that can pick a different execution path on the first invocation of a
freshly loaded model), not a general property of the model or of `think=True`
generation.

**Two follow-up checks, both load-bearing for the fix:**

1. **Is `keep_alive` honored on `/v1/chat/completions` (the endpoint every
   `think=True` call uses)?** No. Sending `"keep_alive": "90s"` in the
   request body left `ollama ps`'s `UNTIL` at the ~5-minute default
   afterward — silently ignored, the same failure mode already documented
   for `num_ctx` on this endpoint
   (`scripts/ollama_context_window_results.md`). A per-request fix on this
   endpoint is not available; server-side default (`OLLAMA_KEEP_ALIVE`,
   container-level) is the only lever, same pattern as the `num_ctx` fix.
2. **Does a fixed warm-up call, applied after a forced-cold state, reliably
   stabilize the following real call?** Yes, but not by reproducing the
   same hash as an unrelated warm history — "warm" is path-dependent on
   what specifically warmed the model, not one universal state. What
   matters for reproducibility is a *consistent procedure*, which this
   does provide: 4 independent forced-cold cycles (unload via `keep_alive=0`
   on the native endpoint, confirmed empty via `ollama ps`, then one
   throwaway `think=True` warm-up call, then the real positioning call)
   produced the **same** hash (`fe47e16836476287`) all 4 times — distinct
   from, but just as stable as, the same-prompt-repeated warm reference
   above.

## Consequence for the design (this section)

- `_warm_up_llm_client` (`run_polity_simulation.py`) issues one throwaway
  call through each endpoint shape (`think=True` and `think=False` are
  genuinely different Ollama request paths — see `llm_client.py`'s own
  module docstring) inside `_llm_client_scope`, before any real decision
  runs, on a real owned client only (never on an injected test client).
  Best-effort: any failure is logged and swallowed, never allowed to abort
  a run. This closes the start-of-run cold-start case, confirmed above.
- **Mid-run cold start — closed separately, by a container-level env var,
  not by `_warm_up_llm_client`.** A real run's own gaps between calls (a
  quiet tick, unusual latency) could in principle exceed Ollama's idle
  `keep_alive` timeout (~5 min default) at any point after the start-of-run
  warm-up, and since per-request `keep_alive` is confirmed silently ignored
  on the endpoint that matters (above), no application-side fix reaches
  this case. `ollama-polity` was recreated (2026-08-18) with
  `OLLAMA_KEEP_ALIVE=60m` added to its existing env vars (image, port,
  named volume, GPU device request, `OLLAMA_FLASH_ATTENTION=false`, and
  `OLLAMA_CONTEXT_LENGTH=16384` from the `num_ctx` fix all preserved
  unchanged — same recreate procedure as that fix). `60m` chosen over `-1`
  (never unload) deliberately: comfortably covers any realistic inter-call
  gap in a real run (15-90s in normal operation) while still releasing the
  ~8.4GB of VRAM after a genuine pause (end of run, an interrupted dev
  session) rather than pinning it indefinitely against a GPU that may run
  other workloads later. Verified directly: `docker exec ollama-polity
  ollama ps` showed `CONTEXT 16384` and `UNTIL 59 minutes from now` after a
  real request — both fixes active simultaneously, model weights confirmed
  intact post-recreation (`ollama list`, all three pulled models present).

  **This is complementary to the warm-up call, not redundant with it — the
  two protect different risk windows.** `_warm_up_llm_client` protects
  exactly one moment: the very first LLM call of a run, when the container
  (or the model within it) may be genuinely cold. `OLLAMA_KEEP_ALIVE=60m`
  protects every moment *after* that: it prevents the model from ever
  going cold again mid-run purely from an idle gap, which the warm-up call
  — a one-shot action taken once at start — cannot do anything about on
  its own. Neither one covers the other's window: a long `keep_alive`
  alone does nothing for a container that was *just* started or recreated
  (the model still has to load and take its one non-deterministic pass for
  the first time); a warm-up call alone does nothing to stop a real idle
  timeout from reintroducing the exact same problem an hour into an
  8-hour acceptance run.
- Every downstream failure this project has chased under a "budget
  shortfall" framing (`_POSITIONING_THINK_TOKEN_ALLOWANCE`,
  `_VOTE_THINK_TOKEN_ALLOWANCE`) may have been partly measuring this
  cold-start effect rather than (or in addition to) genuine content-driven
  token-budget insufficiency — a longer, non-terminating cold-start
  generation would present with the identical `finish_reason='length'`
  signature. Those allowance increases are not wrong (a real generation
  running long is still worth budgeting for), but the warm-up fix should
  be evaluated on its own before recalibrating any allowance further.

## A third mechanism, found live: cross-request prompt-cache reuse (2026-08-18)

With both fixes above in place, a fresh dump attempt of the v6b acceptance
config still failed — `decide_campaign_positioning` hit
`finish_reason='length'` 3/3 times in a row on the same prompt shape
already fixed once (task tokens=3989, decoding to 9775/9836, right at the
already-raised ceiling), exhausting `max_batch_replays`. The model was
confirmed warm throughout (`ollama ps`), so this is not the cold-start case
above. Docker logs showed the failing attempts preceded by
`srv load: - looking for better prompt, base f_keep = 0.290, sim = 1.000` —
a low-confidence partial match against Ollama's cross-request prompt cache
(a pool of recently-run, *unrelated* prompts, logged elsewhere as
`cache state: 11 prompts`). Every subsequent clean/fast rep of the exact
same prompt showed a high `f_keep` (0.7-1.0). Replaying the same known
prompt immediately after: rep 1 reproduced the failure, reps 2-8 all
converged to one stable, fast, clean output — `vote_chunk0` was 8/8 stable
throughout. This raised the hypothesis that a low-quality cache match
corrupts the generation into a long, non-terminating trajectory.

**Two follow-ups, before spending more GPU cycles chasing this:**

1. **Source-checked, not speculated**: does Ollama expose any per-request
   way to control prompt-cache reuse? No. `api/types.go`'s `Options`
   struct has no `cache_prompt`/`no_cache`/`cache_reuse`-shaped field
   anywhere. More decisively, `llm/llama_server.go` — Ollama's own internal
   call to the underlying llama.cpp server — sets `CachePrompt: true`
   (completion) and `"cache_prompt": true` (chat) **hardcoded**, with no
   configuration path from the public API. There is no flag to test or
   use; the mechanism is unconditionally on for every request, by design,
   with no override available short of bypassing Ollama's own wrapper
   entirely.
2. **Causality test, not just correlation, at near-zero GPU cost**: since
   `cache_prompt` can't be disabled, tested instead whether a deliberately
   *low* `f_keep` alone is sufficient to corrupt a generation, using cheap
   `think=False`, `max_tokens=50` calls (3 independent trials, each priming
   the cache with a distinct real long prompt, then immediately sending a
   never-before-seen short call: one sharing the prime's exact system-
   prompt text as a genuine prefix — mirroring production's real shape,
   where successive calls share large common system-prompt boilerplate —
   and one an unrelated control). **Result: all 6 trials (3 shared-prefix,
   3 control) finished cleanly at `done_reason='stop'` in 1.3-1.7s, with no
   distinguishable difference between the shared-prefix and control arms.**
   A low `f_keep` alone does **not** reproduce the failure on a cheap,
   short, `think=False` call. The trigger requires an interaction with long
   `think=True` reasoning generation — `f_keep` is a correlated symptom
   (both track "how novel is this exact token sequence"), not, on its own,
   the causal mechanism. The precise condition under which a long-reasoning
   generation fails to terminate naturally remains unisolated after this
   round; further narrowing would need controlled think=True trials, which
   are the expensive kind this test was designed to avoid pending a
   decision on whether that investment is worth it.

**Pragmatic mitigation, applied now, documented explicitly as mitigation,
not a fix**: the next relaunch uses `--max-batch-replays 5` (6 total
attempts per batch) rather than the `2` used in the run that failed.
Reasoning: the worst streak actually observed in production was 3
consecutive failures on one chunk; the settling behavior observed above
(a bad attempt is very often followed immediately by a stable, clean one)
suggests recovery typically happens within 1-2 extra tries once triggered
at all. `5` extra replays is roughly double the worst observed streak —
deliberately generous margin, not a guess at the minimum, and still
strictly bounded per `LlmResponseError`'s own design philosophy (a
malformed/misaligned response is never silently retried forever; every
replay is logged to `replays.log`, never journaled). This absorbs the
known risk while the root mechanism stays open — it does not claim the
problem is resolved.

**Open, unresolved question this round surfaces rather than answers**:
this is the third distinct Ollama/GPU-level reliability issue found in one
investigation (context-shift from a silently-dropped `num_ctx`, cold-start
non-determinism, and now this cache-interaction effect) — each traced to a
different mechanism, two of them (context-shift, cache reuse) specific to
behavior inside Ollama's own wrapper layer around llama.cpp, not the model
or GPU themselves. Whether Ollama, as currently configured, remains the
right serving layer for this specific workload (`think=True`, long
reasoning, prompts that are never exactly repeated within a run) — versus
a native `llama-server` (which exposes `cache_prompt` as a genuine,
documented per-request option) or the vLLM switch already scoped in this
project's own roadmap (§15bis.6) — is a real question this investigation
raises but does not settle, and is a call for the project owner to make,
not an engineering conclusion to smuggle into a bug-fix commit.
