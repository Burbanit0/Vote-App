# ADR-001: LLM serving layer — stay on Ollama, do not switch to native llama-server (yet)

**Status**: Accepted
**Date**: 2026-08-19
**Context**: Polity v6b acceptance-run reliability investigation
(`fast_api_voter/scripts/llm_batching_determinism_results_gpu.md`)

> **Where the supporting evidence lives**: the spike's own protocol, full
> logs and script are committed on branch `spike/llama-server-cache-prompt`
> (`fast_api_voter/scripts/llama_server_spike/RESULTS.md` and
> `test_cache_prompt_loaded.py`), which is deliberately NOT merged into the
> main line — see Consequences. That branch must be checked out to read
> them; this ADR summarizes the parts the decision actually rests on, so it
> stands on its own without it.

## Context

Three distinct GPU/Ollama-level reliability bugs were found in one investigation
session while trying to complete the v6b acceptance run (`sortition-llm-8y`):

1. **Context-shift**: `num_ctx` silently ignored on Ollama's OpenAI-compat
   endpoint — fixed at the container level (`OLLAMA_CONTEXT_LENGTH=16384`).
2. **Cold-start non-determinism**: a freshly-loaded model's first inference
   pass is measurably non-deterministic — fixed via an application-level
   warm-up call plus `OLLAMA_KEEP_ALIVE=60m`.
3. **Cross-request prompt-cache interaction**: `campaign_positioning` batches
   intermittently hit `finish_reason='length'` (a `think=True` generation
   that never terminates). Root-caused via Ollama's own public source
   (`llm/llama_server.go`): `cache_prompt` is hardcoded `true` internally,
   with **no per-request override anywhere in Ollama's API** — `llama.cpp`
   itself (which Ollama wraps) *does* expose this as a genuine, documented
   per-request option on its own native server.

Two of these three bugs are specifically artifacts of Ollama's own
wrapper/compat layer, not of the model or the GPU. That pattern — plus the
fact that `llama-server` offers a real lever (`cache_prompt`) that Ollama
does not — raised a genuine question: is Ollama, as currently configured,
the right serving layer for this workload (`think=True`, long reasoning,
prompts that are never exactly repeated within a run), or would switching
to native `llama-server` (or accelerating the already-scoped vLLM switch,
§15bis.6) avoid this whole class of problem rather than patching around it
bug by bug?

## Decision

**Stay on Ollama for now, with the shipped mitigations in place
(`OLLAMA_CONTEXT_LENGTH`, `OLLAMA_KEEP_ALIVE`, the application-level
warm-up, and a bounded `--max-batch-replays` for genuinely stochastic
misalignment failures). Do not switch to native `llama-server` at this
time.**

This is deliberately a "not yet," not a "never" — the question is expected
to be revisited if this bug class keeps costing real time, or once vLLM
(already scoped, §15bis.6) gets its own live verification.

## Why

A timeboxed spike (3h budget, concluded in 14 minutes) tested whether
`llama-server`'s per-request
`cache_prompt: false` control eliminates bug 3, under the condition that
actually produced it in production: a KV-cache already loaded with several
distinct prior prompts, not an empty cache (an earlier, narrower version of
this same investigation had already shown — and this project's own results
doc corrects — that an empty-cache test tells you nothing about the
production failure mode).

**The spike could not reproduce the bug on `llama-server` at all**, under
two separate load protocols (a light 4-prompt load and a heavy, realistic
10-prompt load with substantial per-prompt generations), using the exact
same GGUF weights copied directly out of Ollama's own blob store (no
quantization-mismatch confound) and the exact real failing prompt
reconstructed from the production run's own journal. 6/6 identical
submissions of the failing prompt succeeded cleanly on `llama-server`,
against a documented, reproducible OK/FAIL/FAIL pattern for the same prompt
on Ollama.

