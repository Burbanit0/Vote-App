# EXP-027 — The scenario profile with the model playing the leaders: the first timing

- **Date**: 2026-11-16 UTC (run 13:47Z to 14:23Z) · **Status**: measured; it gives the first time and call count for this profile, and says nothing yet about variety · **Real cost**: 36 min of local GPU for the run, about 3 min more for the server to load; no rented compute
- **Verdict in one sentence**: with the crowd decided by rules and the model playing only the president, nominees, coalition leaders, forum and chamber votes, one 8-year, 100-citizen run took 35.8 minutes for 609 model calls (604 decisions and 5 retried calls) with no fallback, where two exploration-profile runs of the same shape took about 100 minutes for 1,173 and 1,309 calls; it is one seed on one commit, the two profiles differ in what they ask the model, and the run's own plausibility check failed on three measures.

## Starting hypothesis

`plan-scenarios-v1.md` step 2 moved the crowd to rules so the model would only play the leaders, on the condition recorded on 2026-10-21 that this "improves speed and reliability". The scenario profile had never been run with the model, so neither half of the condition had a number. Stage 2a of `polity-state-2026-11.md` is that number: one run, alone on the GPU.

## Protocol

`polity-runs/stage2a/chain.sh`, on the `polity` tip `1456fef5` (a detached worktree, so the commit is fixed), vLLM `v0.31.0` (the pin; started by the script, stopped by it afterwards):

```
run_polity_flagship.py --engine llm --profile scenario --years 8 --population 100 --seats 15 --seed 42 \
    --workers 24 --reproducibility relaxed --max-batch-replays 2   (POLITY_LOG_PROMPTS=1)
```

The shape is the one of OBS-052's 8B baseline and of `founding-lock-ab` (8 years, p100, 15 seats, seed 42, 24 workers, relaxed). Model `qwen3:8b` (Qwen3-8B-AWQ on vLLM), thinking budget 2,048. `nvidia-smi` showed an idle card and nothing on :8000 before the start (read in the session, not logged by the script). Numbers below come from `digest.json`, `progress.json`, `events.jsonl` and `llm_calls.jsonl` of the run; the call table counts `kind == "decision"` rows only.

## What it found

- **Wall clock: 2,147.9 s (35.8 min) for 32 ticks**, an average of 67 s a tick.
- **609 model calls, 0 fallbacks.** The digest counts 604 decisions (`agent_turn` 64, `amendment_vote` 135, `coalition_decision` 75, `forum_post` 330); the call log has 5 more `decision` rows, which are retried calls, all `president_turn` (attempt 1 four times, attempt 2 once). The digest's `retry_count` of 4 counts retry events; the log shows 5 retried calls. Every retry is the president's turn, the longest prompt (3,898 tokens on average).
- **Where the time goes** (decision calls only, 212.7 call-minutes across 24 workers):

| decision | calls | p50 s | p95 s | share of call time | thinking at the budget |
|---|---:|---:|---:|---:|---:|
| `forum_post` | 330 | 20.0 | 28.8 | 52% | 43 (13%) |
| `amendment_vote` | 135 | 19.9 | 29.2 | 21% | 4 (3%) |
| `coalition_turn` | 75 | 28.5 | 42.6 | 16% | 39 (52%) |
| `nominee_turn` | 31 | 32.0 | 44.1 | 7% | 26 (84%) |
| `president_turn` | 38 | 13.8 | 15.5 | 4% | 22 (58%) |

  "At the budget" means the call's reasoning reached 2,046 tokens (`thinking_token_budget` minus 2, as in OBS-054), so it was cut, not finished. Across the three leader turns that is 87 of 144 calls (60%). That fits the 8B per-type rates in `plan-rented-gpu-runs.md` (president 65%, nominee 83%, coalition 38%); the 62-100% range quoted there for leader and chamber turns covers both models; the 8B's own rates are 38-83%.
