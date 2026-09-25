# S2.4 first wave: Granite 4.2 8B and Gemma 4 12B through the bake-off bank

Measured 2026-09-25 on the RTX 5070 Ti, `vllm/vllm-openai:v0.30.0`, one server at a time, with
`docker-compose.llm-granite.yml` and `docker-compose.llm-gemma4.yml`. Every session answers the same frozen bank
(`case_bank.jsonl`, sha `709265958412f811`, 174 cases) one request at a time; the control is
Qwen3-8B-AWQ on the shipped server the same day (`qwen3-8b-awq-vllm-030`). Scored with
`bakeoff_report.py --control qwen3-8b-awq-vllm-030`. Both candidate profiles are unmeasured
(`measured=False`): they send Qwen's chunk sizes, budgets and thinking switch. Two of the plan's five candidates
were run; Nemotron-3-Nano-4B, Qwen3-4B and Qwen3.5-4B were not.

**Pre-registered question (plan-polity-build-order.md, S2.4): does `coalition_decision`'s collapse
(|separation| < 0.10) persist on at least two non-Qwen families? Not settled: one of the two needed families
measures flat, the other cannot be read.**

| model | `coalition_decision` | probabilities readable? |
|---|---|---|
| Granite 4.2 8B NVFP4 | 1 distinct answer over 5 levels; P by level 1.000, 0.992, 0.881, 0.651, 0.967; separation -0.033, **flat** | yes: logprob gate 16 of 16 aligned, separation +0.926 |
| Gemma 4 12B QAT | 2 distinct answers over 5 levels | **no**: logprob gate 14 of 16 aligned, separation +0.076 |
| Qwen3-8B-AWQ (control) | 1 distinct answer over 5 levels | no: gate 13 of 16 aligned, so the control's own collapse is unmeasured, as on 2026-09-15 |

## Gates, determinism and cost

| | thinking gate | batching determinism | bank, sum of call latency |
|---|---|---|---:|
| Qwen3-8B-AWQ | yes (341 reasoning tokens on, 0 off) | PASS, and across a restart | 19.3 min |
| Granite 4.2 8B | yes (871 on, 0 off) | **FAIL**: identical concurrent requests differ at batch sizes 5, 25 and 50; the batch-size-1 output is identical across a restart | 40.2 min |
| Gemma 4 12B | yes (1,499 on, 0 off) | PASS, and across a restart | 65.5 min |

Granite's NVFP4 build is W4A4 and loads on vLLM's FlashInfer-CUTLASS NVFP4 kernel on this card (KV cache 28,208
tokens, 1.72 sequences of 16k). Failing the batching check means a Granite run would not honour the project's
temperature-0 reproducibility rule under concurrency; the check passes for Gemma. The `qwen3` reasoning parser was an
inference for Granite's `<think>` markers; the thinking gate (871 reasoning tokens on, 0 off) confirms it.

## Validity and accuracy by decision type

Valid answers, main pass (candidacy_p500 and pressure_act accuracy are against the bank's own labels):

| decision type | Qwen | Granite | Gemma |
|---|---:|---:|---:|
| campaign_positioning | 10/10 | **0/10** | 5/10 |
| candidacy_considered | 20/20 | 20/20 | 20/20 |
| chamber_deliberation | 10/10 | 10/10 | 8/10 |
| coalition_decision | 25/25 | 25/25 | 25/25 |
| party_nomination_choice | 10/10 | 10/10 | 10/10 |
| pressure_action | 24/24 | 23/24 | 24/24 |
| reaction_to_event | 10/10 | 10/10 | 10/10 |
| representative_response | 43/45 | 45/45 | 36/45 |
| vote_cast | 13/14 | 13/14 | 10/14 |

| accuracy | Qwen | Granite | Gemma |
|---|---:|---:|---:|
| candidacy_p500 (units, of 500) | 318 | 394 | 435 |
| pressure_act (of 24) | 15 | 11 | 24 |
| vote_first_choice (of 40) | 36 | 37 | 29 |

## What went wrong, and it is one thing

Every long-thinking failure is **runaway thinking**, not a malformed answer. All ten Granite `campaign_positioning`
cases finish with `finish_reason='length'` at exactly 9,716 tokens, all of it reasoning and no answer; Gemma's five
positioning failures stop at the same 9,716, and its `vote_cast` and chamber failures at 13,250 to 14,426 tokens.
Qwen's median positioning answer is 4,002 tokens. The bank arm does not cap thinking. Production caps it, at 2048
(`llm.thinking_token_budget`), for `vote_cast` and `chamber_deliberation` **only** (`THINKING_BUDGET_TYPES`;
`campaign_positioning` "reasons thousands of tokens too" and was left uncapped because it was never measured under a
budget). So a budget could rescue Gemma's vote and chamber failures but not the positioning ones (Granite 10 of 10,
Gemma 5 of 10), which production would meet as they are. The thinking-budget arm (`--arm thinking_budget_2048`) had
not been run on these two models when this session was written. Gemma's nine `representative_response`
failures are different: the model finished but broke a domain rule (silence without motif 303 or 308 seven times,
a concession without a shift twice).

Speed follows the same thing: relative to Qwen, Granite takes 2.3 times as long on vote_cast and Gemma 5.0 times
(1,546 s against 310 s), because they think far longer, not because they decode slowly.

## Not settled, and cautions

- The collapse question needs a second readable non-Qwen family. Gemma's gate would have to pass, or another
  candidate would have to; the Nemotron, Qwen3-4B and Qwen3.5-4B candidates are still unrun.
- One session per model; Granite's re-run agreement on the same requests is 13 of 17 (76.5%), Qwen's 16 of 17, so
  small differences here are inside its noise.
- Gemma runs at `--gpu-memory-utilization` 0.88 and is sized for one request at a time, not the 12 of a simulation run.
- These are bake-off sessions only. Neither profile is measured; do not run a simulation on either.

## Disposition

Neither model is a drop-in, and nothing about the served model changes. The next step that would change the picture is the
thinking-budget arm on both (short: the Qwen arm took 7 minutes) to see whether capped thinking makes the long-thinking families valid,
then the determinism question for Granite (its `-mxfp4` build, 5.47 GiB, is the fallback named in its compose file).

## How it was run

Per candidate: boot, an answering check, `check_vllm_batching_determinism.py` (with `POLITY_PROBE_MODEL` set to the
served name) saved, a plain `compose restart`, and compared; then `run_bakeoff.py --label <name> --model <name>`.
