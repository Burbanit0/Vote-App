# ADR-002: the shipped candidacy configuration cannot hold an election — calibrated, `ambition_threshold` 0.7 → 0.30

**Status**: Accepted — calibrated 2026-08-29. (Was: Open, problem measured and
deferred, 2026-08-29 earlier the same day.)
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

## Decision (2026-08-29, superseding the deferral recorded below)

**`candidacy.ambition_threshold: 0.7` → `0.30`. `citizens.ambition_dist`
(`beta(2,8)`) and `decide_candidacy`'s rule are both left untouched.**

This is option 2 of the three listed further down. The reasoning, and what was
rejected with it:

- **Why not 0.0** (the value every acceptance script forces): it would enshrine
  the workaround. At 0.0 every citizen is eligible, the threshold carries no
  information, and the whole weight of selection falls on
  `select_party_nominee`'s tie-break — the regime `THEORY.md` §10.10 measured
  as costing 70% Blank wins under `uniform`. The pre-registered criterion
  rejects it explicitly (eligible rate must stay ≤ 40%).
- **Why 0.30 specifically, derived before the sweep, not fitted to it**: §2.3
  gives the party an arbitration between *several* internal contenders (an LLM
  decision point, §3.6.3), so the mechanism needs ≥ 2 eligible per party on
  average — at 5 parties and 100 citizens that is a floor of 10% eligible. The
  ceiling is ~40%, past which the trait stops discriminating. 0.30 lands at
  **20.0% eligible, 4.0 contenders per party**. Measured against the real
  pipeline over 320 elections: **0 elections with an empty candidate field,
  100% with ≥ 4 of 5 parties fielding a nominee**, reproduced on an independent
  seed block (41..80: 20.4%, 0 empty, 100%).
- **The fourth reading was tested and rejected.** `rupture_path_enabled: true`
  alone leaves 26.9% of elections with no candidate at all, inverts §2.4's own
  proportions (476 rupture declarations against 8 dominant), leaves the party
  nomination inert on 312 of 320 elections — and is not even cheaper: it breaks
  the same seven tests. Full measurement in
  `plan-calibration-ambition.md` §1.1.
- **A fifth option was found, and is deferred on evidence rather than on
  cost.** Design doc §2.4 defines the dominant path as `ambition_score` **and**
  perceived social support crossing a *combined* threshold;
  `decide_candidacy` implements only the first half, while the LLM path
  (`llm_behavior_engine.decide_candidacies`) already feeds the model both
  signals and describes itself as the replacement for "`decide_candidacy`'s
  **bare** ambition_score threshold". Implementing §2.4 as written was measured
  to cost no more than option 2 (verified on final bit-generator state: neither
  option touches `generate_population`'s stream), but it **does not fix the
  problem on its own** — at the shipped 0.7 the combined rule still leaves
  304/320 elections empty, because a mean compresses rather than translates.
  And once recalibrated to pass the criterion, it moves the mean support of
  actual nominees by **+0.018 (~3%)** and nothing else, because
  `select_party_nominee` takes the argmax on `ambition_score` and washes the
  eligibility change out. **§2.4's substantive claim is blocked downstream by
  the nominee criterion, not by `decide_candidacy`** — so it is deferred to be
  taken up *together* with §10.10's nominee-selection question, where it would
  actually have an effect. Full measurement in `plan-calibration-ambition.md`
  §2.3–§2.4.

**Migration cost, as actually paid** (measured before implementing, per the
plan's §3, rather than discovered during): seven tests, not the four this ADR
originally named — including a **second** byte-identity proof it had not
identified. Both proofs were rebuilt on
`institutions.president_term_limit: 0`, which makes `is_term_limited` true for
every citizen before anyone has served anything, so the candidate field is
empty *by construction, at every tick, for every seed, independent of any RNG
draw* — an exact mechanism where the old one (the shipped threshold happening
to empty the pool) was only distributional. `test_events_enabled_but_
structurally_inert_...` additionally needed its off-arm corrected to carry the
same `awakening` config as its on-arm: it was comparing awakening as well as
events, and only passed because the permanently vacant presidency made
awakening inert on both sides.

**Deliberately NOT changed**: the acceptance scripts keep their
`ambition_threshold=0.0` override. It is now a **continuity** choice — keeping
`THEORY.md` §10.4–§10.9 comparable with each other — rather than a precondition
for an election to exist.

**Re-baseline question — checked, not deferred (2026-08-29,
`plan-calibration-ambition.md` §3bis).** `ambition_threshold` has exactly one
functional read site in the whole domain package
(`decide_candidacy`/`select_party_nominee`, the deterministic path only) —
the LLM path (`decide_candidacies`) never consults it, confirmed by tracing
the code before writing any sweep criterion. Every numeric claim in §10.4–
§10.9 is measured under `--engine llm`, so every one of them is structurally
invariant to this calibration, by construction. The only thing exposed to
`ambition_threshold` — each acceptance script's cheap `--engine deterministic`
pre-flight anchor — was measured byte-identical between `0.0` and `0.30`
across eight configurations spanning every acceptance script family
(v4/v5/v6a/v6b/cascade, both shipped `position_dist` values, with and
without `sortition_chamber`/`events`/`social_graph`). **Nothing needs
re-baselining.**

**Spun out**: `ADR-003-ballot-access-filter-is-inert.md`, for a defect found
while measuring this one (§2.3's ballot-access filter rejects nobody at
`population_size ≤ 200`, and silently becomes live above it).

## The original deferral (superseded, kept for the record)

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

## Consequences

- **The shipped configuration now holds elections**: 320/320 in the 40-seed
  block, 0 with an empty candidate field. A regression guard
  (`test_the_shipped_config_no_longer_warns`) fails if the shipped pair ever
  drifts back to a state where no citizen can run.
- The run-start warning and `election_no_winner`'s `reason: "no_candidates"`
  key (the visibility half, below) both remain — they are no longer describing
  the shipped default, but they are what makes any *future* empty-pool
  configuration loud instead of silent, which was always their point.
- **Every published result predating 2026-08-29 was measured at
  `ambition_threshold=0.0`** and remains so: nothing was re-baselined, and the
  acceptance scripts still pin 0.0. `THEORY.md` §10.4–§10.9 are therefore
  internally comparable but do not reflect the shipped value.

## Consequences of deferring (superseded — kept for the record)

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
