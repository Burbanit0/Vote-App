# Plan — the full run: 30 simulated years at population 500

> **Living document, English, like `plan-flagship-30y-run.md`, which it picks up.** That plan built
> the runner, checkpointing and observability (Phases 0-6) and left Phase 7, "the run", as `TODO`
> since 2026-09-11. Since then the serving stack, the defaults and the known defects all moved.
> This is the run's own tracker: what is decided, what is not, what to expect, how to start it,
> what to read afterwards. Written 2026-09-26. **The run has not been started.**

**Status: preparation DONE, the run is TODO and its date is the owner's.** The owner's stated plan:
run it as it stands, see what can be improved, then work on it to make it as clean as possible.

## What this run is for

The flagship arm: 30 simulated years (120 ticks), population 500, 75 sortition seats, LLM engine on
vLLM / Qwen3-8B-AWQ, one worker, checkpointing on. It answers the production question the earlier plan
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
| engine and server | `llm`, `qwen3:8b` on vLLM, temperature 0, `llm.reproducibility: strict`, 1 worker |
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
| D1 | Serving: the shipped server (no speculation) or EAGLE-3 | shipped | EAGLE-3 makes 8-year runs about 38% shorter and answers on the two capped families identically (`check_vllm_eagle3_results.md`), but adopting it is a change to `docker-compose.llm.yml` that nobody has made. If you adopt it, do it in its own PR and run the timing probe on it. |
| D2 | Reproducibility: `strict`, 1 worker, or `relaxed`, 12 workers | strict | Strict for this first run: it matches every earlier p500 run and the flagship plan, and it is reproducible from its seed (modulo OBS-020) and from its call log. Relaxed is faster by an amount nobody has measured at this scale; measure it with the probe below before choosing it. |
| D3 | Fix OBS-021 (chamber fallbacks) first, or run as it stands | as it stands | As it stands: the run is the baseline the fix is measured against. Choose otherwise only if 460 to 1,100 chamber fallbacks would make the run unreadable to you. |
| D4 | Seed | 42 | 42, for comparability with the p500 batch. |
| D5 | Apply the Stage 4 result (`awakening_anxiety` 0.25) or keep emotions off | off | Off: it is a mechanism change, and the run's first job is to be a baseline. |
| D6 | Timing probe first | yes | Yes (below): two simulated years at population 500 turn the cost estimate into a measurement, for one to two hours of GPU time (8 ticks at 5 to 14 minutes). |

## Cost

**Measured, on the current code and server, one worker, strict (2026-09-25):** an 8-year, 100-citizen run takes
1,891 s, 1,785 s and 2,277 s (32 ticks), which is 62 s per tick; on EAGLE-3, 1,173 s and 1,098 s, which is 35 s per tick.
**Last uninterrupted p500 measurement:** 7.29 h for 8 years (`sweep-8y-p500-seed2`, 13.7 min per tick), on the
earlier setup (vLLM 0.28.0 with n-gram speculation, `vote.mode: llm`, no thinking budget), before the changes that
halved the p100 times.

**Estimate, an inference:** if a p500 tick costs five times a p100 tick, the run takes about **10 h on the shipped
server and about 6 h on EAGLE-3**. Election ticks are 8 to 10 times an ordinary tick (the last tick of `sweep-8y-p500-seed2`,
an election, took 61 minutes), so expect long silences. Projecting the old p500 measurement instead gives about 27 h, which is
the upper bound if the estimate is wrong. **The probe replaces the guess.**

**Disk:** the p500 outputs of an 8-year run are 2.5 to 4.5 MB of events, 2.6 MB of census and 0.9 MB of checkpoint; 30 years is
well under 1 GB. The risk is not this run's own files but everything else on the disk (OBS-016), which is why the launcher watches it.

## Day-of sequence

Nothing here needs to be done until the owner decides to start. `PY` is the Python with the backend dependencies
(`~/Documents/Dev/Vote-App-polity/fast_api_voter/.venv/bin/python`).

1. **Merge this branch**, then work from a clean checkout of `polity`, so the run records a pushed commit:
   `git worktree add ../Vote-App-run origin/polity` (detached), and `cd ../Vote-App-run/fast_api_voter`.
2. **Start the server** (`docker compose -f docker-compose.llm.yml up -d`, or the EAGLE-3 file if D1 says so) and wait until it is healthy.
3. **Dry run:** `PY=$PY scripts/launch_full_run.sh`. It runs `scripts/prepare_full_run.py` and prints what `--go` would do; it starts nothing.
   Fix every `FAIL`. Two `WARN`s are expected and harmless when launched this way: the launcher detaches the run, so the
   editor-process-tree warning is about the shell you are typing in, not the run. `Linger=no` matters: it means logging out of
   the desktop session would stop the run. `loginctl enable-linger $USER` fixes it, and it is a system change, so it is not done for you.
4. **Timing probe (recommended):** `YEARS=2 PY=$PY scripts/launch_full_run.sh --go`. It uses the same path with two years (8 ticks) and its own
   run id. Read the per-tick time from `progress.json` and multiply by 120, election ticks aside. Decide D1 and D2 on it.
5. **The run:** `PY=$PY scripts/launch_full_run.sh --go`. It starts the run as a `systemd-run --user` unit, off this terminal and off any editor
   (OBS-014), under an inhibitor that blocks sleep, idle and shutdown, with a watchdog that stops the run cleanly if free disk falls below 8 GiB.
