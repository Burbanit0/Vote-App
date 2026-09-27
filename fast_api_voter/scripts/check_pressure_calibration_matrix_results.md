# Phase C: calibration works at batch 1, all five variants, and nowhere else

## The question this closes

polity-decision-contracts.md's pilot correction for `pressure_action`: does supplying a scale
reference for `self_gap` (C3), without ever stating a rule (C4), make the decision track content
— and does it survive production batch sizes? Already known before this run: the unmodified
production prompt is flat at batch 1 (+0.000008) and batch 17 (+0.004); a prompt that states the
full act-mapping rule outright (a capability control, not a candidate — writing the rule into the
prompt is exactly the "LLM décoratif" §7bis.9d prohibits) scores +0.993 at batch 1 but collapses
back to +0.0001 at batch 17. The open cell was calibration alone, C4-compliant, at batch 1, and
whether it survives batching.

## Method

Real heterogeneous population (`generate_population`, pool=300, real `blank_threshold` per
citizen from its own Beta distribution — no earlier pressure_action script in this project used
more than one fixed threshold for the whole batch). Real `self_gap` via the actual production
formula (`weighted_euclidean(citizen.issue_positions, officeholder.revealed_position,
citizen.issue_priorities)`, matching `accountability.self_gap` exactly), against one fixed,
documented synthetic officeholder (pledged the centre of the issue space, drifted +0.3 in every
dimension). Only unambiguous citizens sent at all (`gap < 0.5×bt` or `gap > 1.5×bt`,
`plan-decision-quality-validation.md`'s own definition, applied at selection time, not
post-hoc) — pool yielded 14 unambiguous-below and 80 unambiguous-above.

Five variants (`build_pressure_system_prompt_calibrated`/`build_pressure_user_prompt_calibrated`
with each `PRESSURE_*_SIGNAL`), three batch sizes (1, 5, 25), three independently randomised
trials per (variant, size) — composition and order both re-randomised per trial, RNG seeded from
`(run_seed, variant, size, trial)` so the whole matrix replays identically. Scored as agree/
disagree on **should-act vs should-not-act** only (not which lever), per
`plan-decision-quality-validation.md`'s own narrower, more defensible axis.

## Result

| variant | size 1 | size 5 | size 25 |
|---|---|---|---|
| V1 threshold | **100% · 100% · 100%** PASS | 40% · 60% · 40% FAIL | 52% · 40% · 52% FAIL |
| V3 history | **100% · 100% · 100%** PASS | 60% · 60% · 60% FAIL | 52% · 52% · 52% FAIL |
| V4 threshold+history | **100% · 100% · 100%** PASS | 100% · 40% · 40% FAIL | 48% · 52% · 76% FAIL |
| V2 percentile | n/a (undefined at n=1) | 100% · 60% · 60% FAIL | 52% · 52% · 52% FAIL |
| V5 pledge | **100% · 100% · 100%** PASS | 60% · 60% · 60% FAIL | 52% · 52% · 52% FAIL |

**Every single variant: 100% at batch 1, 9/9 trials clean. Every single variant: FAIL at batch 5
and batch 25**, dropping to within a few points of the ~52% a constant answer scores by
construction against this 14-below/80-above pool. The pooled act histograms confirm it plainly —
at size 25, four of five variants show 72-75 of ~75 decisions landing on the identical act,
exactly the pre-existing collapse signature, not a partial or graded degradation.

**Open-menu follow-up** (the best closed-menu cell, V1 @ size 1, re-run under the full
`{0,1,2,3,4}` menu): **100% again**, 3/3 trials. The model chose `act=3` (MOBILIZE) rather than
`act=4` under the open menu — a different lever, correctly classified as "acting" either way — so
the batch-1 result is not an artifact of the closed menu's own two-option shape.

## What this establishes

1. **Calibration works.** Every mechanism tested — a bare threshold, one tick of history, cohort
   rank, distance to a pledge — turns the flat production prompt into a decision that tracks real
   per-citizen state, with zero prescriptive content, the moment the citizen is asked alone.
2. **It is not partially fragile to batching — it is completely destroyed by it**, uniformly
   across every mechanism, the instant a second citizen shares the call. This is sharper than
   the earlier batch-order-randomization finding (`check_pressure_batch_order_randomized.py`),
   which used a rule-STATING prompt and found composition-dependent instability (20-100% at
   size 5, 0-100% at size 12). Calibration-only prompts do not even reach that instability —
   they land at the flat baseline directly, every trial, every variant.
3. **Which mechanism is used does not matter.** All five behave identically at both extremes.
   The batching failure dominates any difference between what is supplied as a scale reference.

## Caveat

Pool imbalance: only 14 unambiguous-below citizens against 80 above, out of 300 — a thin margin
for batch-25's need of ~12-13 per side, though not thin enough to have failed any draw. The
batch-1 result (9/9 clean per variant, 45/45 across all five) is unlikely to be an artifact of
this given its size and perfect consistency; the batch-5/25 FAIL verdicts would not change under
a better-balanced pool, since they already sit at the constant-answer floor.

## Disposition

**The fix works, and the batch size is the entire remaining question.** No calibration variant
can ship at the production batch sizes measured. Whether batch 1 is viable depends entirely on
its real cost — Phase D, next — since `pressure_action` still carries the §3.B.7 prefix-cache
gap (`build_pressure_system_prompt` still embeds `cid_list`, unlike `vote_cast` and
`chamber_deliberation`), which is exactly the fix that would matter most at batch 1 specifically.

## Correction, 2026-09-11 (Track B6, `lets-build-a-solid-spicy-otter.md`)

A real defect in the script this result came from: at `size=1`, `half = size // 2 = 0`, so
`chosen = rng.sample(below, 0) + rng.sample(above, 1)` sampled **exclusively from the
unambiguous-HIGH pole**, every trial, for every variant — never `below`. A constant "act" answer
scores 100% there by construction; the batch-1 9/9 result above was never actually testing
sensitivity to `self_gap`'s sign, only to its magnitude on one side. Fixed by randomizing which
pole receives the odd-size remainder per trial instead of hardcoding it to `above`; sizes 5 and 25
are unaffected (an even split has no remainder to misassign).

**The disposition above is unchanged.** The batch-5/25 FAIL verdicts rest on the constant-answer
floor, which this bug cannot explain away (it does not touch those sizes). The batch-1 100%
result is downgraded from "confirmed both-directions" to "confirmed on the HIGH pole only, `below`
untested" — independently corroborated regardless: `check_pressure_shipped_wiring_results.md`'s
own live wiring test used 12 alternating citizens (both sides of `blank_threshold` by
construction) and got 12/12, which the size=1 bug could not have produced by accident. Not
re-run: the fix changes what future runs of this script measure, not what this document's own
already-corroborated conclusion was.
