# 10-seed sweep at 8y/p100 — Track D, 2026-09-12/13 (`lets-build-a-solid-spicy-otter.md`)

## What was checked

Every published polity result to date was n=1 on a seed (42) already shown once to
be unrepresentative — `plan-distribution-positions-seeds.md`'s own open §4.3
`seed_representativeness: unvalidated` marking. This is the first real answer to
that question, at the smaller of the two shapes Track D scoped (8y/population 100;
the 8y/population 500 batch, sized to also exercise `party_nomination_choice`'s
own scale-dependent fallback, is not run yet).

## Method

`scripts/run_polity_seed_sweep.py` (Track D's own thin driver, `llm_test_harness`-
registered) — 10 seeds (1 through 10), each a real, independent `run_polity_
flagship.py --engine llm --years 8 --population 100 --seats 15` subprocess against
the production vLLM server. Seed 1 needed a standalone retry after a real,
now-fixed bug in the driver's own `--resume-sweep` logic (a leftover, checkpoint-
less run directory from an earlier interrupted attempt made it pass `--resume` to
a run with nothing to resume from) — the retry used the corrected driver and
produced a clean result identical in shape to every other seed. Total wall clock:
~11.5h for the 10 runs, averaging ~1h/run (in line with the plan's own pre-measured
1.14h/run estimate).

## Result

| seed | office_occupancy | fallback alerts (>10%) |
|---|---|---|
| 1 | 0.9697 | none |
| 2 | 0.9697 | `representative_response` 30.3% |
| 3 | 0.9697 | `representative_response` 36.4% |
| 4 | 0.9091 | none |
| 5 | 0.8788 | none |
| 6 | 0.8182 | none |
| 7 | 0.9697 | none |
| 8 | 0.9091 | none |
| 9 | 0.9697 | none |
| 10 | 0.9394 | none |

**`office_occupancy`, n=10: mean 0.9303, stdev 0.0516, min 0.8182, max 0.9697.**

## Reading it

**Track A's presidency-vacancy fix generalizes across seeds, not just the one it
was verified on.** Before Track A, the chronic vacancy was measured at
`office_occupancy` ≈ 0.15–0.33 across every run this project had produced (all on
seed 42 or close variants). This sweep's mean of 0.93, in a tight band (stdev
0.052, every single seed above 0.81), is the first multi-seed confidence figure
for that fix and settles the seed-representativeness question for this metric at
this population size: a single seed was not, and did not need to be, hiding a
materially different outcome.

**`representative_response`'s fallback alert (Track C2's own >10% bar) fired on 2
of 10 seeds (2 and 3), both early in the sweep, quiet on the other 8** (seeds 5, 6,
7, 8, 9, 10 had zero fallbacks at all; seed 1 had 6, seed 8 had 1 — all under the
10% bar). Read carefully: this is **not** a re-opening of B1's own partial fix
(that work was about `representative_response`'s content-blind collapse
signature, a different question from its raw fallback rate) — the fallback rate
measures how often the model's *decode/validation* fails outright, not whether
its answer is content-sensitive. Two hits out of ten is not enough to call a
pattern (a rate that low is exactly the kind of thing Track C2's own alert
threshold was built to surface without immediately over-interpreting), but it is
a real, seed-linked data point: nothing else in the sweep flagged at all, and this
type flagged twice. Worth a closer look if it recurs in the p500 batch or in a
future, larger sweep — not actionable on its own yet.

## What this does not settle

- **`party_nomination_choice`'s own scale-dependent fallback** (measured 67% at
  p500 in Stage 3, never seen at p100 scale) is untouched by this batch on
  purpose — it needs the p500 seeds, not these.
- **Per-type fallback rates for every OTHER decision type** were tracked (Track
  C2's own `llm_fallback_rates` field, in each run's `digest.json`) but not
  summarized here — this document reports only what the pre-registered hypothesis
  named (`office_occupancy`, and which types crossed the alert bar). The full
  per-type numbers are in each seed's own `digest.json`
  (`scripts/seed_sweep_runs/sweep-8y-p100-seed<N>/run/sweep-8y-p100-seed<N>/digest.json`,
  gitignored run output, not committed) for anyone who wants to look deeper.
- **The p500 batch itself.** Scoped (seeds 1, 2, 42 — the last chosen specifically
  to tie back to Stage 3's own already-analyzed run at the same population), built,
  and ready to launch, but not run as of this document.
