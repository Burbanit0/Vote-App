# The precision probe: Qwen3-8B in NVFP4 against the shipped AWQ

Run 2026-09-20 (`docker-compose.llm-nvfp4.yml`, the plan's "precision probe", Track 0a). The question it
was written for: representative_response and coalition_decision collapse on the shipped 8B AWQ, while the
one setup that ever answered representative_response correctly was Qwen3-4B at bf16. Holding size and
weights lineage fixed and changing only the 4-bit format, does the collapse go away?

**Answer: not on the two collapse probes, but the format does move other decisions, some of them
significantly.** Both arms ran on the same stack, vLLM 0.29.0 without speculation (Model Runner V2), so
only the checkpoint differs: `Qwen/Qwen3-8B-AWQ` against `ELVISIO/Qwen3-8B-NVFP4A16` (compressed-tensors,
weight-only; the server log says this card has no native FP4, so vLLM uses the Marlin kernel). The AWQ
arm reproduces the committed 0.28.0 numbers, so the stack change is not what moved anything.

## The two collapse probes

`check_logprob_response_stance_tracking.py` and `check_logprob_coalition_action_tracking.py`, unchanged,
with `POLITY_PROBE_MODEL=qwen3:8b-nvfp4a16` for the NVFP4 arm.

| probe | AWQ | NVFP4 |
|---|---|---|
| representative_response: P(stance=1) across the 9 points | 0.999999 to 1.000000 (spread 0.000001) | 0.999996 to 1.000000 (spread 0.000004) |
| coalition_decision: P(join) at join-obvious / decline-obvious | 0.9994 / 0.9968 | 0.9983 / 0.9841 |
| coalition_decision: pole-to-pole gap (bar: 0.10 or more, in the right direction) | −0.0026 | −0.0142 |
| coalition_decision: spread across the 5 points | 0.035 | 0.105 |

Both stay flat. NVFP4 is less confident in the middle of the coalition axis (P(join) 0.89), but it joins at
every point, including the decline-obvious pole, and the dip is not monotonic in the distance, so it does
not track the axis. That is the base-model pattern again: less confidence is not sensitivity
(`check_base_vs_instruct_results.md`).

## The full frozen bank

The 174-case bank (sha `709265958412f811`; "bank matches: yes") on the NVFP4 model, against the AWQ
session on the same stack and the 0.28.0 control (`bakeoff_report.py`, paired McNemar, Holm-corrected).

| family | control (0.28.0 AWQ) | AWQ, this stack | NVFP4 |
|---|---:|---:|---:|
| candidacy_p500: units right of 500 | 318 (63.6%) | 314 (62.8%) | **351 (70.2%)** |
| pressure_act: citizens right of 24 | 15 | 15 | **22** |
| vote_first_choice: right of 40 | 36 | 36 | 34 |
| coalition: distinct answers over 5 levels | 1 | 1 | 2 |
| reaction_scandal: distinct answers over 2 levels | 1 | 1 | 2 |
| response_sweep: distinct answers over 9 levels | 2 | 2 | 1 |
| nomination: same candidate under permutation | 13 of 23 | 13 of 23 | 8 of 18 |
| chamber_poles: valid of 10 (truncated) | 9 (1) | 8 (2) | 6 (4) |
| vote_cast: valid of 14 | 13 | 13 | 12 |
| representative_response: valid of 45 | 42 | 43 | 45 |

- **Candidacy is the one significant gain.** NVFP4 against the control: 63 units gained, 30 lost, exact
  McNemar p = 0.0008, Holm-corrected 0.028.
- **pressure_act is a large gain that does not survive the correction.** 7 citizens gained, none lost:
  raw p = 0.016, Holm 0.52. The three-model omnibus test (Cochran's Q) is significant, Holm 0.031. On 24
  citizens, treat it as strong and suggestive, not settled.
- **Two contrasts stop being flat.** Coalition and reaction each show 2 distinct answers; the reaction
  controls agree 50 of 50 (the AWQ sessions: 25 of 50). One session per arm, so this is a reading, not a
  test.
- **Everything else is within noise.** On the accuracy tests the AWQ session on the new stack differs from
  the control only by 4 candidacy units (p = 0.125).
- **The re-run noise floor is the same** in all three sessions (16 of 17 outputs, 83 of 86 units).

## What it costs

The same model, one request at a time, on the same stack:

| decision type | AWQ | NVFP4 | tokens per call, AWQ / NVFP4 | time |
|---|---:|---:|---:|---:|
| vote_cast | 303 s | 979 s | 866 / 2,428 | 3.2× |
| chamber_deliberation | 411 s | 646 s | 2,387 / 3,490 | 1.6× |
| campaign_positioning | 413 s | 565 s | 4,470 / 5,733 | 1.4× |
| the six non-thinking types | 230 s | 241 s | about equal | 1.05× |
| **whole bank** | **22.7 min** | **40.7 min** | | **1.8×** |

The NVFP4 model decodes about 5% slower per token (13% on vote_cast) and, on the thinking decisions, reasons much longer
(the thinking gate reads 745 reasoning tokens against 341). It also truncates more: `chamber_poles` 4 of
10 (AWQ 2, control 1) and `vote_cast` 2 of 14 (AWQ 0), on the bank's requests, which send no thinking
budget. Production sends 2,048, which bounds this.

## Reading

- The 4-bit format is not irrelevant. Between two 4-bit weight-only checkpoints of the same model,
  candidacy moves 7 points and pressure_act 7 citizens, and two flat contrasts show a second answer.
  The AWQ checkpoint loses some discrimination that a different format keeps.
- It does not repair the collapse the probe was written for: representative_response stays flat and
  coalition still joins everywhere.
- Both formats are 4-bit. **"4-bit against 16-bit" is still untested**: an 8B at bf16 does not fit this
  card (about 16 GB of weights), and Qwen3-4B at bf16 (8 GB) is the next step of the local plan.
- NVFP4 is not adopted by this result: a 1.8× longer sequential session, longer reasoning and more
  truncation on the two thinking families the simulation depends on most (chamber and vote), and the
  profile added for it is probe-only. Whether the accuracy gain is worth that is the owner's call.

## Reproduce

```bash
cd fast_api_voter
docker compose -f docker-compose.llm.yml stop
docker compose -f docker-compose.llm-nvfp4.yml up -d          # serves qwen3:8b-nvfp4a16
export POLITY_PROBE_MODEL=qwen3:8b-nvfp4a16
python scripts/check_logprob_response_stance_tracking.py
python scripts/check_logprob_coalition_action_tracking.py
unset POLITY_PROBE_MODEL
python scripts/run_bakeoff.py --label qwen3-8b-nvfp4a16 --model qwen3:8b-nvfp4a16   # about 41 minutes
docker compose -f docker-compose.llm-nvfp4.yml down
docker compose -f docker-compose.llm.yml up -d                # restore the pinned server
```

The model needs a profile (S2.3); `QWEN3_8B_NVFP4A16_VLLM` in `model_profiles.py` inherits every value
from the AWQ profile on purpose, so the probe sends the same requests, and none of those values was
measured on this checkpoint.
