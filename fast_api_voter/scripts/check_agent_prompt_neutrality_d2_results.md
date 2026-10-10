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

Founding does not follow the stated threshold. Most of the 60 are told they have 7 or more backers, so founding at 7% is consistent with the rule for them; the 14 told 5 or 6 are the test, and at least 13 of them founded at 7% anyway (OBS-045 gives the backing counts).
By the plan's rule the threshold experiment stops here (`docs/plan/PLAN_BEYOND_CI.md` W2.1), and the finding is
recorded as OBS-045 in `docs/plan/polity/observations.md`.

The first attempt (2026-10-08) hit an unattended NVIDIA library upgrade (kernel module 595.91, userspace 595.99:
"Driver/library version mismatch"), so it ran only after a reboot.

Before the run, the gate's logic was checked with stand-in answers in place of the model, on the same checkpoint (30 able founders):

- an agent that founds at 3% and never at 7%: 30/30 vs 0/30, exact McNemar p = 1.86e-09, **PASS**;
- an agent that ignores the threshold: 30/30 vs 30/30, p = 1, **STOP**.

The gate compares 3% with 7%, the ends of the plan's (3, 5, 7%) range; 5% was not asked. A PASS would not have promised a response at D1's 3 vs 5, and the pilot would have been sized on that difference. With no response even between the ends, there is no pilot.

## The answers logged (2026-10-10, OBS-045)

From the `fast_api_voter/` of `feat/polity-threshold-gate-log` (base `polity` 772736d6), vLLM 0.31.0 serving `qwen3:8b`,
the same phase-4 seed-2 checkpoint, at 79890945. The gate printed founding by backing and how many rationales at 7%
mention a threshold or a percentage, and wrote every answer as JSON lines. That last count also caught founders' own
shares ("8% support"), so the next commit replaced it with "answers at 7% that name the seat bar (7%, a seat,
votes)", which is 0/60 for both runs below, recomputed from their logs.

**Shipped wording** (`--probe threshold --n 60 --gate-log gate-answers.jsonl`, 3 min 14 s):

```
W2.1 gate: does founding follow the stated seat threshold? (60 able founders, each told 3% then 7%; founding rule worded: shipped)
  found at 3%: 56/60    found at 7%: 59/60
  only at 3%: 1   only at 7%: 4   exact McNemar p = 0.375
  backing   n  found at 3%  found at 7%
        5   4            4            4
        6  10            8           10
        7   5            5            5
        8   9            8            9
        9   4            4            4
       10   7            6            7
       11   3            3            3
       12   9            9            8
       13   6            6            6
       14   2            2            2
       16   1            1            1
  rationales at 7% that mention the threshold or a percentage: 22/60
  GATE  STOP  founding does not move with the threshold at this n: the experiment stops here (PLAN_BEYOND_CI W2.1)
```

**The founding rule as a count** (`--gate-wording count`): "at least 5% of the citizens" becomes "at least 5 of the
100 citizens", the same fact without its percentage. The party roll still gives each party's share of the citizens
as a percentage.

```
W2.1 gate: does founding follow the stated seat threshold? (60 able founders, each told 3% then 7%; founding rule worded: count)
  found at 3%: 60/60    found at 7%: 58/60
  only at 3%: 2   only at 7%: 0   exact McNemar p = 0.5
  backing   n  found at 3%  found at 7%
        5   4            4            4
        6  10           10           10
        7   5            5            5
        8   9            9            9
        9   4            4            4
       10   7            7            7
       11   3            3            3
       12   9            9            8
       13   6            6            6
       14   2            2            2
       16   1            1            0
  rationales at 7% that mention the threshold or a percentage: 14/60
  GATE  STOP  founding does not move with the threshold at this n: the experiment stops here (PLAN_BEYOND_CI W2.1)
```

**What the answers cite** (rationale, note to self and post together; read by hand where a count needed it):

| wording | told | n | name the seat bar | name the founding rule | call their own share a threshold | say "threshold" unqualified |
|---|---|---:|---:|---:|---:|---:|
| shipped | 3% | 60 | 0 | 29 | 1 | 1 |
| shipped | 7% | 60 | 0 | 26 | 1 | 1 |
| count | 3% | 60 | 0 | 6 | 0 | 9 |
| count | 7% | 60 | 0 | 9 | 0 | 7 |

"Name the seat bar" is the bar the founder was told, a seat, or votes. "Name the founding rule" is "5%" ("meets the 5%
threshold with 6 citizens closer to my positions"), "the 5-citizen threshold" or "the founding threshold". Own shares
read "8% support meets the threshold". Unqualified answers read "6 citizens closer to my positions meets the
threshold", which could be either rule. Reading: OBS-045's follow-up.
