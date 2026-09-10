# Phase D: batch size 1 costs 2.8×, not 25× — and the reason is not the one hypothesized

## The question, and the number that turned out to be wrong

Every framing of this problem going in — including the plan's own — treated "batch size 1 costs
~25× the calls" as the central risk to measure. That framing conflated **call count** with
**wall-clock cost**. It measures cleanly different, and the answer is decisive.

## Method

Real wall-clock (`time.perf_counter`), real prompt token counts (`count_prompt_tokens`, not
estimated), and vLLM's own prefix-cache hit-rate log line, for a 25-citizen population (the
shipped `llm.max_batch_size`) replayed at sizes 25/5/3/1, using the **calibrated** builders
(Phase B, `PRESSURE_THRESHOLD_SIGNAL` — the cheapest of the four Phase C validated) with real
`think=False` production calls (`complete_json`, not the logprobs variant — this measures what
`decide_pressure_actions` would actually send).

Two arms per size: `fixed` (the real, current builders, §3.B.7 already applied) and `legacy` — a
byte-for-byte local reconstruction of what those same builders looked like *before* that fix
(the per-chunk cid list embedded in the system prompt), kept only in this script as a comparison
artifact, never a live code path. Confirmed structurally before running live: the legacy system
prompt does embed the raw cid list, the fixed one does not, and the legacy user prompt lacks
`expected_cids`.

## Result

| size | arm | calls | total | ms/call | mean prompt tokens | hit rate |
|---|---|---|---|---|---|---|
| 25 | legacy | 1 | 2.55s | 2553.5 | 2575.0 | 46.1% |
| 25 | fixed | 1 | 2.69s | 2691.8 | 2604.0 | 46.1% |
| 5 | legacy | 5 | 3.26s | 652.8 | 958.0 | 46.1% |
| 5 | fixed | 5 | 3.29s | 658.3 | 988.0 | 46.1% |
| 3 | legacy | 9 | 4.33s | 480.9 | 778.4 | 50.3% |
| 3 | fixed | 9 | 4.23s | 469.8 | 808.4 | 50.3% |
| 1 | legacy | 25 | 7.67s | 306.9 | 634.8 | 55.6% |
| 1 | fixed | 25 | 7.58s | 303.1 | 664.8 | **61.3%** |

**Batch size 1 costs 2.8–3.0× batch size 25's wall-clock time — not 25×.** Per-call latency drops
sharply as batch size shrinks (2554ms → 303ms), because most of a call's latency here is fixed
overhead (network round-trip, scheduling, the model's own per-request setup) rather than
prompt-token processing — these prompts are small (600–2600 tokens) and generation is short
(`think=False`). More, smaller calls costs far less than the naive "N× the calls = N× the time"
model predicts.

## Where the original hypothesis was wrong

The plan's own framing predicted the §3.B.7 prefix-cache fix would be *why* batch 1 turns out
affordable — "likely separates 'batch 1 costs 25×' from 'batch 1 costs ~3×'." **That mechanism is
not what happened.** The fix's own contribution at batch size 1: legacy 7.67s vs fixed 7.58s —
**98.8% of legacy's time**, essentially no wall-clock difference. Batch 1 is affordable regardless
of whether the prefix-cache fix is applied at all; the real reason is the fixed per-request
overhead noted above, not prompt-cache reuse.

The one place the two arms do diverge is the hit-rate reading at size 1 (55.6% legacy vs 61.3%
fixed) — a real, if modest, signal that the fix does something. But the hit-rate readings
throughout are **not cleanly isolated per arm**: they are read from a rolling `docker logs
--since 20s` window immediately after each arm's own burst, and consecutive arms' bursts run
close enough together that a reading can reflect a mix of both. The wall-clock numbers, measured
directly around each arm's own calls with no such contamination, are the reliable metric here —
and they say the fix's contribution to *this specific cost question* is small.

## Extrapolation

Using the real anchor already in this project's own plan (`plan-flagship-30y-run.md`'s Phase 7
scale-probe: 137 real `pressure_action` decisions in one real tick) and `polity_config.yaml`'s
own shape (`ticks_per_year=4 × duration_years=30` = 120 ticks):

| | calls/tick | ms/call (measured) | s/tick |
|---|---|---|---|
| batch=25 (shipped) | 6 | 2691.8 | 16.15 |
| batch=1 (calibrated) | 137 | 303.1 | 41.53 |

**Difference: +25.4s/tick, +0.85h over the full 30-year run** — against the ~35.6h whole-run
baseline (every decision type combined, not `pressure_action` alone). Under 2.5% of total runtime.

This is a linear extrapolation from one real per-tick anchor and this script's own measured
per-call cost, not a second full measured run — reported as that, not as a re-measured flagship
total. It uses the *fixed* arm's own numbers throughout, since that is what would actually ship.

## Disposition

**Batch size 1 is affordable.** The plan's own central cost concern — the "25×" framing that
motivated deferring this decision to a real measurement rather than a model — does not survive
contact with real numbers. The true cost is a rounding error against the flagship run's own
total. Combined with Phase C's own result (calibration clears 100% agreement at batch 1, fails
everywhere else), there is now a real, affordable, quality-clearing configuration to ship.

The prefix-cache fix (§3.B.7, already committed) is kept regardless of this measurement's
verdict on its cost contribution: it is a pure, zero-risk simplification independent of the
batch-size question (`build_pressure_system_prompt` becoming a config-only constant is valuable
on its own terms), and the earlier verification of it (`check_pressure_prefix_cache_fix_results.md`)
already established it as correctness-neutral.
