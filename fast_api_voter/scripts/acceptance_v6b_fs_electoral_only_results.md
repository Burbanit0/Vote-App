# v6b acceptance run — elected vs. sortition (§6bis.3), Lot 4

n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this project has already named. The elected side runs under `--menu electoral_only`: `écart(t) ≡ 0` by construction (no petition, no street pressure, `passive_erosion_weight: 0.0`), so `L(t)` converges to `m` and never crosses the shipped `recall_floor` -- the office stays occupied for the whole run. This removes the vacancy confound the `both` runs hit (`office_occupancy = 0.333`, `mandate_deviation_coverage = 0.0`) STRUCTURALLY, without disabling accountability the way `--recall-floor 0.0` did. The cost is stated rather than hidden: a president facing none of §7bis's three channels is not §6bis.3's own literal comparison subject, so any drift observed here is drift under NO measurable pressure at all. `social_graph.enabled`/`events.enabled` stay OFF throughout, the same confound-avoidance call v5 Lot 5 and v6a Lot 4 already made independently. Unlike v6a Lot 4, this comparison needs BOTH quantities from the SAME run at the SAME ticks, so there is no prior acceptance row to cite -- this is one new, self-contained run.

This directory's own runs used `--menu electoral_only --recall-floor 0.2`.

| menu | engine | years | elapsed(s) | replays | office_occupancy | mean L (last) | recalls | mandate_dev (mean/max) | mandate_dev unified (mean/max) | chamber_dev (mean/max) | motif mix | last seated size |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| electoral_only | deterministic | 8 | 1.5 | 0 | — | 0.770 |  | —/— | —/— | 0.000/0.000 (known 0.0, no LLM call) | — | 30 |
| electoral_only | llm | 8 | 15037.1 | 11 | 1.000 | 0.720 |  | 0.000/0.000 | 0.048/0.170 | 0.000/0.000 | 701=0.999, 702=0.001 | 30 |

## §6bis.3's own headline question

*« L'absence de pression électorale produit-elle des décisions plus « sincères » (alignées sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de responsabilité) ? »*
- Compare `mandate_dev (mean/max)` against `chamber_dev (mean/max)` in the `llm` row above: a materially LOWER chamber_deviation than mandate_deviation is the signature of insulation producing more sincere (less drifted) decisions; a comparable or higher chamber_deviation would say the opposite -- that accountability pressure alone doesn't explain the elected side's own drift.
- `motif mix` (701 SINCERE_POSITION vs 702 DELIBERATIVE_SHIFT) is the model's own stated label for each decision -- not enforced by any coherence rule (v6b Lot 3's own removed validator), so it is informative but non-binding: a chamber that stays mostly 701 is sincere by its own account; a chamber that trends toward 702 is not, independent of whether the resulting `chamber_deviation` values are themselves large or small.
- `last_seated_size` cross-checks v6b Lot 2's own pool-exhaustion calibration finding (`sortition_calibration_results.md`) lands the same way inside a real LLM run: the chamber should stay at or near `seats=30` for the whole run once the relaxed-pool fallback engages.
- **Not claimed here**: the sortition chamber's own institutional consequence (veto power, design doc point ouvert n°11) -- this MVP is comparison-only, with no lawmaking concept for a veto to act on.

---

# Findings (hand-written — a re-render of this file DROPS this section)

Everything above this line is rendered from `metrics.json`/`chamber.json` by `--summarize`.
Everything below is hand-narrated from the journal and from a one-off population check, the
same convention `acceptance_v6b_results.md` already follows. Re-render only if you are
prepared to re-attach this section.

Run configuration worth stating explicitly, because it is the variable that made this run
possible at all: `citizens.position_dist: factor_structure` (the shipped default since
commit `a3ebfa9`). The two earlier `uniform` v6b runs reached ~6-9% office occupancy; the
`factor_structure` `both` run reached 33.3%; this `electoral_only` run reaches **100%**.

## 1. The pre-registered criterion is cleared, and `L` behaves exactly as §7bis.6 predicts

`office_occupancy = 1.0` against the script's own pre-registered `>= 0.70` bar — the bar the
`both` run failed at 0.333. Zero recalls, `recalls_by_trigger = {}`. And `mean_legitimacy` is
**flat at `m` within each term** to three decimals: 0.720 across ticks 0-15, 0.850 across
16-31, 0.720 again at 32 (a fresh election). That is the `L ≡ m` fixed point §7bis.6 defines
as the control case, observed on the LLM path rather than assumed from the formula. The
deterministic sibling probe predicted 0 recalls and `L ≈ 0.77`; the realized LLM values
bracket it (0.72, 0.85). On this quantity the deterministic probe was accurate — worth
contrasting against office occupancy, where the same probe over-predicted by roughly 2×.

## 2. `clamped_at_bound` did its job on a real run, for the first time

The observability event added in commit `397d0ac` — which closes `apply_shifts`'s own
long-standing "KNOWN OBSERVABILITY GAP" docstring note — fired **8 times** here, and the
breakdown is exactly what it was built to expose:

| tick | citizen | decision | dimensions |
|---|---|---|---|
| 0 | 48 | `campaign_positioning` | [0] |
| 0 | 44 | `campaign_positioning` | [1] |
| **8** | **42** | **`representative_response`** | **[0]** |
| **9** | **42** | **`representative_response`** | **[0]** |
| **13** | **42** | **`representative_response`** | **[0, 1]** |
| **15** | **42** | **`representative_response`** | **[0, 1]** |
| 32 | 48 | `campaign_positioning` | [0] |
| 32 | 44 | `campaign_positioning` | [1] |