- **The call time is spread over about six workers, not 24.** 212.7 call-minutes in 35.8 minutes of wall clock is an average concurrency of about 6, so a type's share of call time is not its share of wall clock. The forum is 52% of call time, with the forum capped at 10 speakers a tick (ADR-032's scenario setting); the leaders together are 27%. Whether the forum or the concurrency limits the run is not measured here.
- **Budget probes cost about 12% of call time.** The log carries 604 further rows, `kind == "budget_probe"`: one-token calls that check the budget, not decisions. They add 27.6 call-minutes (11.5% of the total, 13% of the decision time). Their `finish_reason` is `length` by design, so a count of `length` finishes over the whole log reads as 50% failures when it is not.
- **Compared with the exploration profile** (the two `founding-lock-ab` runs, same shape, 2026-10-21, older code, run at the same time on one server): 102.6 and 99.7 minutes, 1,309 and 1,173 decision calls. Those runs also made calls this one does not: 365 and 301 `pressure_action`, 115 and 114 `chamber_deliberation`, 18 and 16 `vote_cast`; and 516 and 513 forum posts against 330 here. The speed-up is the sum of these (the crowd by rule, the forum cap of 10) and of the profile's other settings; it is not an effect of "the model playing only the leaders" alone, and the ratio is not a controlled one.
- **Fallbacks are not comparable either.** The exploration profile recorded 0 to 15 fallbacks per run at this size (OBS-051), where they were in `chamber_deliberation`, a decision this profile does not call. 0 in 609 says the five agent-turn types decoded, not that they were right: there is no ground truth for agent turns (Stage 3a), and 60% of the leader turns ended at the thinking budget, which on the 8B's vote calls was where wrong answers came from (OBS-054).
- **What the run did, as a description** (one seed): 3 presidential elections (citizen 13 won at tick 0 and again at tick 16, citizen 90 at tick 32; turnout 0.84, 0.90, 0.92), 2 legislative elections, both with no majority, 2 coalitions, no recall; 43 parties founded and 23 dissolved, 16 parties standing at tick 8 and 26 at tick 24, an effective number of parties by seats of 9.9 and 10.1; 9 amendments proposed and 9 resolved, 6 of them ratified; 13 bills; 17 citizens replaced. **The digest's own plausibility check failed on `enp_seats`, `turnout` and `volatility`, and labels the run's archetype `fragmentation`.** So the first model-led run already sits outside three of the bands the catalogue is read against; Stage 2b should read that before it reads variety.

## What it cost

36 minutes of local GPU and about 3 minutes of server start; my own time was the setup (a worktree, a chain script, a CPU-only wiring check) and this note. The probe was alone on the GPU, as asked, and vLLM was stopped by the script afterwards.

## Verdict and why

The run is faster than the exploration profile's two runs, by about a third of the time and about half the calls, for reasons that are the profile's design, not a measured effect of the leaders. The reliability half of the condition is a count and not a verdict (above). The model-led scenario run lands in `fragmentation` and fails three plausibility measures, on one seed.

What this note does **not** show: whether the model's leaders make the runs more varied than the rule-only twin, which is Stage 2b's question (ten seeds, one commit, placed on the rule catalogue's archetype map); whether one seed is typical (one run, no spread); and what limits the run's speed (the average concurrency of about 6 suggests it is not the 24 workers). Ten seeds run one after the other would take about six hours at this rate; two at once would be quicker per pair and slower per run, which this probe did not measure.

## What I take from it (portable)

- Count a call log by `kind` before reading it: a log that records probes next to decisions makes any rate over all rows wrong (here, 50% `length`). And say which count a number is: decisions, calls and retry events were three different numbers in this one run.
- A comparison across profiles is a comparison of what each asks the model; name the calls that differ before naming a ratio.
- Read the run's own plausibility verdict before the story the numbers invite. The 43 and 23 parties, and a pass of the speed condition, are easy to read as good news.
