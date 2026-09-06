# vLLM switch — axis (a)/(b) results (plan-vllm-switch-readiness.md §5)

Per that plan's own explicit instruction (§5, §3): the two axes are reported
**separately**, never collapsed into a single "vLLM works"/"vLLM doesn't
work" verdict. Axis (a) is the vLLM backend itself; axis (b) is whether the
AWQ-quantized model reasons comparably to Ollama's un-quantized weights on
already-characterized hard cases. Both were blocked entirely until
2026-09-05, when the platform blocker recorded in this same plan's §0
(`RuntimeError: UVA is not available`, confirmed upstream WSL2/Docker
Desktop bug) cleared on this project's move to native Ubuntu.

## Axis (a) — the vLLM backend itself: PASS

| Check | Result |
|---|---|
| `test_polity_vllm_live.py` (8 tests) | 5/8 pass; 3 fail on the pre-existing, already-documented `blank`/`ranking` cross-field defect (`cache_recycle_chunk_size_tension_findings.md`), not a vLLM/axis-(a) issue — see `scripts/vllm_determinism_results.md` |
| `check_vllm_batching_determinism.py` (§15bis.4c) | PASS — batch sizes 1/5/25/50 concurrent, 10 sequential calls, and a full container restart all byte-identical |
| `check_vllm_prefix_cache_priming.py` (this plan's own named gap — no existing test reproduced the protocol that found Ollama's cross-request prompt-cache bug) | PASS — 6/6 clean (3 shared-prefix + 3 control), after fixing a self-inflicted `max_tokens` sizing bug in the first attempt (see below) |
| Config: `--max-model-len`, `--gpu-memory-utilization` | Resolved live — see `scripts/vllm_determinism_results.md` (8192 too small, 24576 unstable across restarts, settled 16384 + explicit 0.80 utilization, verified over 4 consecutive clean restarts) |

**`check_vllm_prefix_cache_priming.py` detail**: vLLM reports
`enable_prefix_caching=True` by default (confirmed in this container's own
startup log) — architecturally different from Ollama's llama.cpp
`cache_prompt: true` (an exact block-level prefix match vs. a fuzzy
"closest previous prompt" similarity heuristic), so the *same* bug isn't
expected to reproduce by construction. What this script actually tests:
whether *any* vLLM-specific cache-interaction mechanism corrupts a cheap
call immediately after priming with a distinct, long, real `think=True`
prompt. First attempt gave 6/6 false failures — identical across both the
shared-prefix and control arms, all near-instant (~0.5s) — the classic
signature of an under-provisioned `max_tokens`, not a cache bug: the
original Ollama test's flat `max_tokens=50` didn't leave enough headroom
for vLLM's own JSON schema overhead even at a single-citizen batch.
Corrected to `compute_max_tokens(1)` (production's own sizing for that
shape): 6/6 clean on the re-run. As with Ollama's own version of this test,
a clean result here is evidence of absence for the **cheap, think=False**
variant only — it does not exercise think=True/long-reasoning generations,
which this protocol was never designed to test cheaply.

## Axis (b) — does AWQ reason comparably to Ollama's un-quantized weights on the already-known-hard cases: PASS on both

### `campaign_positioning` (`check_vllm_axis_b_campaign_positioning.py`)

Same 6 cids, same `population_size=300`, same seed, same
`think=True`/`compute_max_tokens(1)+8000` protocol as
`validate_campaign_positioning_disambiguation_fix.py`'s live Ollama
validation — only the client changed.

| cid | role | Ollama (pre-fix / post-fix) | vLLM/AWQ |
|---|---|---|---|
| 167, 209, 158 | fix targets | 6/6 pre-fix / ≤1/9 post-fix | **0/9 truncated** |
| 79 | different, unaddressed cause (array-transcription artifact) | 2/2 truncated, not expected to improve | **0/3 truncated** |
| 184, 126 | no-regression check | 0/2 each | **0/6 truncated** |

All 18 calls decoded cleanly with legal motifs (601 sincere / 602-603
strategic shifts) and shift counts that track distance-to-electorate-mean
sensibly (closer nominees stayed sincere, farther ones shifted 1-3
dimensions) — not a degenerate fixed output.

**Notable, not over-claimed**: cid=79's root cause was explicitly
characterized as a *model-internal* artifact (the model silently
truncating its own transcription of a 20-element array to 10 while
reasoning), not a prompt-wording issue the 2026-08-31 fix ever targeted —
and it still reproduces on Ollama post-fix. It did not reproduce at all in
this n=3 sample under vLLM/AWQ. Consistent with (not proof of) the
different-serving-stack/different-quantization change altering that
specific internal failure mode — a 3-trial sample is not enough to call
this resolved, only to note it didn't fire here.

### `chamber_deliberation`, `chamber_position == sincere_position` (`check_vllm_axis_b_chamber_sincere_position.py`)

Production's real single-member-chunk shape
(`_CHAMBER_MAX_CHUNK_SIZE=1`), `think=True`,
`compute_max_tokens(1)+8000`, 10 distinct freshly-sortitioned members (not
a literal replay). This is the exact state the Mode A loop fired on live
(`lot3_chamber_reliability_results.md`: 7/270 sweep, always this state) —
the 2026-08-29 disambiguation fix to `build_chamber_system_prompt` was
validated 0/7 on Ollama.

**Result: 0/10 truncated under vLLM/AWQ.** Every rep returned the correct
motif (701, SINCERE_POSITION) with zero shifts — matching the objectively
correct answer for a member whose chamber position already equals their
sincere position.

## What this does and does not license

**Confirmed**: axis (a) and axis (b) both clear their respective bars.
Every check this plan named as a go/no-go criterion, including the one it
flagged as missing from the existing test suite, now has a result.

**Not covered by this document**: `provider` stays `ollama` in
`polity_config.yaml` — switching the shipped default is a separate,
not-yet-authorized decision, same standing note as every other update to
this investigation. Nor does this document re-verify every reliability
calibration in the codebase (`_VOTE_CAST_MAX_CHUNK_SIZE`,
`recycle_after_n_calls`, etc.) — only the two specific hard cases this
plan named. A production switch would still warrant watching those other
calibrations under real load, not assuming they transfer from this
targeted result.
