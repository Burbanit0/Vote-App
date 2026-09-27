# Plan — the full run: 30 simulated years at population 500

> **Living document, English, like `plan-flagship-30y-run.md`, which it picks up.** That plan built
> the runner, checkpointing and observability (Phases 0-6) and left Phase 7, "the run", as `TODO`
> since 2026-09-11. Since then the serving stack, the defaults and the known defects all moved.
> This is the run's own tracker: what is decided, what is not, what to expect, how to start it,
> what to read afterwards. Written 2026-09-26, **the run was made the same day: see "What the run showed".**

**Status: the run is DONE (2026-09-26, 2 h 08 min, no resume, no error); reading it and the improvements are next.**
The owner's stated plan: run it as it stands, see what can be improved, then work on it to make it as clean as possible.
**Decided 2026-09-26: EAGLE-3 is adopted (PR #656), and the run is relaxed with 12 workers: the owner does not
need byte-identity as long as the run leaves enough logs to be read closely** (PR #655 adds the prompts).

## What this run is for

The flagship arm: 30 simulated years (120 ticks), population 500, 75 sortition seats, LLM engine on
vLLM / Qwen3-8B-AWQ with EAGLE-3, 12 workers, checkpointing on. It answers the production question the earlier plan
asked: can the simulator run at the scale it was designed for, long enough to produce something the
explorer can be pointed at.

Its first job is **diagnostic**. So the known defects are *not* fixed first: the run is the baseline they
are measured against, and their expected size is written down below (before the run, so none of it is a
surprise and none of it can be read as a discovery).

## The configuration

Built by `run_polity_flagship._flagship_config` and validated by `validate_config` on 2026-09-26
(`scripts/prepare_full_run.py` re-checks it on the day):

| setting | value |
|---|---|
| length, population, chamber | 30 years x 4 ticks = 120 ticks, 500 citizens, 75 seats (15%) |
| seed | 42 |
| engine and server | `llm`, `qwen3:8b` on vLLM with EAGLE-3 (Model Runner V2), temperature 0, `llm.reproducibility: relaxed`, 12 workers |
| retries | `max_batch_replays` 2 |
| thinking | `thinking_token_budget` 2048 on `vote_cast` and `chamber_deliberation` only (`campaign_positioning` is uncapped) |
| votes | `vote.mode: utility`, `turnout_cost` 0.04, `audit_fraction` 0.1, `vote_cast_grammar_invariants` on |
| institutions | `president_term_limit` 2, a recalled president barred from the snap election, `ambition_threshold` 0.3 |
| mechanisms on | legitimacy, mandate, petition, street pressure, social graph, exogenous events, awakening |
| mechanisms off | emotions, legislation, dynamics (experimental, off by design) |

## Decisions for the owner

Defaults are what the launcher does if nothing is changed. Each has a recommendation.

| # | Decision | Default | Recommendation |
|---|---|---|---|
| D1 | Serving: the shipped server (no speculation) or EAGLE-3 | **EAGLE-3, decided** | Adopted 2026-09-26 by the owner: PR #656 moves the two flags into `docker-compose.llm.yml` (verified there: three clean restarts, determinism, acceptance length about 3.3). 8-year runs are about 38% shorter (`check_vllm_eagle3_results.md`). |
| D2 | Reproducibility: `strict`, 1 worker, or `relaxed`, 12 workers | **relaxed, 12 workers, decided** | The owner does not need a run to be reproducible from its seed as long as it leaves enough logs to read it closely. Relaxed lets 12 workers run in parallel (a 3.5x speed-up on a 1-year, 100-citizen run in `concurrency_sweep_kv_auto_results.md`, never measured at p500) and reproduces from its call log (`--replay-calls-from`) instead. What "enough logs" means is in "What the run leaves behind" below. |
| D3 | Fix OBS-021 (chamber fallbacks) first, or run as it stands | as it stands | As it stands: the run is the baseline the fix is measured against. Choose otherwise only if 460 to 1,100 chamber fallbacks would make the run unreadable to you. |
| D4 | Seed | 42 | 42, for comparability with the p500 batch. |
| D5 | Apply the Stage 4 result (`awakening_anxiety` 0.25) or keep emotions off | off | Off: it is a mechanism change, and the run's first job is to be a baseline. |
| D6 | Timing probe first | yes | Yes (below): two simulated years at population 500, with the run's own settings (12 workers, EAGLE-3), turn the cost estimate into a measurement, for about one hour of GPU time. It is also the first measurement of whether 12 workers help at p500 and whether the smaller KV pool (22.9k tokens) queues requests. |

## Cost

**Measured, on the current code and server, one worker, strict (2026-09-25):** an 8-year, 100-citizen run takes
1,891 s, 1,785 s and 2,277 s (32 ticks), which is 62 s per tick; on EAGLE-3, 1,173 s and 1,098 s, which is 35 s per tick.
**Last uninterrupted p500 measurement:** 7.29 h for 8 years (`sweep-8y-p500-seed2`, 13.7 min per tick), on the
earlier setup (vLLM 0.28.0 with n-gram speculation, `vote.mode: llm`, no thinking budget), before the changes that
halved the p100 times.

**Estimates, inferences.** If a p500 tick costs five times a p100 tick, one worker takes about **10 h on the plain server
and about 6 h on EAGLE-3**. The run's own settings add 12 workers: a 2-year, 100-citizen, 12-worker EAGLE-3 run took 229 s (29 s
per tick, against 35 s per tick for the 8-year one-worker run, which is not the same shape), so the run should take about
**2 to 5 h**, and 6 h would mean the workers gained nothing at this scale. Election ticks are 8 to 10 times an ordinary tick
(the last tick of `sweep-8y-p500-seed2`, an election, took 61 minutes), so expect long silences. Projecting the old p500
measurement instead gives about 27 h, the upper bound if every estimate is wrong. **The probe replaces the guess.**

**Disk:** the p500 outputs of an 8-year run are 2.5 to 4.5 MB of events, 2.6 MB of census and 0.9 MB of checkpoint; 30 years is
well under 1 GB. The risk is not this run's own files but everything else on the disk (OBS-016), which is why the launcher watches it.

## Day-of sequence

Nothing here needs to be done until the owner decides to start. `PY` is the Python with the backend dependencies
(`~/Documents/Dev/Vote-App-polity/fast_api_voter/.venv/bin/python`).

1. **Merge this branch**, then work from a clean checkout of `polity`, so the run records a pushed commit:
   `git worktree add ../Vote-App-run origin/polity` (detached), and `cd ../Vote-App-run/fast_api_voter`.
2. **Start the server** (`docker compose -f docker-compose.llm.yml up -d`, from a checkout that has PR #656, so that the file carries the EAGLE-3 flags) and wait until it is healthy
   (about 3 minutes cold). The pre-flight warns if the server is not running with EAGLE-3.
3. **Dry run:** `PY=$PY scripts/launch_full_run.sh`. It runs `scripts/prepare_full_run.py` and prints what `--go` would do; it starts nothing.
   Fix every `FAIL`. Two `WARN`s are expected and harmless when launched this way: the launcher detaches the run, so the
   editor-process-tree warning is about the shell you are typing in, not the run. `Linger=no` matters: it means logging out of
   the desktop session would stop the run. `loginctl enable-linger $USER` fixes it, and it is a system change, so it is not done for you.
4. **Timing probe (recommended):** `YEARS=2 PY=$PY scripts/launch_full_run.sh --go`. It uses the same path with two years (8 ticks) and its own
   run id. Read the per-tick time from `progress.json` and multiply by 120, election ticks aside. D1 and D2 are decided, so the probe does not choose between
   them: it says whether 12 workers help at p500 (against about 29 s per tick at p100) and whether the 22.9k-token KV pool queues requests
   (`Waiting` and `preempted` in the server log). If 12 workers do not help, `WORKERS=1 REPRO=strict` is the fallback, and it is the owner's call.
5. **The run:** `PY=$PY scripts/launch_full_run.sh --go`. It starts the run as a `systemd-run --user` unit, off this terminal and off any editor
   (OBS-014), under an inhibitor that blocks sleep, idle and shutdown, with a watchdog that stops the run cleanly if free disk falls below 8 GiB,
   and three helpers bound to it that capture the server log, a GPU sample every minute, and a `docker inspect` of the server.
6. **Watch it** (the launcher prints these):
   - status `systemctl --user status polity-<run-id>`, log `tail -f <out>/<run-id>.log`.
   - one line: `jq -r '"tick \(.tick)/\(.total_ticks) (year \(.simulated_year)), last tick \(.last_tick_duration_seconds/60|floor) min, eta \(.eta_seconds/3600*10|floor/10) h, fallbacks \(.fallback_count), retries \(.retry_count)"' <run-dir>/progress.json`
   - fallback rate by type: `jq -r '. as $p | .decisions_by_type | to_entries[] | select(.value>0) | [.key, .value, ($p.fallback_by_type[.key] // 0)] | @tsv' <run-dir>/progress.json | awk -F'\t' '{printf "%-26s %6d %4d %6.1f%%\n", $1, $2, $3, 100*$3/$2}' | sort -k4 -rn`
   - the server side: `tail -f <out>/<run-id>.vllm.log` (acceptance length, KV cache usage, running and waiting requests), and the last GPU sample:
     `tail -1 <out>/<run-id>.telemetry.jsonl` (`gpu` is utilisation %, memory MiB, temperature C, power W, SM clock MHz).
   - alive or stuck: `$PY scripts/check_run_liveness.py <run-dir>`. **Never kill a run for silence alone**: on 2026-09-11 a healthy run was killed after
     an hour of legitimate silence and about 2 h of GPU work was lost (the script's own docstring).
   - the explorer, live: `~/Documents/Dev/polity-runs/polity-ui.sh start`, then http://localhost:3000/polity, root `full`. The run is listed as soon as it
     has written its journal, config and census, and is re-read as its files change.
7. **Stop and resume:** `systemctl --user stop polity-<run-id>` sends SIGTERM, the runner writes its digest, and `launch_full_run.sh --go --resume` continues
   from the last per-tick checkpoint. (Phase 3 showed a resumed run byte-identical to an uninterrupted one for a strict run; a relaxed run is not
   byte-reproducible from its seed anyway, so nothing of that kind is claimed here, and `run_metadata.json` counts the `resumes`.) After a `kill -9` or a power cut
   there is no digest, and the same `--resume` works from the checkpoint. If a resume complains about an empty `digest.json`, move it aside (OBS-016).
   Each launch takes its own `docker inspect` of the server, so a server change between a stop and a resume is on record.

## What to watch, and when to stop

**Proposed stop conditions, pre-registered, for the owner to confirm.** Everything else is the run doing its job:

1. A decision type whose fallback rate exceeds **50% over any four completed ticks**. Precedents: `vote_cast` at 494 of 500 at tick 16 of the pre-fix scale probe,
   which decided both presidential elections in substance by the deterministic baseline while the journal recorded an LLM run, and `party_nomination_choice` at 66.7%
   in the post-fix probe (OBS-006).
2. The server unhealthy or restarted mid-tick: pause, restart it, resume.
3. Ticks slower than **three times the median of the last eight ordinary ticks, three in a row, and the liveness check says suspect**.
4. Free disk below 8 GiB: stops by itself.
5. `office_occupancy` **below 0.5 after year 8** (the ten 8-year p100 seeds sit between 0.82 and 0.97).

## Expected before it starts

Written down now, so the run can be read against them:

- **Chamber fallbacks of about 5 to 12% of chamber units (OBS-021), an inference from scaling.** About 9,300 chamber decisions (the p100 run's 495, times 5 for the seats, times
  3.75 for the years) gives 460 to 1,100 fallback units, and the digest's 10% alert on `chamber_deliberation` may fire. The last clean p500 run had 0.2%; the difference is the
  configuration that changed since (2048 thinking budget, vote grammar invariants, turnout cost, term limit). The cause is a validation rule (five shifts against a cap of three), not the model or the server.
- **`representative_response` and `coalition_decision` stay in the digest's `unverified_decision_types`**, so `mandate_deviation`, `cohabitation_rate` and `coalition_lifespans` are labels, not results.
  S2.4 (PR #648, `bakeoff_s24_first_wave_results.md`, not yet merged when this was written) found the collapse persists on Granite and Gemma, so a different model does not fix it.
- **About 40% of citizens declare candidacy at every election (OBS-011)**, which 30 years amplifies.
- **Positioning thinking is uncapped in production.** Watch `finish_reason='length'` on `campaign_positioning`; two other models ran it to 9,716 tokens without an answer, Qwen's median is 4,002.
- **The run will not reproduce from its seed, by choice.** Relaxed with 12 workers, on a server whose same-seed pairs are not always byte-identical (OBS-020).
  The guarantee is replay from the call log, which needs the same flags (see "After the run").
- **EAGLE-3 and runaway thinking.** On the uncapped bank, EAGLE-3 turned three cases into runaways (about 14,100 reasoning tokens, no answer), all in `vote_first_choice` and
  `chamber_poles`, which production caps at 2048; with the cap, all 24 cases were valid and byte-identical to the plain server. `campaign_positioning` is the family that is
  uncapped in production, and it showed no runaway and no validity loss on 10 of 10 cases. A 30-year run is the first time this is tested at volume.
- **A smaller KV pool under 12 workers.** 22.9k tokens on EAGLE-3 (26.7k without). Preemption would show in the server log before it shows in the tick times.

## What the run leaves behind

The owner's condition for dropping same-seed reproducibility is "enough logs to look at it deeply". These are those logs, all written by the launcher's units and the
runner, none of it needing a flag beyond what `launch_full_run.sh` already sets. `<out>` is `~/Documents/Dev/polity-runs/full`, `<run-dir>` is `<out>/<run-id>/run/<run-id>`.

| File | What it answers | Size (from the 8-year p500 run, scaled to 30 years) |
|---|---|---|
| `<run-dir>/events.jsonl`, `snapshots.jsonl`, `events.duckdb`, `viz_export.json` | what happened, and the explorer's data | 4.5 MB + 2.6 MB in 8 years, so about 20 to 30 MB |
| `<run-dir>/checkpoint.json` | where a resume restarts | about 1 MB |
| `<run-dir>/llm_calls.jsonl` | the model's answer, its reasoning, tokens, `finish_reason` and latency for every call; the replay input | 17 MB for 6,711 calls, so about 65 MB |
| `<run-dir>/llm_prompts.jsonl` | what the model was asked: system prompt, user prompt and schema per `call_id` (PR #655, switched on by the launcher) | not measured; at most about 140 MB (mean prompt 1,335 tokens, before the de-duplication of repeated text) |
| `<run-dir>/llm_calls_summary.json`, `digest.json`, `digest.jsonl`, `progress.json` | totals, the fallback rates and alerts, live progress | small |
| `<run-dir>/run_metadata.json` | provenance: `git_sha`, `git_dirty` and its paths, `config_hash`, `vllm_image` and `vllm_version`, the served model repo and revision, GPU driver and CUDA, `resumes` | small |
| `<out>/<run-id>.log` | the runner's own output | small |
| `<out>/<run-id>.vllm.log` | the server's log during the run: acceptance length, KV cache usage, running, waiting and preempted requests | grows with the run, tens of MB |
| `<out>/<run-id>.telemetry.jsonl` | a GPU sample and the run's `progress.json` every minute | about 80 KB per hour (`progress.json` is about 1 KB) |
| `<out>/<run-id>.server.<time>.json` | `docker inspect` of the server at each launch: the image, and the full command line, which is where EAGLE-3 is recorded | small |

The one thing `run_metadata.json` does not record is the server's command line, hence the `docker inspect` file. The whole set is well under 1 GB.

## What the run showed

Run `full-30y-p500-seed42-20260926`, 15:45 to 17:54 local on 2026-09-26, from a clean checkout of `polity` at `e362f4d3`
(`run_metadata.json`: `git_dirty` false, vLLM 0.30.0). Files in `~/Documents/Dev/polity-runs/full/` (root `full` in the explorer).
`digest.json`: `outcome` completed, `error` none, `resumed_attempt` false. No stop condition fired.

| Written before the run | Measured |
|---|---|
| 2 to 5 h; 6 h would mean the workers gained nothing | **7,705 s (2 h 08 min)**: 120 ticks, 32,677 decisions, 281 replays. Median tick 47.5 s. No 2-year probe was run: the first 8 ticks served as one (tick 2 took 57 s). |
| Election ticks 8 to 10 times an ordinary tick, so long silences | The slowest ticks took 343 to 349 s (7 times the median, among the 98 the minute telemetry sampled) and are the three elections where positioning ran away (OBS-022). The longest tick was under 6 minutes; the hour-long election tick of the old p500 measurement did not recur. |
| The smaller KV pool may queue requests under 12 workers | **It did, briefly.** Over 764 server samples (every 10 s), requests waited in 37 (4.8%, at most 8 waiting) and KV use reached 95% or more in 3; there were no preemptions and no errors in the server log. Mean acceptance length 2.66 (the earlier short probe measured about 3.3). |
| Chamber fallbacks of 5 to 12% of units (OBS-021), the 10% alert may fire | **7.05%** (640 of 9,075 units); the alert did not fire. The cause is shown: the shift-count rule, and one bad answer costs its whole batch of five (OBS-021, updated). |
| `representative_response` and `coalition_decision` stay unverified | They do: `unverified_decision_types` lists both. Fallbacks: 4.1% and 0%. |
| About 40% declare candidacy at every election (OBS-011) | 202 to 206 of 500 at each of the 11 elections, 2,234 of 5,500 (40.6%). |
| Positioning is uncapped: watch `finish_reason='length'` | **3 of 11 first attempts** ran to the 9,836-token limit with no answer; the retry answered each time (0 fallbacks of 55). It is the prompt, not chance (OBS-022). |
| The thinking budget binds on 41 to 45% of chamber calls and 25% of vote calls | Chamber **41%**, as written. `vote_cast` **86%** (192 of 223), which was not expected (OBS-023). |
| The guarantee is replay from the call log | **Shown.** `--replay-calls-from` on CPU with the same flags served 20,297 recorded calls, asked for none that was missing, and reproduced `events.jsonl` and `snapshots.jsonl` byte for byte (86 s). |
| Stop conditions (a type over 50% fallbacks over four ticks, occupancy under 0.5, ...) | None. The highest cumulative rate in a type with 30 or more decisions was `representative_response` at 12.9% (4 of 31, tick 30), and `chamber_deliberation` at 8.9% at tick 2; `office_occupancy` is 0.967. |

**What happened in the society.** 11 presidential terms and 8 different presidents (citizens 463, 177, 3, 459, 132, 298,
471, 315). Seven terms ended by election, three by the legitimacy floor (ticks 27, 41 and 90) and one was running at the
end. The term limit of 2 held: 463, 3 and 132 each served twice. `office_occupancy` 0.967, against 0.82 to 0.97 for the ten
8-year p100 seeds. 8 coalitions formed and 139 candidacies were declared over the 11 elections.

**The record.** Everything the owner asked for is there: `llm_calls.jsonl` (24 MB, 20,299 lines: 18,283 decision calls, 2,014 budget probes, 2 warm-ups),
`llm_prompts.jsonl` (12 MB), the server log (22,092 lines), the minute telemetry and the server's `docker inspect`. The
prompts sidecar was first used at this scale here and worked. Not yet read closely: the chamber answers behind the
fallbacks beyond the shift count, the `representative_response` fallbacks (5), and the citizen biographies in the explorer.

## The three seeds

Seeds 1 and 2 were run the same night, one after the other (`~/Documents/Dev/polity-runs/chain-seeds.sh 1 2`), from the same
code and config as seed 42 (only docs changed between the commits) on the same server. All three completed. Numbers from
each run's digest, call log and events; the entries they feed are OBS-021 to OBS-025.

| | seed 42 | seed 1 | seed 2 |
|---|---:|---:|---:|
| wall clock | 2 h 08 (7,705 s) | 1 h 59 (7,162 s) | 2 h 05 (7,498 s) |
| median tick / slowest tick | 47.5 s / 349 s | 49.6 s / 184 s | 52.1 s / 177 s |
| decisions | 32,677 | 33,888 | 40,459 |
| fallbacks (share of decisions) | 648 (1.98%) | 562 (1.66%) | 710 (1.75%) |
| `chamber_deliberation` fallback | 7.05% | 5.79% | 7.11% |
| `vote_cast` fallback | 0.51% (1 batch) | 2.69% (4 batches) | 2.14% (4 batches) |
| `representative_response` fallback | 4.13% | 0% | 2.48% |
| `reaction_to_event` fallback | 0% | 0.83% (1 batch of 25) | 1.67% (2 batches of 25) |
| positioning first attempts at the limit | 3 of 11 | 0 of 9 | 0 of 12 |
| `vote_cast` / chamber budget reached | 86% / 41% | 84% / 44% | 72% / 40% |
| candidacies declared per election (of 500) | 202 to 206 | 170 | 185 to 186 |
| presidential terms / presidents | 11 / 8 | 9 / 8 | 12 / 9 |
| terms ended by the legitimacy floor | 3 | 1 | 4 |
| `office_occupancy` | 0.967 | 0.983 | 0.959 |

**Structural (all three seeds).**
- The chamber loses 5.8 to 7.1% of its units to validation, every failed call loses all five of its units, and the rules
  explain 361 of 362 failed calls (OBS-021). Fallbacks stay at 1.7 to 2.0% of all decisions and no digest alert fired.
- The `vote_cast` thinking budget binds on 72 to 86% of calls and the chamber's on 40 to 44% (OBS-023).
- Candidacy is the same number at every election of a run, and its level depends on the seed (OBS-011).
- A run costs 2 h (1 h 59 to 2 h 08), a spread of under 8% across seeds. No preemption and no server error in any of them.
- `representative_response` and `coalition_decision` stay unverified.

**Seed-specific.** The positioning runaway (OBS-022) is seed 42's party set, and it produced its three slowest ticks.
`reaction_to_event` fell back only in seeds 1 and 2 (OBS-025). The number of terms (9 to 12), removals by the legitimacy floor (1 to 4)
and presidents (8 or 9) vary with the seed: the society is not a fixed trajectory.

**New.** A `vote_cast` batch of three sometimes answers for one voter, identically over three attempts, with the budget
exhausted each time (OBS-024, 9 batches over the three runs). `reaction_to_event` fails whole batches of 25 on the same kind of
bound overshoot as the chamber (OBS-025).

**One design defect, three decision types.** In each of the chamber (5 units), `reaction_to_event` (25) and `vote_cast` (3)
one invalid or incomplete answer discards the whole batch, and a retry either does not happen (a validation failure) or gives the same
answer (7 of 9 failed `vote_cast` batches). A fallback per decision instead of per batch would keep the good answers; it is a candidate,
not a decision, and it changes what the fallback rates mean, so it should land with its own before/after run.

## After the run: what to read

1. `digest.json`: outcome, `llm_fallback_rates`, `llm_fallback_alerts`, `llm_retries`, `elapsed_seconds`, the terms and `office_occupancy`.
2. `llm_calls_summary.json` and `llm_calls.jsonl`: time by decision type, the thinking-budget bind rate (the share of `chamber_deliberation` and `vote_cast` decisions that reach
   2,048 reasoning tokens; 41 to 45% and 25% on the 2-year p100 run), and every `finish_reason='length'`.
3. **The replay proof:** `scripts/run_polity_flagship.py` with the same flags as the run (`--engine llm --years 30 --population 500 --seats 75 --seed 42 --max-batch-replays 2
   --workers 12 --reproducibility relaxed --run-id <run-id>`, and the same `VOTE_MODE` if it was set), plus `--replay-calls-from <run-dir>` and an `--output-dir` of its own, on CPU
   (no server needed). It must reproduce `events.jsonl` byte for byte, and it refuses to start if the recorded `config_hash` differs from the flags it is given.
   This is the test of the claim that the call log is a sufficient record. **Untested for a stopped and resumed run:** `--replay-calls-from` replays a whole run from
   tick 0 and cannot itself `--resume`, and a resume appends to the same call log, so if the run was interrupted, expect to find out here whether the log still replays.
4. **The prompts:** `llm_prompts.jsonl` gives, per `call_id`, the system prompt, the user prompt and the JSON schema the model was asked (`llm_call_log.read_prompts`).
   Read the ones behind every fallback, every `finish_reason='length'` and every decision you find odd in the explorer, next to the model's reasoning in `llm_calls.jsonl`.
5. **The explorer**: walk the run tick by tick (presidents and their terms, recalls, the chamber, the citizen biographies). Note anything that looks wrong as an OBS entry (see `observations.md`).
6. **The narrative:** `/log-run` writes `TIMELINE.md` beside the events, and `/log-session` the journal entry.
7. **The server and the GPU:** the acceptance length over time and the preemption count in `<run-id>.vllm.log`, the utilisation and temperature curve in `<run-id>.telemetry.jsonl`.
8. Compare with the p100 sweep (`office_occupancy` 0.93, standard deviation 0.05) and with `sweep-8y-p500-seed1` and `-seed2`.

## The improvement backlog, ranked by what makes the run cleaner

| # | Item | Evidence | Note |
|---|---|---|---|
| 1 | One invalid answer discards its whole batch (chamber 5 units, `reaction_to_event` 25, `vote_cast` 3), and validation failures are not retried | OBS-021, OBS-024, OBS-025 | Chamber: 5.8 to 7.1% of units over three seeds, 361 of 362 failed calls are the shift or delta bound. Candidates: replay a rejected answer like a decode failure, drop zero-delta shifts before the count, or fall back per decision instead of per batch. None is done. |
| 2 | Positioning thinking has no cap | S2.4 results (PR #648), OBS-022 | It cost 3 of 11 elections their first attempt in the full run (about 230 s each). It needs a bank arm before a budget can be measured (`THINKING_ARM_TYPES` covers only vote and chamber). |
| 3 | Party nominations: out-of-range and last-listed | OBS-006, OBS-013 | Watch `party_nomination_choice` per election; the call log records the reasoning. |
| 4 | About 40% declare candidacy | OBS-011 | A contract defect the run amplifies. |
| 5 | Two decision types stay unverified | OBS-007, S2.4 | The lever is the decision contract, not the model. |
| 6 | Speed: EAGLE-3 and 12 workers are in, at p500 for the first time | `check_vllm_eagle3_results.md` | The timing probe measures it; the smaller KV pool is the thing to watch. |
| 7 | Reproducibility across servers | OBS-020 | Replay is the guarantee, and the full run showed it holds (byte-identical replay). The cause is open. The owner does not need more, given the logs above. |
| 8 | The 2,048 budget binds on 72 to 86% of `vote_cast` calls | OBS-023, OBS-024 | Measure whether 4,096 or no budget changes the winner or the ranking, and whether it stops the nine failed batches that answer for one voter of three. |

## Safeguards built in, and their limits

- **Detached from the editor** (OBS-014): `systemd-run --user`. **Limit:** `Linger=no`, so a desktop logout stops it.
- **Kept awake:** an inhibitor blocking sleep, idle and shutdown. **Limit:** `systemctl poweroff -i` overrides it, and so does pulling the plug; the run then resumes from its checkpoint.
- **Disk floor** (OBS-016): a watchdog stops the run cleanly below 8 GiB. **Limit:** it polls once a minute.
- **Output outside any worktree and off `/tmp`:** `~/Documents/Dev/polity-runs/full`, so removing a worktree cannot delete the run (a worktree cleanup on 2026-09-25 deleted a set of runs that lived inside three worktrees).
- **The record is written as it goes, and survives a stop:** the server log, the GPU sample and the prompts are flushed as they are written, and the helpers stop with the run
  (`BindsTo`) rather than outliving it. The call log flushes each line, so a `kill -9` of the runner costs at most a half-written last line. **Limit:** the prompts writer disables
  itself on a write error rather than stopping the run, so a full disk costs the prompts before it costs the run, and only the run's own output would say so.
- **Tested 2026-09-26 with a stand-in process:** the launcher refuses to start when the pre-flight fails; a unit runs under the inhibitor; SIGTERM reaches the child so it can write its digest;
  the watchdog prints a readable message, stops the run and disappears with it. **Not tested:** a real run, on purpose.

## Preparation tracker

| Item | Status |
|---|---|
| Config validated for 30 years at population 500 | **DONE** 2026-09-26 |
| Pre-flight: `scripts/prepare_full_run.py` | **DONE**, run against this machine |
| Launcher: `scripts/launch_full_run.sh` (dry run by default): 12 workers, relaxed, prompts, server log, telemetry, server inspect | **DONE**, mechanics tested with a stand-in |
| EAGLE-3 adopted in `docker-compose.llm.yml` | **DONE**, PR #656 (verified: 3 clean restarts, determinism, acceptance about 3.3) |
| Prompts kept beside the call log (`llm_prompts.jsonl`) | **DONE**, PR #655 |
| The run visible in the explorer as root `full` | **DONE** (`~/Documents/Dev/polity-runs/polity-ui.sh`, outside the repo) |
| Decisions D1, D2 | **DECIDED** 2026-09-26: EAGLE-3, relaxed with 12 workers |
| Decisions D3 to D6 | **TODO**, the owner's (the defaults stand until then) |
| Timing probe (2 years at population 500) | **SKIPPED**: the first 8 ticks of the run served as one |
| The run | **DONE** 2026-09-26, 2 h 08 min; replay proof passed; results above, OBS-021 to OBS-023 |
| Seeds 1 and 2 | **DONE** 2026-09-27, 1 h 59 and 2 h 05; compared above, OBS-024 and OBS-025 |
