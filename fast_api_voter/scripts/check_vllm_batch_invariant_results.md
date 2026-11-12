# `VLLM_BATCH_INVARIANT`: fixes Phase 2's correctness finding, costs more than it saves

Follow-up to Phase 2 (`plan-flagship-30y-run.md`,
`check_intra_run_concurrency_determinism_results.md`), investigated before starting Phase 7:
can the underlying batch-composition sensitivity be fixed, rather than worked around by staying
sequential?

## Background

Phase 2 found vLLM concurrent batching breaks reproducibility: 20/497 events diverged between
`workers=1` and `workers=8` on an otherwise identical config, concentrated in `vote_cast`'s
first-attempt success/failure outcome. Confirmed via a `workers=1`-vs-`workers=1` control (0/497
diffs) that this is concurrency-specific, not inherent vLLM/AWQ non-determinism.

## The candidate fix

vLLM 0.28.0 — the exact version already pinned in `docker-compose.llm.yml` — ships
`VLLM_BATCH_INVARIANT=1`. It enables batch-invariant Triton kernels
(`vllm.model_executor.layers.batch_invariant`) for matmul/bmm/softmax/rms_norm, sets
`num_splits=1` on FlashAttention's decode path (disabling split-KV / flash-decoding, the
documented source of batch-composition-dependent floating-point reduction order), forces a
deterministic cuBLAS workspace config, and disables TF32.

Confirmed genuinely active before testing anything, not assumed from the flag's own name:
`envs.VLLM_BATCH_INVARIANT` reads `True` inside the running container, and the flag is threaded
into attention-backend selection (`flash_attn.py`'s own `self.batch_invariant_enabled` gate), not
just the matmul layer.

## Correctness: fixed, cleanly

Re-ran Phase 2's own `scripts/check_intra_run_concurrency_determinism.py`, unmodified, at the
same scale (1 year / pop 100 / seats 30, `workers=1` vs `workers=8`, `max_batch_replays=0`),
with the flag on:

```
- events.jsonl: workers=1 134724 bytes, workers=8 134724 bytes
- Speedup: 5.84x (16801.2s -> 2876.3s)
**PASS -- byte-identical.**
```

`filecmp.cmp` → `True`. Matches Phase 2's own pre-registered gate exactly. Also confirmed with a
direct raw-request probe (a fixed prompt served alone vs. concurrently alongside 7 different
filler requests, 3 trials each way): identical output both ways.

## Cost: prohibitive for this specific workload

| | Time (4 ticks) | vs. Phase 2's own sequential baseline |
|---|---|---|
| `workers=1`, no batch invariance (Phase 2's own measurement) | 1482.4s | — |
| `workers=1`, **with** batch invariance | 16801.2s | **11.3x slower** |
| `workers=8`, **with** batch invariance | 2876.3s | **1.9x slower** |

The 5.84x concurrency speedup is real. It is not enough to recover an 11.4x collapse in raw
decode throughput.

**Confirmed via two independent measurements, not just the full-arm timing above**:

1. **vLLM's own reported generation throughput** (`docker logs`, `Avg generation throughput`):
   10.8-11.0 tokens/s under batch invariance, steady across several log lines during an isolated
   single-request call.
2. **A direct isolated-call benchmark**, no concurrency, no other load, immediately after
   restarting the container: a single `vote_cast`-shaped call (chunk=1, `think=True`, a 20-dimension
   weighted-distance reasoning prompt) burned its entire 1596-token budget (`finish_reason='length'`)
   in 142.5s — ~11.2 tokens/s. A follow-up call at 4000 tokens exceeded a 300s timeout entirely.

This session's own earlier baseline measurements (Phase 0, no batch invariance) put generation
throughput at 124-127 tokens/s under the same model/hardware. **~11.4x slower**, matching the
full-arm timing ratio (11.3x) closely enough that GPU throttling was ruled out rather than
assumed: `nvidia-smi` during the isolated probe showed 100% utilization, full clock speed (2865
MHz), 62°C — no thermal event.

## Why the cost is this much larger here than typically reported

Published overhead for `VLLM_BATCH_INVARIANT` elsewhere is usually described as modest (roughly
20-60% for conventionally-batched workloads). The gap here is much larger because this project's
own workload sits precisely in the regime `num_splits=1` hurts most: **long-context, small-batch
decoding**. `_VOTE_CAST_MAX_CHUNK_SIZE`/`_CHAMBER_MAX_CHUNK_SIZE` are both pinned to 1 (measured
Ollama batch-size failures, not a free choice — see those constants' own docstrings), and
`think=True` reasoning budgets run 8,000-12,000 tokens
(`_VOTE_THINK_TOKEN_ALLOWANCE`/`_CHAMBER_THINK_TOKEN_ALLOWANCE`). Split-KV / flash-decoding is
specifically the mechanism that parallelizes attention across GPU thread blocks when a single
request must attend over a long, growing KV cache with no other concurrent work to hide the
latency behind — exactly what this workload does on every call, and exactly what `num_splits=1`
removes.

## Net effect on the flagship, and disposition

At the flagship's own scale (~35.6h sequential, non-invariant, Phase 0's own real measurement),
`workers=8` + batch invariance projects to **~69h** — slower than today's shipped sequential
approach, not faster. **Does not ship.** Reverted completely:

- `_check_supported()`'s guard: confirmed still the unconditional refusal from Phase 2 (no
  uncommitted change survived).
- `vllm-polity`: restarted without the flag; confirmed `VLLM_BATCH_INVARIANT` unset in the running
  container, warm-up call successful.
- No code changes from this investigation were committed.

Phase 2's own verdict stands unchanged: the flagship runs sequential.

## What would change this

Either (a) a workload shape with larger effective batches per call — not available today given
the chunk-size floors are load-bearing, measured constraints, not an arbitrary choice, or (b) an
upstream vLLM fix that recovers split-KV parallelism under batch invariance specifically for the
long-context/small-batch case. Neither is in scope here.