Read it against the `mandate_deviation_unified` series: it climbs 0.000 → 0.164 over ticks
1-10, then **sits at exactly 0.164 for ticks 10, 11, 12 and 13** before edging to 0.170 at
14-15. Before this event existed, that plateau was indistinguishable from "the model stopped
conceding" — and the only way to tell the difference was the throwaway, uncommitted
unclamped-shadow reconstruction the earlier investigation had to write by hand (documented in
`THEORY.md` §10.9/§10.10 at ×2.8-×3.6 above the clamped figure). Here the four clamp events on
president 42's own dimensions 0 and 1 land squarely inside that plateau, and the diagnosis is
readable **from the journal alone**. The consequence for the headline number is direct and must
be carried forward: `mandate_deviation_unified` max = 0.1702 is a **clamped, understated**
figure, not the drift the model actually asked for.

## 3. The president conceded 13 times to a population that never once acted

This is the run's most surprising result and it deserves stating flatly: `inaction_rate` is
**exactly 1.0 on every tick from 0 to 15** — across the entire first mandate, not one citizen
of the consulted cohort chose any act other than `NOTHING` — and during those same sixteen
ticks president 42 returned `stance = concession` on **thirteen** of them. The lever counts for
the whole run are `{0: 383, 4: 16}`: 383 explicit non-actions, 16 deferrals to the next
election, zero mobilizations and zero petitions (structurally impossible under this menu).

So the drift measured here is not a response to pressure. There was no pressure to respond to.
§7bis.6's central claim is that a representative who fully betrays their mandate before a
passive population loses no legitimacy; what this run shows is the mirror image the claim
does not cover — a representative who *concedes* to a passive population, unprompted, while
their legitimacy sits flat at `m` and no citizen has moved. Whether that is the model
reasoning about an anticipated future electorate, or an artifact of a prompt that asks for a
reaction every single tick, is not answerable from this run.

## 4. Third confirmation of the `top_k_priorities` blindness — this time journaled in band

`mandate_deviation` (the shipped top-k scope) reads **0.0000 on all 33 ticks** while
`mandate_deviation_unified` reaches 0.1702 on the same events. `mandate_deviation_coverage` is
`0.0`: not a single `mandate_deviation_recorded` event fired, because the censored path's own
`deviation_log_threshold = 0.1` was never crossed by a quantity that never left zero.

This is the third independent run to show the effect, and the first where the corrected figure
was **journaled in band** by production code rather than reconstructed post-hoc by a script
that was never committed. The provenance gap the production-wiring work targeted is closed for
this run: `0.048 / 0.1702` has a real, tested producer in the repository.

## 5. The elected-vs-sortition comparison, and why n=2 limits what it can support

| | mean | max | observations |
|---|---|---|---|
| Elected — `mandate_deviation_unified` | 0.0479 | 0.1702 (clamped) | 33 ticks |
| Sortition — `chamber_deviation` | 0.000000 | 0.000000 | 990 deliberations |

The chamber never moved. 989 of 990 deliberations returned `SINCERE_POSITION`; the single
`DELIBERATIVE_SHIFT` came back with an empty `shifts` list, so it is a label without a
movement behind it (the coherence validator was removed in v6b Lot 3 for reliability reasons,
so the motif is stated, not enforced). By its own account and by measurement, the insulated
chamber is **sincere, not erratic** — §6bis.3's own question gets its first answer from a run
that clears its own validity criterion.

**The elected side of that comparison rests on two individuals who behaved oppositely, and
they did not start from comparable positions.** President 42 (ticks 0-15) conceded on 13 of 16
ticks; president 2 (ticks 16-31) returned `silence` on 16 of 16 and never moved at all. A
one-off check against the regenerated seed-42 population explains most of the difference
structurally rather than behaviorally:

| | pledge distance to population centre of mass | position spread (σ) | citizens above their own `blank_threshold` |
|---|---|---|---|
| President 42 | 0.1495 | 0.152 | **29 / 99** |
| President 2 | **0.0963** | **0.071** | **15 / 99** |
| population reference | 0.1939 (mean) | 0.193 (mean) | — |

President 2 is a near-centrist — 7th closest of 100 citizens to the centre of mass on their
sincere position, with a platform sitting between 0.327 and 0.583 on every one of the 20
dimensions — facing roughly half the discontent president 42 faced. Pledge and sincere
position say the same thing here: their campaign shift (dt=5) is only 0.0123, against 0.0702
for president 42. Their zero drift is therefore substantially a
"nothing to concede" case, not a demonstrated resistance to pressure (and there was, per
finding 3, no pressure to resist). The honest reading is narrow: **drift is reachable on the
elected side and was not reached once in 990 opportunities on the chamber side** — not that
election as an institution causes drift and sortition prevents it. That claim needs more than
one seed and two presidents.

## 6. Reliability

11 replays, all absorbed at `attempt 1/3`, none exhausted: **8 `vote_cast`, 3
`chamber_deliberation`**. Against ≥1 290 calls from those two decision types alone (both run
at chunk size 1: 300 `vote_cast`, 990 `chamber_deliberation`), plus every other decision
type's own batches, that is under 1% — the same order as the 0.6% measured on the
`factor_structure` `both` run.

The composition matters more than the rate. Three of the eleven landed on
`chamber_deliberation`, a decision type whose system prompt was **not** touched by the
`cast_votes` ranking-rule fix and which has no `ranking` concept at all. That reproduces, on a
third independent run, the residual truncation floor that put this investigation on line 2 of
its own decision matrix rather than line 1 — and keeps the written `build_ranking` fallback
scope (plan §2.3) justified rather than academic.