6. **Watch it** (the launcher prints these):
   - status `systemctl --user status polity-<run-id>`, log `tail -f <out>/<run-id>.log`.
   - one line: `jq -r '"tick \(.tick)/\(.total_ticks) (year \(.simulated_year)), last tick \(.last_tick_duration_seconds/60|floor) min, eta \(.eta_seconds/3600*10|floor/10) h, fallbacks \(.fallback_count), retries \(.retry_count)"' <run-dir>/progress.json`
   - fallback rate by type: `jq -r '. as $p | .decisions_by_type | to_entries[] | select(.value>0) | [.key, .value, ($p.fallback_by_type[.key] // 0)] | @tsv' <run-dir>/progress.json | awk -F'\t' '{printf "%-26s %6d %4d %6.1f%%\n", $1, $2, $3, 100*$3/$2}' | sort -k4 -rn`
   - alive or stuck: `$PY scripts/check_run_liveness.py <run-dir>`. **Never kill a run for silence alone**: on 2026-09-11 a healthy run was killed after
     an hour of legitimate silence and about 2 h of GPU work was lost (the script's own docstring).
   - the explorer, live: `~/Documents/Dev/polity-runs/polity-ui.sh start`, then http://localhost:3000/polity, root `full`. The run is listed as soon as it
     has written its journal, config and census, and is re-read as its files change.
7. **Stop and resume:** `systemctl --user stop polity-<run-id>` sends SIGTERM, the runner writes its digest, and `launch_full_run.sh --go --resume` continues
   from the last per-tick checkpoint (byte-identical to an uninterrupted run, Phase 3). After a `kill -9` or a power cut there is no digest, and the same
   `--resume` works from the checkpoint. If a resume complains about an empty `digest.json`, move it aside (OBS-016).

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
- **Same-seed re-runs are not always byte-identical (OBS-020).** The guarantee is replay from the call log.

## After the run: what to read

1. `digest.json`: outcome, `llm_fallback_rates`, `llm_fallback_alerts`, `llm_retries`, `elapsed_seconds`, the terms and `office_occupancy`.
2. `llm_calls_summary.json` and `llm_calls.jsonl`: time by decision type, the thinking-budget bind rate (the share of `chamber_deliberation` and `vote_cast` decisions that reach
   2,048 reasoning tokens; 41 to 45% and 25% on the 2-year p100 run), and every `finish_reason='length'`.
3. **The replay proof:** `scripts/run_polity_flagship.py` with the same flags, the same `--run-id` and `--replay-calls-from <run-dir>`, on CPU. It must reproduce `events.jsonl` byte for byte.
4. **The explorer**: walk the run tick by tick (presidents and their terms, recalls, the chamber, the citizen biographies). Note anything that looks wrong as an OBS entry (see `observations.md`).
5. **The narrative:** `/log-run` writes `TIMELINE.md` beside the events, and `/log-session` the journal entry.
6. Compare with the p100 sweep (`office_occupancy` 0.93, standard deviation 0.05) and with `sweep-8y-p500-seed1` and `-seed2`.

## The improvement backlog, ranked by what makes the run cleaner

| # | Item | Evidence | Note |
|---|---|---|---|
| 1 | Chamber answers rejected on the shift-count cap are never retried | OBS-021 | Candidates: replay a rejected answer like a decode failure, or drop zero-delta shifts before the count. Neither is done. |
| 2 | Positioning thinking has no cap | S2.4 results (PR #648) | It needs a bank arm before a budget can be measured (`THINKING_ARM_TYPES` covers only vote and chamber). |
| 3 | Party nominations: out-of-range and last-listed | OBS-006, OBS-013 | Watch `party_nomination_choice` per election; the call log records the reasoning. |
| 4 | About 40% declare candidacy | OBS-011 | A contract defect the run amplifies. |
| 5 | Two decision types stay unverified | OBS-007, S2.4 | The lever is the decision contract, not the model. |
| 6 | Speed: EAGLE-3, or 12 workers | `check_vllm_eagle3_results.md` | D1 and D2 above. |
| 7 | Reproducibility across servers | OBS-020 | Replay is the guarantee; the cause is open. |

## Safeguards built in, and their limits

- **Detached from the editor** (OBS-014): `systemd-run --user`. **Limit:** `Linger=no`, so a desktop logout stops it.
- **Kept awake:** an inhibitor blocking sleep, idle and shutdown. **Limit:** `systemctl poweroff -i` overrides it, and so does pulling the plug; the run then resumes from its checkpoint.
- **Disk floor** (OBS-016): a watchdog stops the run cleanly below 8 GiB. **Limit:** it polls once a minute.
- **Output outside any worktree and off `/tmp`:** `~/Documents/Dev/polity-runs/full`, so removing a worktree cannot delete the run (a worktree cleanup on 2026-09-25 deleted a set of runs that lived inside three worktrees).
- **Tested 2026-09-26 with a stand-in process:** the launcher refuses to start when the pre-flight fails; a unit runs under the inhibitor; SIGTERM reaches the child so it can write its digest;
  the watchdog prints a readable message, stops the run and disappears with it. **Not tested:** a real run, on purpose.

## Preparation tracker

| Item | Status |
|---|---|
| Config validated for 30 years at population 500 | **DONE** 2026-09-26 |
| Pre-flight: `scripts/prepare_full_run.py` | **DONE**, run against this machine |
| Launcher: `scripts/launch_full_run.sh` (dry run by default) | **DONE**, mechanics tested with a stand-in |
| The run visible in the explorer as root `full` | **DONE** (`~/Documents/Dev/polity-runs/polity-ui.sh`, outside the repo) |
| Decisions D1 to D6 | **TODO**, the owner's |
| Timing probe (2 years at population 500) | **TODO** |
| The run | **TODO** |
