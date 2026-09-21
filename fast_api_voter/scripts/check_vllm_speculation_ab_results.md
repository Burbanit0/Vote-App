# n-gram speculation on real traffic, and the move to vLLM 0.29.0

Measured 2026-09-20 with `scripts/check_vllm_speculation_ab.py` and the bake-off scorecard
(`scripts/bakeoff_report.py`). n-gram speculation was shipped on 2026-09-10 on two synthetic fixtures
(`check_vllm_speculative_decoding_results.md`: about 2.5 times faster on a uniform chamber fixture,
neutral on a varied `vote_cast`). This asks two things: does it earn its place on real traffic, and is
vLLM 0.29.0 an improvement? **Decision (owner, 2026-09-20): pin 0.29.0 and drop `--speculative-config`,
accepting OBS-020.**

## The A/B on a simulation run (12 workers)

The flagship LLM config, population 100, 30 seats, seed 1, 2 years, 12 relaxed workers, one election.
Every arm had an untimed 1-year warm-up first. The server flags are the shipped ones in every arm except
the speculative config and the image.

| run | server | wall | calls | output tokens | output tok/s |
|---|---|---:|---:|---:|---:|
| A1 | 0.28.0 + n-gram (the old pin) | 323 s | 333 | 111,907 | 347 |
| A2 | 0.28.0 + n-gram | 352 s | 334 | 117,046 | 333 |
| B1 | 0.28.0, no speculation ("Using V2 Model Runner") | 332 s | 362 | 114,593 | 345 |
| C1 | 0.29.0, no speculation ("Using V2 Model Runner") | 310 s | 361 | 110,624 | 357 |
| R1 | 0.29.0, no speculation, after three restarts | 299 s | 346 | 108,789 | 364 |

The two speculation runs differ from each other by 9%, as much as any gap between arms: **no wall-clock
difference.** Call counts differ (333 to 362) because relaxed concurrency changes the trajectory.

Per-call decode rate (completion tokens over call latency, tokens per second):

| decision type | A1 | A2 | B1 | C1 |
|---|---:|---:|---:|---:|
| chamber_deliberation (about 80% of output) | 87.5 | 85.7 | 89.0 | 90.6 |
| pressure_action | 54.1 | 54.6 | 74.8 | 75.9 |
| vote_cast | 74.5 | 64.6 | 89.2 | 93.5 |
| representative_response | 122.2 | 122.3 | 111.8 | 112.0 |

With 12 requests in flight the server is batch-bound: speculation is about 28% slower per call on
pressure_action and 24% on vote_cast, 4% on chamber, and 9% faster on representative_response (7
model-seconds in total).

## The same model, one request at a time (the bake-off harness)

The full frozen bank (174 cases, `case_bank.jsonl` sha `709265958412f811`), sent one request at a time,
against the 0.28.0 control session (`qwen3-8b-awq-control`, speculation on):

| decision type | calls | control | 0.29.0 no speculation | control tok/s | new tok/s | new / control |
|---|---:|---:|---:|---:|---:|---:|
| campaign_positioning | 11 | 356 s | 413 s | 144 | 119 | 1.16× |
| vote_cast | 44 | 239 s | 303 s | 164 | 126 | 1.26× |
| chamber_deliberation | 20 | 203 s | 411 s | 178 | 116 | 2.03× |
| candidacy_considered | 21 | 37 s | 93 s | 329 | 131 | 2.50× |
| representative_response | 50 | 30 s | 35 s | 134 | 114 | 1.17× |
| reaction_to_event | 11 | 19 s | 55 s | 376 | 131 | 2.87× |
| coalition_decision | 28 | 16 s | 27 s | 202 | 121 | 1.67× |
| party_nomination_choice | 11 | 8 s | 11 s | 155 | 113 | 1.38× |
| pressure_action | 27 | 9 s | 9 s | 125 | 123 | 1.01× |
| **all** | 225 | **15.9 min** | **22.7 min** | | | **1.43×** |

Without speculation a single stream decodes at a flat 113 to 131 tokens/s whatever the content; with it,
repetitive structured JSON (candidacy, reactions) reaches 300 to 376. So speculation helps sequential
sessions and not concurrent runs: **bake-off-style sessions cost about 43% more GPU time without it**
(about 7 minutes per full bank).

## Answers on the frozen bank

160 of 174 main-pass answers are identical to the control. The 14 that differ:

- 13 because of the server, all in the long-thinking families: `positioning_poles` 9 of 10 differ,
  `chamber_poles` 3 of 10 (two validity flips, both `finish_reason='length'`), one `candidacy_p500` case
  (318 of 500 units right against 314).
- 1 in `response_sweep`, because #545 now accepts a silence citing motif 303, which the control's code
  rejected (validity 42 of 45 against 43).

Every short-answer family is identical: pressure_action (15 of 24 right in both), coalition_decision (one
distinct answer over five levels in both), party nominations, reaction_to_event and vote_cast (36 of 40).
The logprob gate's probabilities differ by at most 0.13. The thinking gate passes in both (341 reasoning
tokens on, 0 off), the logprob gate reads the same 13 of 16 aligned, and the re-run noise floor is the
same (16 of 17). The two families that moved were already fragile: the control's own re-render agreement
is 1 of 6 on positioning and 6 of 10 on chamber.

## Reproducibility (OBS-020)

The same 4-year, 100-citizen, one-worker, strict pair of runs, by server:

| server | pairs | result |
|---|---:|---|
| 0.28.0 + n-gram | 1 | byte-identical |
| 0.29.0 + n-gram | 1 | byte-identical |
| 0.29.0, no speculation | 3 | 2 differ (15 of 312 lines in one), 1 identical |

Suspected cause: Model Runner V2, which only engages when speculation is off. Not settled; see OBS-020.
A run's guarantee is replay from its call log, which passes live.

## Checks run on the new setup

| check | result |
|---|---|
| `check_llm_stack_versions.py` | `docker-compose.llm.yml` and `docker-compose.llm-nvfp4.yml` at v0.29.0, latest stable (pushed 2026-09-09). The finished `docker-compose.llm-4b.yml` bench stays at v0.28.0. |
| `check_thinking_token_budget.py` | honoured: 972 reasoning tokens unbudgeted, 256 and 64 exactly, every answer decodes |
| `check_vllm_batching_determinism.py` | PASS within the run (batch sizes 1, 5, 25, 50; 10 sequential calls) and across a restart |
| three consecutive clean restarts | answering after each |
| `test_polity_vllm_live.py` | 11 passed and the byte-identity test XPASS (see OBS-020); an earlier run failed that test once |
| the 2-year run, repeated | 299 s, no errors |
| frozen bank | 22.7 minutes; answers as above |

## Disposition

Adopted: `vllm/vllm-openai:v0.29.0` with no `--speculative-config`. What is not free about it: sequential
sessions cost about 43% more GPU time, 13 of 174 frozen-bank answers differ from 0.28.0's (long thinking
families), and same-seed live runs are not always byte-identical. The 12-worker simulation runs are equal
or slightly faster. Rollback: revert the change and `docker compose -f docker-compose.llm.yml up -d`; the
0.28.0 image stays local.

## How it was run

Each arm was a server started with the shipped flags (`docker-compose.llm.yml`, or a `docker run` with the
same flags for the arms that are not the compose file), an untimed 1-year run, then
`python scripts/check_vllm_speculation_ab.py <label> 2 <out_dir>`. Arm A is the old compose file, B is
0.28.0 with the speculative config removed, C is 0.29.0 with it removed.
