# Moving the pinned vLLM server from 0.29.0 to 0.30.0

Measured 2026-09-24 on the RTX 5070 Ti with the shipped flags (`docker-compose.llm.yml`, no
`--speculative-config`), image `vllm/vllm-openai:v0.30.0` (`sha256:8a69ffad015f`, pushed 2026-09-22, the
latest stable tag per `check_llm_stack_versions.py`). Only the image tag changed, in
`docker-compose.llm.yml` and the unrun `docker-compose.llm-nvfp4.yml`. `docker-compose.llm-4b.yml`, a
finished bench, stays at v0.28.0 as it did for 0.29.0. Baselines are the 0.29.0 numbers in
`check_vllm_speculation_ab_results.md` and its recorded bank session.

**Verdict: nothing broke, and no speed change that can be told from noise.** Every check that passed on
0.29.0 passes on 0.30.0. The frozen bank moves in the families that were already fragile (two chamber
generations that ran away on 0.29.0 now finish), and the byte-identity test still xfails (OBS-020).

## Checks

| check | result |
|---|---|
| server start, shipped flags | healthy in about 156 s cold; "Initializing a V1 LLM engine (v0.30.0)", `speculative_config=None`, "Using V2 Model Runner", KV cache 3.67 GiB (26,704 tokens, 1.63x concurrency at 16,384). `--model` still works and still warns that it will be removed. |
| `check_vote_grammar_xgrammar.py` (CPU, in the image) | xgrammar 0.2.7 (0.28.0 shipped 0.2.3); it takes the vote_cast schema without falling back, and every S1.2 ballot verdict is as required |
| `check_thinking_token_budget.py` | honoured: 972 reasoning tokens unbudgeted, 256 and 64 exactly, every answer decodes (identical to 0.29.0) |
| `check_vllm_batching_determinism.py` | PASS within the run (batch sizes 1, 5, 25, 50; 10 sequential calls) and across a restart |
| three consecutive `compose restart`s | healthy in about 42 s each, answering after each |
| `test_polity_vllm_live.py` | 11 passed, 1 xfailed (the byte-identity test, OBS-020) in 15 min 41 s; the replay test passed |
| `check_llm_stack_versions.py` | both shipped compose files at v0.30.0, latest stable |

## The 2-year, 100-citizen, 12-worker run

Same protocol as the 0.29.0 A/B (`check_vllm_speculation_ab.py`, seed 1, one election, an untimed 1-year
warm-up first):

| run | server | wall | calls | output tokens | output tok/s |
|---|---|---:|---:|---:|---:|
| C1 | 0.29.0 | 310 s | 361 | 110,624 | 357 |
| R1 | 0.29.0, after three restarts | 299 s | 346 | 108,789 | 364 |
| D1 | 0.30.0 | 325 s | 360 | 114,247 | 352 |
| D2 | 0.30.0 | 349 s | 362 | 119,372 | 342 |

Wall clock is 5 to 17% longer on 0.30.0 and aggregate tokens per second 1 to 6% lower, but two runs per
arm cannot separate that from noise: the two 0.28.0 speculation runs differed by 9% between themselves,
and relaxed concurrency changes the call count from run to run. Per-call decode rate is not lower: at 12
workers chamber_deliberation decodes at 91 tok/s (0.29.0: 91), vote_cast 97 (94), pressure_action 80 (76).
The gap in wall clock is the call mix, not a slower server.

## The frozen bank (174 cases, `case_bank.jsonl` sha `709265958412f811`)

Sent one request at a time, scored against the recorded 0.29.0 session (`qwen3-8b-awq-vllm-029`) with
`bakeoff_report.py --control qwen3-8b-awq-vllm-029`. 161 of 174 main-pass answers are identical to 0.29.0's
(158 byte-identical). The 13 that differ:

- `positioning_poles`: 10 of 10 answers differ, all still valid. (0.29.0 moved 9 of 10 from 0.28.0; the
  control's own re-render agreement on this family is 1 of 6.)
- `chamber_poles`: 2 differ, and both are improvements: on 0.29.0 they died with
  `finish_reason='length'`; on 0.30.0 they finish and validate. Chamber validity goes from 8 of 10 to 10 of 10.
- `candidacy_p500`: 1 case differs; accuracy 318 of 500 against 314 (McNemar exact, discordant 4 to 0,
  p = 0.125, not significant).

Every short-answer family is identical (pressure_action 15 of 24 right in both, coalition_decision one
distinct answer over five levels, party nominations, reaction_to_event, vote_cast 36 of 40). The thinking gate
passes in both (341 reasoning tokens on, 0 off); the logprob gate reads the same 13 of 16 aligned
(separation +0.947 against +0.920); the re-run noise floor is 17 of 17 against 16 of 17.

Reading the scorecard: its four "acceptance" lines compare the *control* session, here 0.29.0, with fixed
0.28.0 expectations, so "candidacy declared 206, expected 202" and "agreeing 314, expected 318" describe
0.29.0. The 0.30.0 session lands on 202 and 318, the 0.28.0 values.

Time: the session took 19.6 minutes against 22.7 for 0.29.0 (sum of call latency 19.3 against 22.5). The
whole difference is chamber_deliberation, 407 s down to 188 s, where the two runaway generations of 0.29.0
are gone. Decode rate per stream is unchanged in every family (113 to 131 tok/s), so this is not a faster
server.

## Not settled

- OBS-020: one same-seed pair on 0.30.0 (the live test), and it differs. One pair says nothing about the
  rate; the five-pair protocol in OBS-020 is still what would settle it. Replay from the call log, which is
  what a run promises, passed.
- The chamber improvement is one session against one session, in a family whose own re-render agreement is
  6 of 10. It is a fact about this bank, not evidence that 0.30.0 fixes runaway chamber generations.
- The 4B bench file is not moved.

## Disposition

Pin `vllm/vllm-openai:v0.30.0`. Rollback: revert the change and `docker compose -f docker-compose.llm.yml up -d`;
the 0.29.0 and 0.28.0 images stay local.

## How it was run

`docker compose -f docker-compose.llm.yml up -d` from the bumped file, then the scripts named above in the
order of the tables. The bank session is `python scripts/run_bakeoff.py --label qwen3-8b-awq-vllm-030 --out <dir>`
with a copy of the 0.29.0 session beside it in `<dir>`.
