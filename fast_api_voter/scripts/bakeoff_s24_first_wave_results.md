# S2.4 first wave: Granite 4.2 8B and Gemma 4 12B through the bake-off bank

Measured 2026-09-25 on the RTX 5070 Ti, `vllm/vllm-openai:v0.30.0`, one server at a time, with
`docker-compose.llm-granite.yml` and `docker-compose.llm-gemma4.yml`. Every session answers the same frozen bank
(`case_bank.jsonl`, sha `709265958412f811`, 174 cases) one request at a time; the control is
Qwen3-8B-AWQ on the shipped server the same day (`qwen3-8b-awq-vllm-030`). Scored with
`bakeoff_report.py --control qwen3-8b-awq-vllm-030`. Both candidate profiles are unmeasured
(`measured=False`): they send Qwen's chunk sizes, budgets and thinking switch. Two of the plan's five candidates
were run; Nemotron-3-Nano-4B, Qwen3-4B and Qwen3.5-4B were not.

**Pre-registered question (plan-polity-build-order.md, S2.4): does `coalition_decision`'s collapse
(|separation| < 0.10) persist on at least two non-Qwen families? Yes: it is flat on both families run, Granite
(separation -0.033) and Gemma (+0.000). Gemma's reading needed the production thinking budget to be readable at
all (below), and the Qwen control's own value is unmeasured.**

| model | `coalition_decision`, 5 levels | probabilities readable? |
|---|---|---|
| Granite 4.2 8B NVFP4 | 1 distinct answer; P by level 1.000, 0.992, 0.881, 0.651, 0.967; separation -0.033, **flat** | yes, in the plain session: logprob gate 16 of 16 aligned |
| Gemma 4 12B QAT | 2 distinct answers; P by level 0.000 at every level; separation +0.000, **flat**; every rendering and relabelling control flat | **only with the budget arm**: gate 16 of 16 aligned (14 correct). In the plain session it fails, 14 of 16 |
| Qwen3-8B-AWQ (control) | 1 distinct answer | no, in either session: gate 13 of 16, so its own collapse is unmeasured here, as on 2026-09-15 |

The representative-response probe agrees: `response_sweep/pressure` is flat on both (Granite 1 distinct answer over 9
levels, separation +0.000; Gemma 2 distinct over 9, -0.000). Gemma's collapse reading comes from a session with
`--arm thinking_budget_2048` on `coalition_diagonal` and `response_sweep`, because a session is only read when its own
logprob gate passes. The coalition cases do not think, so the arm does not change their answers (25 of 25 valid and 2
distinct answers in both sessions); it changes whether the gate lets the probabilities be read. "Persist" is read
against the collapse the plan already records for Qwen. What this suggests, as an inference and not a finding, is that
the collapse comes from what the request asks and not from Qwen.

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

## Validity and accuracy by decision type (plain sessions)

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
| representative_response | 43/45 | 45/45 | 36/45 (37/45 with the arm) |
| vote_cast | 13/14 | 13/14 | 10/14 |

| accuracy | Qwen | Granite | Gemma |
|---|---:|---:|---:|
| candidacy_p500 (units, of 500) | 318 | 394 | 435 |
| pressure_act (of 24) | 15 | 11 | 24 |
| vote_first_choice (of 40) | 36 | 37 | 29 |

## The failures are runaway thinking, and production's cap fixes only some

Every long-thinking failure is **runaway thinking**, not a malformed answer. All ten Granite `campaign_positioning`
cases finish with `finish_reason='length'` at exactly 9,716 tokens, all of it reasoning and no answer; Gemma's five
positioning failures stop at the same 9,716, and its `vote_cast` and chamber failures at 13,250 to 14,426 tokens.
Qwen's median positioning answer is 4,002 tokens. Production caps thinking at 2048 (`llm.thinking_token_budget`) for
`vote_cast` and `chamber_deliberation` **only** (`THINKING_BUDGET_TYPES`; `campaign_positioning` "reasons thousands of
tokens too" and was left uncapped because it was never measured under a budget). The budget arm
(`--arm thinking_budget_2048`, on `vote_first_choice` and `chamber_poles`) therefore tests exactly the two families
production caps:

| | valid, vote / chamber (plain -> budget) | vote_first_choice accuracy | request latency, vote | logprob gate |
|---|---|---:|---:|---|
| Qwen3-8B-AWQ | 14/14, 10/10 (budget only) | 39 of 40 | 13.5 s | no (13 of 16) |
| Granite 4.2 8B | 13 -> 14 of 14, 10 -> 10 of 10 | 39 of 40 | 18.2 s | yes (16 of 16) |
| Gemma 4 12B | 10 -> 14 of 14, 8 -> 10 of 10 | **40 of 40** (was 29) | 25.3 s | yes (16 of 16; was 14) |

Under the cap all of Granite's and Gemma's vote and chamber cases finish with `finish_reason='stop'`, Gemma's vote and chamber calls take about a third of
the time (1,087 s to 354 s and 856 s to 269 s over the family), and Granite's 453 s to 255 s and 471 s to 175 s. What
the cap does **not** touch is campaign_positioning (Granite 0 of 10, Gemma 5 of 10 valid), which production would meet as
it is. Gemma's `representative_response` failures are a different kind: the model finished but broke a domain rule
(silence without motif 303 or 308 seven times, a concession without a shift once or twice).

Speed in the plain sessions follows the same thing: Granite takes 2.3 times as long as Qwen on vote_cast and Gemma 5.0
times (1,546 s against 310 s), because they think far longer, not because they decode slowly.

## Cautions

- One session per model; Granite's re-run agreement on the same requests is 13 of 17 (76.5%), Qwen's 16 of 17, so
  small differences here are inside its noise.
- Gemma runs at `--gpu-memory-utilization` 0.88 and is sized for one request at a time, not the 12 of a simulation run.
- These are bake-off sessions only. Neither profile is measured; do not run a simulation on either.
- Nemotron-3-Nano-4B, Qwen3-4B and Qwen3.5-4B (the rest of the first wave) are unrun.

## Disposition

The pre-registered question is answered: the collapse persists on both non-Qwen families, so it is not something a
switch to Granite or Gemma would remove. Neither model is a drop-in, and nothing about the served model changes.
Granite fails batching determinism and cannot write a positioning. Gemma is the more accurate model on several
families under the production cap (vote 40 of 40, pressure 24 of 24, candidacy 435 of 500) but is slower, tight on
memory, and breaks domain rules on about one response in five. Measuring a thinking budget on `campaign_positioning`
needs a new bank arm (`THINKING_ARM_TYPES` covers only vote and chamber); Granite's `-mxfp4` build (5.47 GiB, named in
its compose file) is the untried route for its determinism.

## How it was run

Per candidate: boot, an answering check, `check_vllm_batching_determinism.py` (with `POLITY_PROBE_MODEL` set to the
served name) saved, a plain `compose restart`, and compared; then `run_bakeoff.py --label <name> --model <name>`.
Then the budget arm (`--arm thinking_budget_2048 --families vote_first_choice chamber_poles`) on both, and Gemma's
collapse families under the arm (`--families coalition_diagonal response_sweep`), scored against the Qwen budget-arm
session.
