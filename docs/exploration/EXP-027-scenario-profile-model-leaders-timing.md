# EXP-027 — The scenario profile with the model playing the leaders: the first timing

- **Date**: 2026-11-16 UTC (run 13:47Z to 14:23Z) · **Status**: measured; the number settles the speed half of the 2026-10-21 condition, and says nothing yet about variety · **Real cost**: 36 min of local GPU for the run, about 3 min more for the server to load; no rented compute
- **Verdict in one sentence**: with the crowd decided by rules and the model playing only the president, nominees, coalition leaders, forum and chamber votes, one 8-year, 100-citizen run takes 35.8 minutes and 609 model decisions with no fallback, where the exploration profile (the crowd by model) took about 100 minutes; this is one seed and one commit, and it says nothing about whether the model's leaders make the runs more varied.

## Starting hypothesis

`plan-scenarios-v1.md` step 2 moved the crowd to rules so the model would only play the leaders, on the condition recorded on 2026-10-21 that this "improves speed and reliability". The scenario profile had never been run with the model, so neither half of the condition had a number. Stage 2a of `polity-state-2026-11.md` is that number: one run, alone on the GPU.

## Protocol

`polity-runs/stage2a/chain.sh`, on the `polity` tip `1456fef5` (a detached worktree, so the commit is fixed), vLLM `v0.31.0` (the pin; started by the script, stopped by it afterwards):

```
run_polity_flagship.py --engine llm --profile scenario --years 8 --population 100 --seats 15 --seed 42 \
    --workers 24 --reproducibility relaxed --max-batch-replays 2   (POLITY_LOG_PROMPTS=1)
```

The shape is the one of OBS-052's 8B baseline and of `founding-lock-ab` (8 years, p100, 15 seats, seed 42, 24 workers, relaxed), so wall clock and call counts can be set side by side. Model `qwen3:8b` (Qwen3-8B-AWQ on vLLM), thinking budget 2,048. The server was idle (about 460 MiB used, nothing on :8000) before the start. Numbers below are from `digest.json`, `progress.json` and `llm_calls.jsonl` of the run; the call table counts `kind == "decision"` rows only.

## What it found

- **Wall clock: 2,147.9 s (35.8 min) for 32 ticks**, an average of 67 s a tick (`progress.json` read one tick at 167 s at tick 24). The two `founding-lock-ab` runs, exploration profile, same shape, took 103 and 100 minutes, but they shared the server with each other, so this is not a controlled ratio: it says "about a third", not "2.8 times".
- **609 model decisions, 0 fallbacks, 4 retries** (the digest's `llm_fallback_alerts` is empty). The exploration profile, with the crowd by model, recorded 0 to 15 fallbacks per run at this size (OBS-051).
- **Where the time goes** (decision calls only, 212.7 call-minutes across 24 workers):

| decision | calls | p50 s | p95 s | share of call time | thinking at the budget |
|---|---:|---:|---:|---:|---:|
| `forum_post` | 330 | 20.0 | 28.8 | 52% | 43 (13%) |
| `amendment_vote` | 135 | 19.9 | 29.2 | 21% | 4 (3%) |
| `coalition_turn` | 75 | 28.5 | 42.6 | 16% | 39 (52%) |
| `nominee_turn` | 31 | 32.0 | 44.1 | 7% | 26 (84%) |
| `president_turn` | 38 | 13.8 | 15.5 | 4% | 22 (58%) |

  "At the budget" means the call's reasoning reached 2,046 tokens (`thinking_token_budget` minus 2, as in OBS-054), so it was cut, not finished. Across the three leader turns that is 87 of 144 calls (60%), which is the 62-100% range `plan-rented-gpu-runs.md` reports for leader and chamber turns; the forum and the chamber vote rarely hit it here.
- **The forum is half the model time** for 330 of the 609 calls, with the forum capped at 10 speakers a tick (ADR-032's scenario setting). The leaders together are 27% of the time.
- **Budget probes cost about 12%.** The log carries 604 further rows, `kind == "budget_probe"`: one-token calls that check the budget, not decisions. They add 27.6 call-minutes (11.5% of the model's call time). Their `finish_reason` is `length` by design, so a count of `length` finishes over the whole log reads as 50% failures when it is not.
- **What the run did, as a description, not a finding** (one seed): 3 presidential elections (citizen 13 won at tick 0 and again at tick 16, citizen 90 at tick 32), 2 legislative elections, 2 coalitions, no recall; 43 parties founded and 23 dissolved, 16 parties standing at tick 8 and 26 at tick 24, an effective number of parties by seats of 9.9 and 10.1 at the two legislative elections; 9 amendments proposed and 9 resolved, 6 of them ratified; 13 bills; 17 citizens replaced. The party churn is lower than OBS-052's 47 and 30 but not low, with the founding lock on; this is the profile's first run, so it is not compared with anything.

## What it cost

36 minutes of local GPU and about 3 minutes of server start; my own time was the setup (a worktree, a chain script, a CPU wiring check of 0.2 s) and this note. The probe was alone on the GPU, as asked, and vLLM was stopped by the script afterwards (439 MiB used at the end).

## Verdict and why

The speed half of the condition holds, on one seed: the scenario profile is about a third of the exploration profile's time. The reliability half is a count, not a verdict: 0 fallbacks in 609 decisions says the model's answers were decodable, not that they were right (no ground truth exists for agent turns: Stage 3a), and OBS-053's finding that the schema is never shown to the model still applies to all five of these turns.

What this note does **not** show: whether the model's leaders make the runs more varied than the rule-only twin, which is Stage 2b's question (ten seeds, one commit, placed on the rule catalogue's archetype map); and whether one seed is typical (one run, no spread). Ten seeds run one after the other would take about six hours at this rate; two at once would be quicker per pair and slower per run, which this probe did not measure.

## What I take from it (portable)

- Count a call log by `kind` before reading it: a log that records probes next to decisions makes any rate over all rows wrong (here, 50% `length`).
- A timing taken from two runs sharing a server cannot be turned into a ratio; say "about a third", name the sharing, and run the controlled one only when the decision needs it.
- The first run of a new profile is a description. Resist the story the 43 and 23 invite until there are ten seeds.
