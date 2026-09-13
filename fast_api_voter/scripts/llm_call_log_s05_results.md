# S0.5 per-call LLM log: live acceptance run

Step S0.5 of `docs/plan/polity/plan-polity-build-order.md`. One live run against vLLM,
2026-09-13, on branch `feat/polity-llm-call-log` (base `22a12676` plus the uncommitted
S0.5 change, recorded as dirty in the run's own `run_metadata.json`).

```bash
python scripts/run_polity_flagship.py --engine llm --years 2 --population 100 --seats 15 \
  --seed 42 --max-batch-replays 2 --run-id s05-call-log-2y-p100-seed42 --output-dir scripts/flagship_runs
python scripts/attribute_llm_time.py scripts/flagship_runs/s05-call-log-2y-p100-seed42/run/s05-call-log-2y-p100-seed42
```

Server, as recorded by S0.4's probe: vLLM 0.28.0, `vllm/vllm-openai:v0.28.0`, `qwen3:8b` =
`Qwen/Qwen3-8B-AWQ` at `4da05a8e`, relaunched with `--enable-prompt-tokens-details` (added in
this step so `cached_tokens` is reported; it changes the usage block, not generation).

Run: completed, 8 ticks, 560 decisions, 931.7 s, retry_count 20, fallback_count 0.

## Acceptance

| Criterion | Measured | Holds |
|---|---|---|
| Every LLM-derived event's `llm_call_id` resolves to a logged call | 560 / 560 events resolve to a call with the same tick and decision type (also tested on fake-client runs) | yes |
| Golden journal changes only by `llm_call_id` | 578 fake-LLM events identical once the field is removed; 468 gained it; request hashes and the deterministic journal unchanged | yes |
| Writer ≤ 5 ms per call | mean 0.036 ms, max 0.275 ms over 346 calls (`llm_calls_summary.json`) | yes |
| File size recorded | `llm_calls.jsonl` 659,751 bytes for 346 calls (about 1.9 KB per call, reasoning included) | yes |
| Attributed LLM time ≥ 90% of wall-clock | call intervals cover 929.8 s of 930.1 s (100.0%) | yes |

## Where the time went

| category | calls | seconds | share of wall-clock | completion tok | reasoning tok | cached tok |
|---|---:|---:|---:|---:|---:|---:|
| first_attempt | 270 | 625.7 | 67.3% | 103749 | 86766 | 237200 |
| truncation | 2 | 133.2 | 14.3% | 28208 | 28206 | 3952 |
| retry | 6 | 69.0 | 7.4% | 11425 | 10729 | 11616 |
| rejected | 5 | 52.1 | 5.6% | 8438 | 7876 | 9584 |
| warm_up | 2 | 36.9 | 4.0% | 355 | 341 | 9664 |
| budget_probe | 61 | 13.0 | 1.4% | 61 | 0 | 50624 |

By decision type, first attempts: vote_cast 29 calls 315.9 s; chamber_deliberation 26 calls
213.8 s; pressure_action 198 calls 59.6 s; campaign_positioning 1 call 21.4 s;
candidacy_considered 4 calls 6.7 s; representative_response 9 calls 6.3 s;
coalition_decision 2 calls 1.1 s; party_nomination_choice 1 call 0.9 s.

## What this run shows, and what it does not

- The two truncations -- one vote_cast chunk, one chamber chunk, each spending about
  14,000 reasoning tokens before hitting the budget -- cost more time (133 s) than all
  six recovering retries and five rejected answers together (121 s). One run, two
  events: this names where S1.1 and S1.3 (thinking budget) should look, it does not
  size the effect.
- Prefix caching is doing real work: 237,200 of 270,963 first-attempt prompt tokens
  were served from cache.
- The warm-up costs 37 s per run start, fixed; negligible for a multi-day run, 4% of
  this one.
- A 2-year population-100 run is not the p500 shape. Per-call cost and file size here
  do not extrapolate linearly to p500 election ticks (bigger candidate fields, more
  voters per election); S1.1 measures that on the real shape.
- Replay (S0.6) must reproduce this run's `events.jsonl` from this log; that is its
  acceptance test, not this step's -- see below.

## S0.6: this run replayed from its own log

Same flags and run id, written elsewhere, answered by `ReplayClient` with the vLLM
container stopped (`curl localhost:8000/health` unreachable before starting):

```bash
python scripts/run_polity_flagship.py --engine llm --years 2 --population 100 --seats 15 \
  --seed 42 --max-batch-replays 2 --run-id s05-call-log-2y-p100-seed42 \
  --output-dir scripts/flagship_runs/replay \
  --replay-calls-from scripts/flagship_runs/s05-call-log-2y-p100-seed42/run/s05-call-log-2y-p100-seed42
```

| Criterion | Measured | Holds |
|---|---|---|
| Replay reproduces `events.jsonl` byte for byte without the server | `cmp` identical, sha256 `37efa54bd0a78067...` both; `snapshots.jsonl` identical too | yes |
| Every recorded call is used | 344 served, 0 never asked for (the 2 warm-up calls are not replayed: an injected client is never warmed up) | yes |

The replay took 1.5 s against the recorded run's 931.7 s. Its `run_metadata.json` names
`llm_client_injected: ReplayClient` and leaves every server field null, as S0.4 intends
for a run that never talked to a server.
