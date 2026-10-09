# D2 — founders told the seat threshold: neutrality before and after, and the W2.1 gate

`docs/plan/PLAN_BEYOND_CI.md` D2 and W2.1 step 1; ADR-018 "Amendment 2026-10-08".

## Setup

- Command: `python scripts/check_agent_prompt_neutrality.py --probe forum`, with the default `--n 30`.
- Server: vLLM 0.31.0 serving `qwen3:8b` at temperature 0.6.
- Citizens: phase-4 seed-2 citizens (`eng-8y-p100-seed2`).
- Run on 2026-10-08:
  - **Before**: from a worktree whose `agents.py` equals `origin/polity` at 6c80077.
  - **After**: from this branch.

## Before (the forum prompt without the threshold sentence)

```
forum party move
  cell                      wording                 none            join           leave           found
  too few would co-found    shipped                 100%              0%              0%              0%
  too few would co-found    paraphrase               94%              6%              0%              0%
  enough would co-found     shipped                   3%              0%              0%             97%
  enough would co-found     paraphrase                3%              0%              0%             97%
  SENSITIVITY  PASS  largest shift 97% across whether enough citizens would co-found a new party (noise band 7% at n=30; raise --n to resolve a smaller one)
  DEAD OPTION  FAIL  never taken: ['leave']; always taken: none
  WORDING      PASS  paraphrase moves 6%, the state moves 97%

1 check(s) failed across 1 probe(s)
```

## After (with "a party with less than 5% of the votes cast for parties wins no seat")

```
forum party move
  cell                      wording                 none            join           leave           found
  too few would co-found    shipped                  88%             12%              0%              0%
  too few would co-found    paraphrase               94%              6%              0%              0%
  enough would co-found     shipped                   3%              0%              0%             97%
  enough would co-found     paraphrase                3%              0%              0%             97%
  SENSITIVITY  PASS  largest shift 97% across whether enough citizens would co-found a new party (noise band 7% at n=30; raise --n to resolve a smaller one)
  DEAD OPTION  FAIL  never taken: ['leave']; always taken: none
  WORDING      PASS  paraphrase moves 6%, the state moves 97%

1 check(s) failed across 1 probe(s)
exit 1
```

## Reading

- **Unchanged verdicts.** Sensitivity is 97% both times, wording moves 6%, and `leave` is dead in both runs. The dead `leave` option predates this change.
- **One cell moved.** Citizens who could not found answered `join` 12% of the time after the change and 0% before. That is above the ±7% band at n=30 for one wording, while the paraphrase stayed at 6%. It is small and recorded as is; the change states a seat rule, not a reason to join.

## The W2.1 gate: STOP (2026-10-09)

Run after the reboot, from the `fast_api_voter/` of a worktree on `feat/winner-strip` (ae59f343, whose `fast_api_voter/` equals `polity` 9201bc58), vLLM 0.31.0 serving `qwen3:8b`:

```
python scripts/check_agent_prompt_neutrality.py --probe threshold --n 60
```

```
100 citizens from eng-8y-p100-seed2, 60 per cell per wording, model qwen3:8b at temperature 0.6

W2.1 gate: does founding follow the stated seat threshold? (60 able founders, each told 3% then 7%)
  found at 3%: 59/60    found at 7%: 59/60
  only at 3%: 1   only at 7%: 1   exact McNemar p = 1
  GATE  STOP  founding does not move with the threshold at this n: the experiment stops here (PLAN_BEYOND_CI W2.1)

1 check(s) failed across 1 probe(s)
exit 1
```

Founding does not follow the stated threshold. Most of the 60 are told they have 7 or more backers, so founding at 7% is consistent with the rule for them; the 14 told 5 or 6 are the test, and at least 13 of them founded at 7% anyway (OBS-044 gives the backing counts).
By the plan's rule the threshold experiment stops here (`docs/plan/PLAN_BEYOND_CI.md` W2.1), and the finding is
recorded as OBS-044 in `docs/plan/polity/observations.md`.

The first attempt (2026-10-08) hit an unattended NVIDIA library upgrade (kernel module 595.91, userspace 595.99:
"Driver/library version mismatch"), so it ran only after a reboot.

Its logic was checked with stand-in answers in place of the model, on the same checkpoint (30 able founders):

- an agent that founds at 3% and never at 7%: 30/30 vs 0/30, exact McNemar p = 1.86e-09, **PASS**;
- an agent that ignores the threshold: 30/30 vs 30/30, p = 1, **STOP**.

The gate compares 3% with 7%, the ends of the plan's (3, 5, 7%) range. D1's main run compares 3% with 5%, so a PASS here does not promise a response at 3 vs 5. That is a reason to size the pilot on the 3-vs-5 difference, not to skip the gate.
