# Thinking budget, serial replay: pre-registration (2026-10-21, before any call)

Follow-up to `thinking_budget_live_preregistration.md` and its results. That experiment ended "unresolved": the 2048 arm's two
repeats of identical bytes disagreed on 10.4% of voter units, above the 5% guard. The replay was at temperature 0 with seed
42, so sampling is not the cause. The calls ran 8 at a time on one vLLM server (EAGLE-3). Question: **is the flip a property of
concurrent batching, or of the 8B's thinking itself?**

**Material.** 80 vote cases drawn (seed 20261022) from the 255 vote cases of `cases.jsonl` that ended at the budget originally.
All 80 were in the concurrent experiment, so each has a concurrent twin: same bytes, same budget, same repeats.

**Arms.** `thinking_token_budget` 2048 and 8192, 2 repeats per case, **one call at a time** (workers = 1), nothing else on the
server. 2048 first. Same client, temperature 0, seed 42, as before.

**Outcome.** The noise floor of an arm: the share of voter units (where the rule says a candidate is acceptable) whose E2 differs
between repeat 0 and repeat 1, the same statistic as the first experiment. Compared with the floor of the same 80 cases in the
concurrent experiment. Also: the share of units whose E2 differs between serial repeat 0 and concurrent repeat 0.

**Decision (on the 2048 arm, the arm the guard concerns; the 8192 arm is reported the same way).** Let S be the serial floor, C the
concurrent floor on the same cases:
- S <= 5%: **the flip is concurrency.** The guard is met when calls run one at a time; the full budget experiment should be
  replayed serially (4 arms, an estimated 9 h on the 8B) and its registered rule applied then.
- S > 5% and S >= C / 2: **the flip is the model's thinking, not the batching.** The 5% guard cannot be met on this server at any
  concurrency; restating the guard (or accepting the verdict "unresolved" on this test) is the owner's decision.
- S > 5% and S < C / 2: **partly concurrency.** Reported as such; no further run is decided here.

**Power.** About 270 units per repeat pair, so a floor near 5% has a standard error near 1.5 points; a floor within 2 points of
the guard is called as it falls, and said to be close.

**Not done here**: the chamber, the 4096 and "none" arms, any claim about elections.
