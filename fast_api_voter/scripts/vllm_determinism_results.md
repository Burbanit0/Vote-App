# vLLM batching determinism — protocol result

Verification protocol for design doc §15bis.5 (batch-composition determinism)
against §15bis.6's vLLM path, using `scripts/check_vllm_batching_determinism.py`
(written 2026-08-15 alongside the v4 vLLM switch, never run until today — no
GPU/vLLM server existed in this project's environment before now). Run
2026-09-05, first native-Ubuntu vLLM session, immediately after the platform
blocker that stopped the 2026-08-30 attempt (`RuntimeError: UVA is not
available`, confirmed upstream WSL2/Docker Desktop bug) was retested and found
resolved — this environment moved off WSL2 on 2026-09-03/04, one of the two
explicit reopening conditions recorded for that block.

**Setup**: vLLM `v0.28.0`, `Qwen/Qwen3-8B-AWQ` (pinned HF revision
`4da05a8edb...`), `awq_marlin`, `--served-model-name qwen3:8b`,
`--reasoning-parser qwen3`, RTX 5070 Ti (16GB), `temperature=0`, `seed=42`,
real production request shape (`VOTE_CAST_JSON_SCHEMA`, dereferenced via
`_inline_refs`, `think=False`) — see `docker-compose.llm.yml`.

## Two config bugs found and fixed before this protocol could even run

1. **`--max-model-len 8192` (the value shipped, unverified, since the v4
   switch) is too small.** `compute_max_tokens(25)`=3036 plus a real 25-citizen
   prompt (~5157 input tokens) already exceeds it by design;
   `decide_campaign_positioning`'s own output budget alone
   (`_POSITIONING_THINK_TOKEN_ALLOWANCE`=8000 + `compute_max_tokens`, up to
   9836) exceeds it regardless of input. Confirmed live via `HTTP 400`s on
   `test_polity_vllm_live.py`.
2. **8192 → 24576 in one step is unstable on this 16GB card.** vLLM's own
   free-memory auto-profiling was not run-to-run reproducible at that setting:
   one cold start reserved 5.93 GiB for KV cache and booted fine; a plain
   `docker compose restart` later reserved 8.02 GiB for the *same* flag,
   leaving 37 MiB free, and the engine died with `torch.OutOfMemoryError`
   during its own CUDA-graph/sampler warmup — not under any load from this
   script. Settled on `--max-model-len 16384` (still clears both budgets above
   with real headroom) plus an **explicit** `--gpu-memory-utilization 0.80`
   (replacing vLLM's own auto-tuned ~0.92 default) — verified stable across
   4 consecutive restarts, each landing at ~2.6-2.7 GiB free, not 37 MiB.

`test_polity_vllm_live.py`'s `test_think_true_actually_produces_reasoning`
also needed a fix unrelated to either bug above: it checked
`message.reasoning_content`, a field name from the v4 switch's
written-but-never-run docs; live vLLM 0.28.0 actually names it
`message.reasoning`. Reasoning was never actually a silent no-op (R1) — the
test was checking the wrong key.

## Result: B2 (temperature=0 + pinned model ⇒ determinism) holds under vLLM

| Check | Result |
|---|---|
| batch_size=1, 10 consecutive sequential calls | **identical** |
| batch_size=1, 5, 25, 50 (concurrent, `asyncio.gather`) | **identical within each batch, and to the batch_size=1 reference** |
| batch_size=1 output, before vs. after a full container restart | **identical** |
| **Overall** | **PASS** |

This is the opposite finding from Ollama's own version of this same protocol
(`llm_batching_determinism_results_gpu.md`): there, `batch_size>=5` reliably
diverged from the sequential reference (llama.cpp's multi-threaded
floating-point reduction order is not batch-invariant). Here, vLLM's
continuous-batching scheduler — the specific mechanism §15bis.4c worried
about, a different code path from llama.cpp's threading — produced
byte-identical output at every tested concurrency level, including 50
simultaneous in-flight requests sharing the same server-side batch.

One operational note, not a determinism finding: the very first concurrent
burst sent immediately after `Application startup complete` (before any
single warm-up request) twice dropped with `httpx.ReadError` — a connection
established before the server's request-handling path was fully warm, not a
model or batching issue. Retrying the identical call immediately after
succeeded every time, matching production's own existing pattern
(`run_polity_simulation.py` already issues a throwaway warm-up call before
real decisions, for a similar reason on the Ollama path). Does not affect the
determinism verdict above, since every measurement here is post-warm-up.

## What this does and does not license

**Confirmed**: the vLLM path is no longer blocked by environment, and its
core determinism guarantee — the one thing B2 requires — holds under real
concurrent batching, which Ollama's does not.

**Not yet re-verified** (§3 axis b in `plan-vllm-switch-readiness.md`,
unchanged by today): every reliability calibration in this codebase
(`_POSITIONING_THINK_TOKEN_ALLOWANCE`, `_VOTE_CAST_MAX_CHUNK_SIZE`,
`_CHAMBER_MAX_CHUNK_SIZE`, the ranking-ambiguity and
`chamber_position==sincere_position` fixes) was measured against Ollama's
un-quantized GGUF `qwen3:8b`, not vLLM's AWQ `Qwen3-8B-AWQ` — different
weights, not just a different server. `test_a_short_live_run_produces_a_valid_journal`
and `test_two_short_live_runs_with_the_same_seed_are_byte_identical` both hit
the **already-documented** `blank=1`+non-empty-`ranking` cross-field defect
(`cache_recycle_chunk_size_tension_findings.md`, first found on Ollama,
deterministic at temp=0, survives replay) — reproducing under vLLM too, which
is informative (it confirms the bug is in model behavior, not an
Ollama-serving-layer artifact) but does not itself validate axis (b).
`provider` stays `ollama` in `polity_config.yaml` pending that separate,
not-yet-authorized decision.
