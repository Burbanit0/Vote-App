# LLM batching determinism — protocol result

Verification protocol for design doc §15bis.5 / DEMARRAGE-polity-v0.md §5.
Run 2026-07-31, before writing `llm_behavior_engine.py` — exactly when the
DEMARRAGE doc says to run it, since it conditions v2's most important test.

**Setup**: Ollama (CPU-only, no GPU on this machine), `OLLAMA_NUM_PARALLEL=8`,
model `qwen2.5:0.5b` (pinned, not `:latest`), `temperature=0`, fixed `seed=42`,
one fixed prompt (a mock citizen-vote-factors prompt), `num_predict=64`.
Script: `fast_api_voter/scripts/check_llm_batching_determinism.py`.

## Result: the B2 concern is real, not hypothetical

| Check | Result |
|---|---|
| batch_size=1, 10 consecutive runs | **identical** (byte for byte) |
| batch_size=1, before vs. after a full container restart | **identical** |
| batch_size=5 (5 concurrent identical requests) | **NOT identical** — outputs diverge from each other and from the batch_size=1 reference |
| batch_size=25, batch_size=50 | same divergence |

`temperature=0` + a pinned model **does** guarantee reproducibility for
sequential, unbatched calls — including across a cold restart of the
inference server. It does **not** survive concurrent batching: five
identical requests fired together produced five different completions, and
none matched the size-1 baseline. Example (batch_size=5, same prompt,
same options, only the batch differs):

```
[0] "...aligns better with their beliefs.\n\n2. **Candidate's Personal
     Background and Experience**: Each candidate has a unique background,
     personal experiences, and qualifications that"
[1] "...aligns better with their personal beliefs and goals.\n\n2.
     **Candidate's Personal Background and Experience**: Each candidate
     has a unique background, experience, and"
[4] "...If the voter has strong beliefs about their own party's policies,
     they might be more inclined to vote for candidate A due to their
     shared principles.\n\n2. **Candidate's Personal Experience and
     Background**: The personal experiences of candidates"
```

Likely cause: floating-point non-associativity in batched matrix
multiplication — concurrent requests change the numerical reduction order
inside the same forward pass, which is a documented property of batched
inference generally, not an Ollama-specific bug.

## Consequence for the design

This directly confirms two decisions already made defensively in
`polity_config.yaml`, now on empirical footing instead of just caution:

- `batch_sharding: static` (§15bis.4a) — **do not** switch to dynamic
  sharding; this result shows *any* concurrent batching, not just dynamic
  reassignment, breaks reproducibility.
- `parallel.intra_run_workers: 1` (§15bis.3) — intra-run parallelism of LLM
  calls is not just "not yet validated," it is now known to break the
  byte-for-byte reproducibility test (Lot 8) the moment the LLM replaces
  `simple_rules.py` in v2, unless calls are serialized per batch.

**Open question for v2, not resolved here**: whether a *fixed-size* static
batch (same citizens, same batch composition, called the same way every
run) is internally deterministic even though *concurrent* calls aren't —
i.e., does batch *composition* need to be reproducible too, or only batch
*size*? This run only tested identical-content concurrent batches; it did
not test whether two runs with the same batch composition (but built from
different-but-parallel work) reproduce each other. That is the actual v2
scenario and should be re-verified against whatever provider/model is
chosen for v2, not assumed from this result.

## Reproducing this check

```bash
docker run -d -p 11434:11434 --name ollama -e OLLAMA_NUM_PARALLEL=8 ollama/ollama
docker exec ollama ollama pull qwen2.5:0.5b
python fast_api_voter/scripts/check_llm_batching_determinism.py --save before.json
docker restart ollama   # wait for it to come back up
python fast_api_voter/scripts/check_llm_batching_determinism.py --compare before.json
```
