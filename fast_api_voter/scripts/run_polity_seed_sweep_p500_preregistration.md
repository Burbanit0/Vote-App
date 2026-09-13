# p500 seed sweep — pre-registration

Step S0.7 of `docs/plan/polity/plan-polity-build-order.md`, written 2026-09-13 and
committed before any run of this batch starts. The batch itself is S0.8. It launches
only on the project owner's decision D5. Its results doc is the summary
`run_polity_seed_sweep.py` generates, read against this file and nothing else.

## Question

At population 500, does the p100 sweep's picture hold? Specifically:

1. `office_occupancy` stays at or above the project's 0.70 bar.
2. No decision type crosses the 10% fallback alert.

And how much does one seed's result move between two runs of that same seed, compared
with how much it moves between seeds?

## Design

| | |
|---|---|
| Runs, in order | seed 1, seed 2, seed 42, seed 1 again (`sweep-8y-p500-seed1-rep2`) |
| Shape | 8 years, population 500, 75 sortition seats, `--max-batch-replays 2`, LLM engine |
| Election | single-tick (no `--staggered-election`), as in the p100 leg and the Stage 3 scale probe, so the legs differ by scale only |
| Server | `vllm/vllm-openai:v0.28.0`, `Qwen/Qwen3-8B-AWQ` @ `4da05a8e`, per §4.2 of `plan-distribution-positions-seeds.md` (no stack bump before this batch). The one compose change since the p100 leg, `--enable-prompt-tokens-details` (S0.5), adds usage reporting and, per vLLM's documentation, does not touch generation; this is documented behaviour, not re-measured |
| Code | one commit for all four runs, run from a dedicated git worktree checked out at the S0.7 merge, so development elsewhere cannot change the code a later run imports. The summary's provenance section checks this from each run's `run_metadata.json`. A mixed batch is reported as mixed and is not read against this pre-registration |
| Expected duration | about 5.2 h per run (the 8-year p500 scale probe `scaleprobe-8y-p500-v2-postfix` took 5.23 h), about 21 h for the batch |

Command, from `fast_api_voter/` in the dedicated worktree:

```bash
python scripts/run_polity_seed_sweep.py --population 500 --years 8 --seats 75 \
  --seeds 1,2,42,1 --max-batch-replays 2 --output-dir scripts/seed_sweep_runs \
  --hypothesis "p500, 8y: office_occupancy stays >= 0.70 and no decision type exceeds the 10% fallback alert across seeds 1, 2, 42; a second seed-1 run diverges less than the seeds do" \
  --decision-criterion "Pre-registered in scripts/run_polity_seed_sweep_p500_preregistration.md (S0.7): three red flags, evaluated in the generated sweep summary; n=3 seeds is not an equivalence test"
```

A crashed run is resumed with `--resume-sweep`, which continues it from its checkpoint.
A run that cannot be completed is reported as missing, never replaced by a fresh run of
another seed.

## Red flags

Any one of these, raised in the generated summary, means the p100 picture does not carry
over as-is. They are evaluated mechanically in `api/domain/polity/sweep_statistics.py`:

1. **`office_occupancy` below 0.70** in any completed run.
2. **Any decision type above 10% fallback** in any completed run. `party_nomination_choice`
   is included: it fell back 67% of the time in the Stage 3 scale probe before its fix.
   The rate is fallbacks over decisions from `progress.json`; exactly 10% does not raise.
3. **Same-seed divergence beyond the across-seed spread.** The flag is raised when
   |`office_occupancy`(seed 1, repeat 2) − `office_occupancy`(seed 1, repeat 1)| exceeds
   the range of first-run `office_occupancy` across seeds 1, 2 and 42.

## What will be reported, and what will not be claimed

Reported, from the generated summary:
- per-run results;
- the provenance check;
- `office_occupancy` mean, stdev, 95% BCa bootstrap interval and 95% prediction interval
  over the first run of each seed;
- pooled per-type fallback rates with 95% Clopper–Pearson intervals;
- the three flags, each raised, clear or not evaluable.

Not claimed, whatever the numbers:
- **Equivalence with the p100 leg.** Three seeds cannot establish it. With n = 3 the BCa
  interval is close to the min–max range and the prediction interval is wide.
- **That any single seed represents population 500.**
- **That clear flags validate the model's decisions.** They say the mechanics hold at
  this scale, not that the decisions are good.

A clear result permits the next step: the 30-year flagship is gated on it
(`plan-flagship-30y-run.md`). A raised flag sends the batch to diagnosis first, using each
run's `llm_calls.jsonl` (S0.5) and replay (S0.6).
