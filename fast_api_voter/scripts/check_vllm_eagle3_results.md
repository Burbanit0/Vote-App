# EAGLE-3 speculative decoding on vLLM 0.30.0

Measured 2026-09-25 on the RTX 5070 Ti with a probe compose file (`docker-compose.llm-eagle3.yml`, removed
when its flags moved into the shipped file, see Disposition) against the shipped
`docker-compose.llm.yml` (`vllm/vllm-openai:v0.30.0`, no speculation), same session, one server at a time. The
probe differed from the shipped file by exactly two flags: `--speculative-config` (EAGLE-3, head
`RedHatAI/Qwen3-8B-Thinking-speculator.eagle3` at revision `7073be9cfb31`, draft length 3) and
`--gpu-memory-utilization` 0.88 (was 0.80), which leaves KV room for the 2.15 GiB head.

**Verdict: about a third faster on real runs, with identical answers on the two thinking families production caps
(`campaign_positioning` is uncapped and already fragile; it differs as it does between any two servers).
Adopted by the owner on 2026-09-26.** Why it exists: n-gram speculation was dropped because Model Runner V2 does
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
| three consecutive plain `compose restart`s | healthy in 48, 48 and 42 s, answering after each, no out-of-memory lines in the log |
| same-seed pairs (`test_polity_vllm_live.py -k same_seed`) | EAGLE-3: 6 of 8 byte-identical (the first 3 pairs, then 5 more). Shipped server, no speculation: 5 of 5 identical in the same session, and 1 differing pair in the earlier live suite (OBS-020, see below) |

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

- **OBS-020.** EAGLE-3 gave 6 identical pairs of 8 and the shipped server 5 of 5 (6 pairs with the earlier live-suite
  pair, 1 differing): no measurable difference at these counts, and neither setup is fully reproducible. One pattern to
  note and not to over-read: **both differing EAGLE-3 pairs were the first pair after a server (re)start**, and every
  later pair was identical. That fits the OBS-020 candidate "run 2 reads a prefix cache that run 1 filled", but the
  shipped server's first pair after its boot was identical too, so it is a lead, not a finding.
- **Restarts** are no longer owed: three consecutive plain restarts were clean (the earlier 24576 `--max-model-len`
  looked fine on its first start and OOM'd on a restart). 0.88 still leaves less headroom than 0.80, so watch it under
  a longer soak than 3 restarts.
- **Two seeds** of the simulation run; **12-worker** behaviour was timed but not checked for fallbacks.
- **The head is third-party** (RedHatAI, Apache-2.0, 116 downloads at the time of writing), pinned by revision.
- KV capacity falls by 14%, which matters if the worker count is raised.

## Disposition and rollback

**Adopted 2026-09-26, by the owner, who does not rely on same-seed byte-identity as long as a run leaves enough logs
to be read closely** (its record is `llm_calls.jsonl`, and a relaxed run replays from it). The two flags moved into
`docker-compose.llm.yml` and the probe compose file was deleted, so there is one set of flags to keep right.

**Verified on the production file itself, 2026-09-26:** the flag set is identical to the probe's (checked by parsing
both), a cold boot is healthy in 186 s (Model Runner V2, `Eagle3LlamaForCausalLM` resolved, KV cache 22,880 tokens, 1.40
sequences of 16k), **three consecutive plain restarts** are healthy in 66, 48 and 42 s and answer each time with no
out-of-memory lines, `check_vllm_batching_determinism.py` passes within the run, and the server's own metrics show a mean
acceptance length of about 3.3 tokens per step. The owed same-seed pairs were run on the probe (6 of 8 identical); they were
not repeated on the production file, since it is the same flags.

**Rollback:** revert this change and `docker compose -f docker-compose.llm.yml up -d`; the 0.30.0 image without speculation
is the same image, and the flags removed are the two named above (`--speculative-config`, and `--gpu-memory-utilization` back to 0.80).

## How it was run

Baseline arm, then EAGLE-3 arm, each with `check_vllm_speculation_ab.py` (warm-up, then two timed runs), the bank
through `run_bakeoff.py` and `bakeoff_report.py --control qwen3-8b-awq-vllm-030`, then the budgeted arm and the
seed 1 and 2 runs of `run_polity_seed_sweep.py --population 100 --years 8 --seats 15 --seeds 1,2`.
