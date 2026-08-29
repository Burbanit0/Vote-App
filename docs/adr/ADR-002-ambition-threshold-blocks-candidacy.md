# ADR-002: the shipped candidacy configuration cannot hold an election — problem stated, fix deferred

**Status**: Open — problem named and measured, decision deliberately deferred
**Date**: 2026-08-29
**Context**: found while discharging §3 of
`plan-distribution-positions-seeds.md` (the population-distribution chantier),
not while looking for it

> **Where the supporting evidence lives**: the measurement is a deterministic
> probe (seconds, no LLM), run from a scratchpad script per this project's own
> convention for such probes — it is not committed. Its full four-cell table,
> its protocol, and the reproduction instructions are written into
> `plan-distribution-positions-seeds.md` §3.1, which is the authority for the
> numbers quoted below. `THEORY.md` §10.10 carries the reader-facing summary.

## Context

`candidacy.ambition_threshold: 0.7` is described in the shipped config as
"seuil du chemin dominant" — the gate on the *dominant* candidacy path.
`decide_candidacy` (`simple_rules.py`) is a bare
`citizen.ambition_score >= config.ambition_threshold`, and `ambition_score` is
drawn from `citizens.ambition_dist: beta(2,8)`.

Those two shipped values are incompatible. `beta(2,8)` has mean 0.2 and puts
almost no mass above 0.7. Measured against the real production pipeline
(`generate_population` → `initialize_parties` → `assign_party_affiliation` →
`select_party_nominee` → `declare_candidacy` → `build_ranking` →
`get_presidential_winner`), 40 seeds, `population_size: 100`:

| `position_dist` | `ambition_threshold` | eligible citizens (mean/100) | nominees (mean) | seeds with NO candidate |
|---|---|---|---|---|
| `uniform` | 0.0 | 100 | 5.00 | 0/40 |
| `uniform` | **0.7 (shipped)** | **0.03** | **0.03** | **39/40 (97.5%)** |
| `factor_structure` | 0.0 | 100 | 5.00 | 0/40 |
| `factor_structure` | **0.7 (shipped)** | **0.03** | **0.03** | **39/40 (97.5%)** |

**At the shipped value, 39 seeds out of 40 produce zero candidates and no
election is held at all.** This is not a distribution artifact: the result is
identical under `uniform` and under `factor_structure`, because the blocker is
the `(ambition_dist, ambition_threshold)` pair, which is orthogonal to citizen
positions. And `candidacy.rupture_path_enabled: false` ships too, so
`decide_candidacy` is the *only* candidacy path at the shipped configuration —
there is no fallback route.

Two consequences that make this worth its own entry rather than a footnote:

- **Every acceptance script silently works around it.**
  `run_acceptance_comparison.py`, `run_v5_acceptance.py`,
  `run_v6a_acceptance.py`, `run_v6b_acceptance.py` and
  `run_cascade_acceptance.py` all force `ambition_threshold=0.0` via
  `dataclasses.replace`, each carrying a comment to the effect that this
  "guarantees a real elected president". That comment reads as a convenience.
  It is not: it is a precondition for the electoral mechanism to exist.
- **No published result has ever exercised the shipped value.** Everything in
  `THEORY.md` §10.4 through §10.9 — legitimacy, mandate deviation, the
  pressure levers, the spark, contagion, the sortition comparison — was
  measured at `ambition_threshold=0.0`.

This was found on 2026-08-29 while verifying a hypothesis the distribution
chantier had explicitly left open (§3: "`ambition_threshold=0.0` may remain a
distinct, legitimate design choice — to be verified empirically once §2 is
settled, not assumed"). The hypothesis is false, but in the opposite direction
to the one anticipated: the parameter was not masking a residual position
problem, it is load-bearing on its own.

## Decision

**None today. The problem is named, measured, and deferred.**

This is deliberate, for the same reason the distribution chantier refused to
touch this parameter in the first place: picking a fix is a modelling
judgment, not a bug fix, and it should not be made as a side effect of closing
an unrelated investigation. Changing either value also changes
`generate_population`'s RNG stream or the candidate pool of every future run,
so it is a re-baselining decision as much as a calibration one.

Nothing is blocked by leaving it open: every acceptance script already
overrides the value explicitly, and the override is now documented at the
config site rather than implicit.

## What the next pass must do FIRST — before any calibration question

**Priority 1: stop the failure from being silent.** Running `run_simulation`
at the shipped defaults today produces zero candidates, zero elections, and
**no error, no warning, no journal signal** — the run completes "successfully"
and simply contains no democracy. That is a worse defect than a mis-calibrated
value, and it is worse for a specific reason: a bad value is at least
detectable by looking at the results, whereas a mechanism that silently
degrades to nothing gives an observer a clean-looking run with no indication
that anything is missing. Every acceptance script happens to override the
value, so this has never bitten a published run — but it is exactly the shape
of defect that costs hours the first time someone runs at defaults and trusts
the output.

Whatever form it takes — a `PolityConfigError` at load time when
`(ambition_dist, ambition_threshold)` cannot produce a candidate pool, a
run-time guard when an election tick finds zero nominees, or a journal event
making the empty candidacy explicit — the guard should land **before** the
calibration debate below is opened, and is independent of how that debate
resolves. It is also the cheaper of the two: it needs no re-baselining
decision, no RNG-order change, and no target rate to be agreed.

## The open question (after the guard, not before)

Three candidate resolutions, none evaluated here:

1. **Calibrate `ambition_dist` upward** so a meaningful fraction of the
   population clears 0.7. Keeps the threshold's stated intent (only genuinely
   ambitious citizens run) but changes the population's ambition profile —
   and `ambition_score` is drawn inside `generate_population`, so this shifts
   the RNG stream and breaks byte-identity with every existing seeded journal.
2. **Lower `ambition_threshold`** to match the shipped `beta(2,8)`. Cheapest
   (no RNG-order change, no journal invalidation), but it needs a defensible
   target: what fraction of a population *should* be willing to run? Picking
   0.0 by default would enshrine the workaround rather than resolve it.
3. **Both**, if the honest answer is that neither value was ever calibrated
   against the other.

A fourth reading deserves testing before any of the three: perhaps
`decide_candidacy` was never intended to be the sole path at the shipped
configuration, and `rupture_path_enabled: false` is the real accident. The
design doc's own §2.4 treats rupture as a rare path, not a substitute, so this
is the least likely reading — but it is the only one that would leave both
shipped values untouched, and it has not been checked.

Whichever is chosen, the fix should state a target eligible-candidate rate
explicitly and measure against it, the same discipline
`plan-distribution-positions-seeds.md` §2 used for the distribution question:
criterion written before the sweep, not after.

## Consequences of deferring

- The shipped configuration remains unable to hold an election, and the
  failure is silent — see "What the next pass must do FIRST" above, which is
  the single highest-priority item on this ADR and is deliberately ordered
  ahead of the calibration question.
- `THEORY.md` §10.10 carries a reader-facing bullet so the limitation is
  visible where readers look for limitations, and `polity_config.yaml` carries
  the warning at the value itself. Both point here.
- The acceptance scripts are left untouched. Their `ambition_threshold=0.0`
  override is correct given the shipped values; what was wrong was the comment
  presenting it as a convenience, which is corrected at the config site rather
  than in five scripts.
