# EAGLE-3 speculative decoding on vLLM 0.30.0

Measured 2026-09-25 on the RTX 5070 Ti with `docker-compose.llm-eagle3.yml` against the shipped
`docker-compose.llm.yml` (`vllm/vllm-openai:v0.30.0`, no speculation), same session, one server at a time. The
probe differs from the shipped file by exactly two flags: `--speculative-config` (EAGLE-3, head
`RedHatAI/Qwen3-8B-Thinking-speculator.eagle3` at revision `7073be9cfb31`, draft length 3) and
`--gpu-memory-utilization` 0.88 (was 0.80), which leaves KV room for the 2.15 GiB head.

**Verdict: about a third faster on real runs, with identical answers on the two thinking families production caps
(`campaign_positioning` is uncapped and already fragile; it differs as it does between any two servers). Not yet
adopted; the decision is the owner's.** Why it exists: n-gram speculation was dropped because Model Runner V2 does
not support it (v0.30.0 `config/vllm.py`, `_get_v2_model_runner_unsupported_features`: ngram, ngram_gpu, draft_model,
suffix, medusa, mlp_speculator fall back to V1). EAGLE-type methods are not on that list, and the boot log confirms
"Using V2 Model Runner" with the head loaded.

## Speed

The 2-year, 100-citizen, 12-worker run of `check_vllm_speculation_ab.py` (seed 1, an untimed 1-year warm-up first):

| run | server | wall | calls | output tok/s |
|---|---|---:|---:|---:|
| B1 | shipped, no speculation | 323 s | 360 | 344 |
| B2 | shipped, no speculation | 355 s | 362 | 336 |
| E1 | EAGLE-3 | 229 s | 347 | 489 |
| E2 | EAGLE-3 | 229 s | 347 | 492 |

Wall clock is 32% lower on average and output tokens per second 42 to 46% higher, well past the 15% adoption bar set
beforehand against the roughly 9% run-to-run noise. Mean acceptance length in the server's own metrics was 2.5 to
3.1 tokens per step (maximum 4 at draft length 3).

The real target configuration is one worker, strict, 8 years, 100 citizens, 15 seats (`run_polity_seed_sweep.py`),
same current code, against the same runs on the shipped server:

| seed | server | wall | office occupancy | terms | fallbacks | holders |
|---|---|---:|---:|---:|---:|---|
| 1 | no speculation | 1891 s | 0.970 | 3 | 63 | 82, 99, 82 |
| 1 | EAGLE-3 | 1173 s | 0.970 | 3 | 55 | 82, 82, 35 |
| 2 | no speculation | 1785 s | 0.970 | 3 | 35 | 29, 29, 43 |
| 2 | EAGLE-3 | 1098 s | 0.970 | 3 | 35 | 29, 29, 43 |

38% less wall time on both seeds. Seed 2 elects the same holders as on 0.29.0 and 0.30.0 without speculation; seed 1
diverges at the second term, as it already did between those two servers. Chamber fallbacks are the OBS-021 rate on
every server (11.1% here in seed 1), not something EAGLE-3 adds.

## Checks

| check | result |
|---|---|
| boot | healthy in about 150 s; KV cache 22,896 tokens (1.40 sequences of 16k), against 26,704 (1.63) without it |
| `check_thinking_token_budget.py` | honoured: 972 reasoning tokens unbudgeted, 256 and 64 exactly, every answer decodes |
| `check_vllm_batching_determinism.py` | PASS within the run and across one restart |
| same-seed pairs (`test_polity_vllm_live.py -k same_seed`) | 1 differs, 2 byte-identical, of 3 (OBS-020, see below) |

## The frozen bank (174 cases), one request at a time

Against the no-speculation session of the same day: 160 of 174 main-pass answers identical (158 byte-identical).
Eight of the 14 differences are `positioning_poles` (already the most fragile family). Four cases go from valid to
invalid and one comes back valid:

- Three are **runaway thinking**: about 14,100 reasoning tokens and no answer (`finish_reason='length'`), where the
  plain server finished in 844, 2,277 and 5,017 tokens (one `vote_first_choice` case, two `chamber_poles`). The two
  chamber cases are the same two that failed on 0.29.0, so they sit on a knife edge that any numerics change can tip.
- One is an ordinary model error (`blank=1` with a non-empty ranking), the kind the control also makes once.

That bank arm does not cap thinking. Production caps `vote_cast` and `chamber_deliberation` at 2048
(`llm.thinking_token_budget`); `campaign_positioning` is uncapped there, and it showed no runaway and no validity
loss under EAGLE-3 (10 of 10 valid in both sessions). Repeating the two capped families
at that budget on both servers (`--arm thinking_budget_2048`): all 24 `vote_first_choice` and `chamber_poles` cases are valid
on both and **byte-identical** between them (the six logprob-gate probes: 4 identical, 2 differ), and the sum of call
latency drops from 7.1 to 4.1 minutes (a `vote_first_choice` request from 13.5 s to 7.5 s).

Per-stream speed on the uncapped bank, by decision type (sum of call latency, EAGLE-3 over no speculation):
candidacy_considered 0.46, reaction_to_event 0.46, coalition_decision 0.60, party_nomination_choice 0.64,
representative_response 0.75, campaign_positioning 0.78, pressure_action 0.79, vote_cast 0.95, chamber_deliberation
2.23 (the runaways). The whole bank: 19.5 minutes against 19.3.

## Not settled

- **OBS-020.** Two of three same-seed pairs were byte-identical, against one pair that differed on the shipped
  server; too few to say it is better or worse. Five or more pairs per setup would settle it.
- **Restarts.** One restart was run on this config, not the three the house rule asks for (the earlier 24576
  `--max-model-len` looked fine on its first start and OOM'd on a plain restart), and 0.88 leaves less headroom than
  0.80. Three consecutive clean restarts are owed before adoption.
- **Two seeds** of the simulation run; **12-worker** behaviour was timed but not checked for fallbacks.
- **The head is third-party** (RedHatAI, Apache-2.0, 116 downloads at the time of writing), pinned by revision.
- KV capacity falls by 14%, which matters if the worker count is raised.

## Disposition and rollback

Not adopted. To adopt: move the two flags into `docker-compose.llm.yml` and run the three restarts. Rollback is the
usual `docker compose -f docker-compose.llm.yml up -d`; the probe is a separate compose file and changes nothing until then.

## How it was run

Baseline arm, then EAGLE-3 arm, each with `check_vllm_speculation_ab.py` (warm-up, then two timed runs), the bank
through `run_bakeoff.py` and `bakeoff_report.py --control qwen3-8b-awq-vllm-030`, then the budgeted arm and the
seed 1 and 2 runs of `run_polity_seed_sweep.py --population 100 --years 8 --seats 15 --seeds 1,2`.
