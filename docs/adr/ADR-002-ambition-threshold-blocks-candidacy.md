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

## The visibility half — DONE 2026-08-29, ahead of the calibration question

**Priority 1 was to stop the failure from being silent, and that half has now
landed.** Running `run_simulation` at the shipped defaults produced zero
candidates and zero elections while completing "successfully" — a worse defect
than a mis-calibrated value, for a specific reason: a bad value is at least
detectable by looking at the results, whereas a mechanism that silently
degrades to nothing hands an observer a clean-looking run with no indication
anything is missing. Every acceptance script happens to override the value, so
this never bit a published run — but it is exactly the shape of defect that
costs hours the first time someone runs at defaults and trusts the output.

**Correction to this ADR's own first statement of the problem.** It originally
read "no error, no warning, **no journal signal**". The third term was wrong,
and measuring rather than re-reading the code is what caught it: a default
8-year run emits exactly seven events — three `election_no_winner`, two
`legislative_result`, two `coalition_formed` — so there *was* a journal signal.
The real defect was narrower and more interesting: `election_no_winner`'s
payload was `{"office": "president"}` and nothing else, so it covered two
structurally different failures with the same bytes — *"candidates ran and
Blank won the runoff"* (the §10.10 seed/distribution failure mode) and *"no
candidate existed at all"*. **No journal this project has ever produced could
tell them apart.**

What shipped, therefore:

1. **A run-start warning** (`_warn_if_no_candidate_is_possible`) when no
   citizen can ever declare a candidacy. Exact rather than distributional:
   `ambition_score` is drawn once in `generate_population` and never mutated
   anywhere in the package, so an empty eligible pool at generation stays empty
   for the whole run. Both alternative candidacy paths are checked rather than
   assumed, so it never cries wolf — `llm.enabled` routes to
   `_declare_nominees_llm`, which never consults `ambition_threshold` at all,
   and `rupture_path_enabled` opens a second, threshold-independent route.
2. **A `reason: "no_candidates"` key on `election_no_winner`**, conditional on
   the nominee field being empty. Conditional deliberately: the emptiness *is*
   the new information, so the key appears exactly where it says something, and
   a config that fields no nominee keeps the byte-for-byte no-op property
   `election_invalidated`'s own comment exists to protect. Journals predating
   the key stay ambiguous — accepted, since they are already documented as
   non-representative (`uniform`/seed=42).

**A `PolityConfigError` was considered and rejected, and the reason matters
more than the choice.** Raising would declare the shipped configuration
invalid — which is precisely the calibration decision this ADR defers. A guard
that forces that decision is not "the guard before the calibration", it *is*
the calibration. Naming the defect out loud is not the same act as ruling on
it, and only the first was in scope.

## The test suite depends on this defect — which raises the price of the fix

Found while designing the guard, and recorded here because whoever opens the
calibration question needs it up front: **at least four places in
`test_polity_run_simulation.py` rely on the shipped threshold producing no
nominee**, with the reasoning written into their own comments. Two lower it to
`0.0` explicitly, noting that `0.7` "never actually produces a presidential
winner at seed=42". One asserts the presidency stays vacant for a whole run on
that basis. And one is load-bearing in a stronger sense —
`test_blank_vote_competitive_enabled_but_never_triggered_matches_the_default_journal_byte_for_byte`
derives its entire proof from it: *"no citizen ever crosses ambition_threshold
(0.7), so nominees is always [] and the invalidation check inside `if nominees:`
never even runs — turning the gate on is a true no-op here, not merely 'happens
not to trigger this seed'."*

So the codebase has been aware of the behaviour for several paliers and used it
as a convenience, without ever identifying it as a breakage. The consequence is
concrete: **fixing the calibration will invalidate at least one byte-identity
proof and will require rebuilding it on a different mechanism for keeping the
nominee field empty.** That cost belongs in the calibration decision, not
discovered halfway through it.

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

- The shipped configuration remains unable to hold an election — but it no
  longer fails quietly: a run-start warning names it, and `election_no_winner`
  now distinguishes an empty candidate field from a Blank-won runoff (see "The
  visibility half" above, shipped 2026-08-29). The calibration itself is
  untouched and still open.
- `THEORY.md` §10.10 carries a reader-facing bullet so the limitation is
  visible where readers look for limitations, and `polity_config.yaml` carries
  the warning at the value itself. Both point here.
- The acceptance scripts are left untouched. Their `ambition_threshold=0.0`
  override is correct given the shipped values; what was wrong was the comment
  presenting it as a convenience, which is corrected at the config site rather
  than in five scripts.
