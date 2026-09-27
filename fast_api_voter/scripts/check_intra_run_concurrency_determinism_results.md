# Phase 2 (plan-flagship-30y-run.md): concurrency breaks vLLM reproducibility too

## Result: FAIL. The guard relaxation does not ship.

`_check_supported()`'s blanket refusal of `parallel.intra_run_workers > 1` cited only
`llm_batching_determinism_results.md`, an Ollama-specific finding — the working hypothesis going
into this phase was that vLLM's own documented determinism (`vllm_determinism_results.md`'s
byte-identical sweep at concurrent batch sizes 1/5/25/50) meant the guard could be relaxed for
`provider == "vllm"` specifically. That hypothesis is wrong. Measured directly, at the full
`run_simulation` level (not isolated synthetic calls): concurrency degrades vLLM's reproducibility
too, just less severely and through a different, more specific mechanism than Ollama's.

## Methodology bug found and fixed first (not the finding — the finding is below)

The first run of `check_intra_run_concurrency_determinism.py` (1 year / pop 100 / seats 30 /
workers 1 vs 8 / `max_batch_replays=0`) reported `filecmp.cmp` as `False` on every single line.
Inspection showed the ONLY difference was the `run_id` field itself
(`determinism-1y-p100-w1` vs `determinism-1y-p100-w8`) — the script gave each arm a different
`run_id`, which `journal.py` writes into every event, so a byte-diff was guaranteed to fail
regardless of whether anything about the actual decisions differed. Fixed: both arms now share
one `run_id`, kept apart by `output_dir` instead (`run_arm`'s own updated docstring explains the
fix). This is a bug in the check, not a finding, and is disclosed here rather than silently
corrected, per this project's own standing convention of reporting self-inflicted measurement
errors alongside the results they could have distorted.

## The real finding, after the fix

With `run_id` no longer confounding the comparison: **20 of 497 events (~4%) diverge** between
`workers=1` and `workers=8`, same seed, same config, `max_batch_replays=0`. Every single diff is
the same shape:

```
A (workers=1): {"citizen_id": 12, ..., "event_type": "vote_cast", ...,
                "payload": {"blank": 0, "llm_fallback": 1, "ranking": [42, 48, 2, 29, 21], ...}}
B (workers=8): {"citizen_id": 12, ..., "event_type": "vote_cast", ...,
                "payload": {"blank": 0, "llm_fallback": 0, "ranking": [42, 48, 2, 29, 21], ...}}
```

**`llm_fallback` flips 0↔1 between arms — but `ranking`/`blank`/`motif` are byte-identical in
every one of the 20 cases.** This is not a different vote; it is a different MECHANISM producing
the identical vote. The voter's first LLM attempt succeeded in one arm and failed (triggering
`cast_votes`'s own deterministic fallback, `check_vllm_vote_cast_retry_is_inert_results.md`) in
the other, for the exact same prompt, seed, and temperature=0.

**Not just a reshuffling — a real increase in the underlying failure rate**: `vote_cast`'s
first-attempt failure rate was 30/100 (30.0%) in BOTH sequential runs (see control below), and
39/100 (39.0%) under `workers=8` concurrency. Concurrent load doesn't just change *which* citizen
happens to fail; it makes failure measurably more likely.

## Control run: is this concurrency-specific, or is vLLM just non-deterministic under real load?

Before attributing the divergence to concurrency, the alternative had to be ruled out: maybe
vLLM/AWQ simply isn't perfectly reproducible run-to-run under this project's own complex,
`think=True` production prompts, independent of whether anything else is concurrently in flight —
which would be a much larger finding, calling into question `vllm_determinism_results.md`'s own
verdict (measured on isolated synthetic calls, never through the full production pipeline).

Ran `workers=1` a second time, identical seed/config, and diffed it against the first `workers=1`
run (`run_id` normalized the same way): **0 of 497 events differ.** Two independent sequential
runs are byte-identical. This rules out inherent, load-independent non-determinism and confirms
the divergence is attributable to concurrency specifically — consistent with, though not
independently re-derived from, this project's own pre-existing mechanism
(`llm_client.py`'s `VllmJsonClient` class docstring): greedy decoding (temperature=0) is normally
robust to per-call floating-point noise, except at a genuine near-tie branch point, where kernel-
level floating-point reduction order — a function of GPU batch composition, which concurrent load
changes by construction — can flip the result. 20/497 near-tie flips, and a measurable failure-rate
increase under load, is consistent with exactly that mechanism, not proof of it in isolation (the
underlying vLLM/CUDA kernel behavior was not independently instrumented here).

## Disposition

Per the plan's own pre-registered gate ("Any diff => the unlock does not ship, and the plan falls
back to sequential + checkpointing"): `_check_supported()`'s refusal is **unconditional again**,
citing both the original Ollama finding and this one. `run_chunks()` (the shared execution
strategy this phase built) stays in the codebase, correct and unit-tested in isolation
(`test_run_chunks_*`, `test_polity_llm_behavior_engine.py`) — every caller today only ever reaches
its `workers == 1` branch, proven byte-for-byte identical to the pre-Phase-2 sequential code. It
is deliberately left in place as ready-to-enable groundwork, not reverted: nothing about today's
finding says the mechanism is wrong, only that the current `_check_supported` gate must not open
it yet. Re-enabling it would need either a fix to the underlying batch-composition sensitivity
(out of scope here — would need vLLM/CUDA-level instrumentation this project doesn't have) or a
deliberate, separately-authorized policy decision to accept a ~4% divergence rate on
non-byte-reproducible runs (`max_batch_replays > 0` already accepts something in this family, but
that is a documented, bounded exception at one call site, not a blanket policy).

## What this means for the flagship run

The flagship stays **sequential**. Phase 0's own real measurement (`baseline-2y-p100-vllm-v3`,
2266.8s for 2 years / pop 100) is the throughput this plan now has to work with, not the ~3.5x
speedup this smoke proof's own timing showed (1482.4s -> 423.6s) before being disqualified on
correctness grounds. Phase 3 (checkpoint/resume) moves from "nice to have alongside concurrency"
to "the only mitigation for a multi-day sequential run" — exactly the plan's own pre-registered
risk-section fallback, now the live path rather than a contingency.
