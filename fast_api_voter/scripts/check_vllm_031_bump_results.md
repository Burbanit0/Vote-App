# Moving the pinned vLLM server from 0.30.0 to 0.31.0

Measured 2026-10-05/06 on the RTX 5070 Ti with the shipped flags (`docker-compose.llm.yml`, EAGLE-3
speculation since #656), image `vllm/vllm-openai:v0.31.0` (`sha256:c1c9f6fd5c10`, pushed 2026-10-04, the
latest stable tag per `check_llm_stack_versions.py`). Only the image tag changed, in every vLLM compose
profile. The baseline is **not** `check_vllm_030_bump_results.md`: those numbers predate EAGLE-3, so a
0.30.0 control was re-measured first with today's flags and code (same session, same commit), and its
bank session recorded as `qwen3-8b-awq-vllm-030-eagle3`.

**Verdict: nothing broke, no speed change that can be told from noise, and a larger KV cache.** Every
check that passes on 0.30.0 passes on 0.31.0. The frozen bank moves only in the families that were
already fragile, and the byte-identity test still xfails (OBS-020).

## Checks

| check | result |
|---|---|
| server start, shipped flags | healthy in 148 s cold; "Initializing a V1 LLM engine (v0.31.0)", `speculative_config=SpeculativeConfig(method='eagle3', ..., num_spec_tokens=3)`, "Using V2 Model Runner". `--model` still works and still warns that it will be removed. |
| KV cache | cold start 4.34 GiB, **30,784 tokens, 1.88x** concurrency at 16,384, against 3.25 GiB, 23,024 tokens, 1.41x for 0.30.0 cold with the same flags (+34%). After each warm restart 0.31.0 reports 5.47 GiB, 38,784 tokens, 2.37x; 0.30.0 was not restarted, so that figure has no control. |
| `check_vote_grammar_xgrammar.py` (CPU, in the image) | xgrammar 0.2.7, as on 0.30.0; it takes the vote_cast schema without falling back, and every S1.2 ballot verdict is as required |
| `check_thinking_token_budget.py` | honoured: 972 reasoning tokens unbudgeted, 256 and 64 exactly, every answer decodes -- byte-identical results doc on both servers |
| `check_vllm_batching_determinism.py` | PASS within the run (batch sizes 1, 5, 25, 50; 10 sequential calls) and across a restart |
| three consecutive `compose restart`s | healthy in 32 s each, answering after each |
| `test_polity_vllm_live.py` | 11 passed, 1 xfailed (the byte-identity test, OBS-020) in 13 min 0 s; the replay test passed |
| `check_llm_stack_versions.py` | every vLLM compose profile at v0.31.0, latest stable |

## The 2-year, 100-citizen, 12-worker run

`check_vllm_speculation_ab.py`, seed 1, one election, an untimed 1-year warm-up before each arm:

| run | server | wall | calls | output tokens | output tok/s |
|---|---|---:|---:|---:|---:|
| C1 | 0.30.0 | 314 s | 372 | 127,970 | 407 |
| C2 | 0.30.0 | 259 s | 367 | 111,483 | 431 |
| D1 | 0.31.0 | 282 s | 348 | 124,600 | 442 |
| D2 | 0.31.0 | 280 s | 349 | 121,700 | 434 |

The two 0.30.0 runs differ by 18% between themselves, so a 2% gap between the arms' means (287 s and
281 s) says nothing. Per-call decode rate is the same at 12 workers: chamber_deliberation 125-130 tok/s on
0.30.0 and 128-129 on 0.31.0, pressure_action 66 and 67, campaign_positioning 131 and 131, vote_cast
122-127 and 118.

## The frozen bank (174 cases, `case_bank.jsonl` sha `709265958412f811`)

Sent one request at a time, scored with `bakeoff_report.py --control qwen3-8b-awq-vllm-030-eagle3`.
162 of 174 main-pass answers are identical to 0.30.0's (159 byte-identical). The 12 that differ:

- `positioning_poles`: 8 of 10 differ, all still valid -- the family that moved on every bump so far.
- `chamber_poles`: 3 differ. Two that finished on 0.30.0 ran to `finish_reason='length'` on 0.31.0 and one
  that ran away on 0.30.0 now finishes, so chamber validity goes from 9 of 10 to 8 of 10. That is the
  0.29.0 -> 0.30.0 movement in reverse, in a family whose own re-render agreement is about half.
- `candidacy_p500`: 1 case differs; accuracy 314 of 500 against 318 (McNemar exact, discordant 0 to 4,
  p = 0.125, not significant), the 0.29.0 -> 0.30.0 count (314 to 318) in reverse. Whether they are the
  same four units cannot be checked: the 0.29.0 session is gone.

Every short-answer family is identical (pressure_action 15 of 24 right in both, coalition_decision one
distinct answer over five levels, party nominations, reaction_to_event, representative_response 43 of 45,
vote_cast 36 of 40). The thinking gate passes in both (341 reasoning tokens on, 0 off); the logprob gate
reads the same 13 of 16 aligned (separation +0.942 against +0.933); the re-run noise floor is 16 of 17
against 17 of 17.

Time: 16.9 minutes of call latency against 14.4. The whole difference is chamber_deliberation, 278 s to
409 s, the two runaway generations; every other family decodes at the same per-stream rate (vote_cast 220
against 217 tok/s, candidacy 294 against 293).

## Not settled

- OBS-020: one same-seed pair on 0.31.0 (the live test), and it differs, as on 0.30.0.
- The chamber runaways are one session against one session in a family that flips both ways from bump
  to bump. It is a fact about this bank, not evidence that 0.31.0 runs away more.
- The warm-restart KV figure has no 0.30.0 counterpart.

## Disposition

Pin `vllm/vllm-openai:v0.31.0`. Rollback: revert the change and `docker compose -f docker-compose.llm.yml up -d`;
the 0.30.0 image stays local.

## How it was run

One detached chain (`~/Documents/Dev/polity-runs/vllm031/chain.sh`, log beside it): the 0.30.0 control
on the running server (warm-up, C1, C2, bank session), then `docker compose -f docker-compose.llm.yml up -d`
from this branch and the scripts above in the order of the tables, then the shipped 0.30.0 server
restored. The bank sessions are `python scripts/run_bakeoff.py --label <label> --out <dir>`, both in one
`<dir>`, scored with `bakeoff_report.py <dir> --control qwen3-8b-awq-vllm-030-eagle3`.