This means the spike's central question — **does `cache_prompt=false` fix
bug 3?** — was **never actually answered**. There was nothing to fix: the
bug didn't manifest on `llama-server` in this protocol at all. Per the
pre-declared stop criterion (agreed before the spike started: either the
per-request control demonstrably eliminates the bug, or it doesn't — stop
either way, don't chase the interesting tangent), this is an inconclusive
result on the original question, not a positive one.

### Why "inconclusive" still resolves to "don't switch yet," not "switch anyway"

An inconclusive spike is not, on its own, grounds to change the serving
layer. Weighed against each other:

- **What a switch would cost, concretely, known and unverified in different
  proportions**: `VllmJsonClient` has *never* been executed against a live
  server (§15bis.6's own standing status) — switching to vLLM trades a
  partially-characterized problem for a completely uncharacterized one.
  Switching to `llama-server` instead is less unknown (this spike is real,
  if limited, live evidence) but still means: a new client implementation
  and deployment path with **zero** of this project's own committed
  reliability findings (`ollama_structured_output_results.md`,
  `llm_batching_determinism_results_gpu.md`, the batch-size/reliability
  spikes for every LLM decision type) verified against it — every one of
  those would need to be re-earned from scratch, not assumed to transfer.
- **What staying costs**: bug 3 is now understood well enough to mitigate
  operationally (a bounded replay absorbs the risk for the *stochastic*
  misalignment failures this project has also observed — separately from
  bug 3's specific "identical resubmission" degenerate pattern, which the
  replay mechanism does NOT protect against, since it resubmits the exact
  same bytes). Two of the three bugs found this session are already fixed
  outright (context-shift, cold-start); the third has a real, if partial,
  mitigation and a live-verified absence of a fix path via `llama-server`
  specifically (this spike), not an absence of *any* investigation.
- **The evidence this spike DID produce is real, even if not what it set
  out to prove**: `llama-server`'s own implementation, same weights, same
  failing prompt, twice under different load intensities, never
  reproduced the bug. That is weak evidence the failure is specific to
  something in Ollama's own orchestration layer (batching internals, its
  own cache-pool management) rather than a property of llama.cpp or Qwen3
  in general — which is informative for *whether this class of bug is
  worth architecting around at all* even before a serving-layer switch is
  on the table, but it is not proof `llama-server` is immune, and the
  spike's own timebox was hit on the reproduction step, not on exhausting
  every variant that might have reproduced it.

Given a real, partial mitigation already in place for the mechanism that
*is* well understood, and no confirmed, live-verified alternative ready to
absorb this workload's actual reliability requirements, switching now would
trade a partially-mitigated, well-characterized problem for an
unmitigated, barely-characterized one — the same reasoning this project's
own `VllmJsonClient` status already established for vLLM, now extended to
`llama-server` on the strength of one spike's worth of evidence.

## Alternatives considered

- **Switch to native `llama-server` now.** Rejected for this round: the
  spike meant to justify it (does `cache_prompt` control actually fix the
  bug) came back inconclusive, not positive — there is no confirmed benefit
  to weigh against the real cost of standing up a new, unverified serving
  path.
- **Accelerate the vLLM switch instead.** Rejected for the same reason it
  was rejected earlier in this investigation: `VllmJsonClient` remains
  completely unverified against a live server; nothing about this
  investigation changed that status, and it carries the same
  "uncharacterized problem" cost `llama-server` does, without even this
  spike's partial live evidence.
- **Do nothing beyond the shipped mitigations, revisit if the bug recurs
  at real cost.** **Accepted** — this is the decision above.

## Consequences

- The v6b acceptance run remains blocked on Ollama's own reliability, not
  on an architecture decision — the next attempt should account for bug 3's
  real behavior (a bounded replay of the *same* prompt does not reliably
  recover from this specific failure mode; see
  `llm_batching_determinism_results_gpu.md`'s own correction section) when
  deciding how to proceed, rather than assume `--max-batch-replays` alone
  resolves it.
- This decision should be revisited if: (a) this bug class (or a
  variant of it) causes another real acceptance-run failure, at which point
  a longer, better-resourced `llama-server` spike (or a first real vLLM
  verification) becomes easier to justify against accumulated cost; or
  (b) vLLM gets its own live verification for unrelated reasons, at which
  point it — not `llama-server` — becomes the natural comparison point,
  since it is already the project's own scoped, intended target (§15bis.6).
- `fast_api_voter/scripts/llama_server_spike/` (the spike's own script and
  `RESULTS.md`) stays on its own branch
  (`spike/llama-server-cache-prompt`), not merged into the main pipeline —
  per the instruction that produced this spike, it was never meant to touch
  `develop` regardless of outcome.
