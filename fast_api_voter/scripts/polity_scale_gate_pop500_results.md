# v3 scale gate at population 500 — measured, not estimated

Phase 5 of `plan-flagship-30y-run.md`. Every number below comes from a
**deterministic** 30-year run at the stated scale (seconds each, no GPU), so
differences between the columns are the population, not a code change.

## Sortition pool exhaustion

| Scale | Seats | Rotations | First relaxed rotation | Seats filled, strict | Seats filled, relaxed |
|---|---|---|---|---|---|
| pop 100 | 30 | 31 | #4 | 30 | 30 |
| pop 500 | 75 | 31 | #7 | 75 | 75 |

## `max_candidates_hard_cap` — inert, at any population

`candidacy.max_candidates_hard_cap` is parsed by `config.py` and read by
**nothing**. Every other field in the `candidacy` section reaches the engine
(`ambition_threshold`, `rupture_path_enabled`, `rupture_base_probability`,
`rupture_distance_multiplier`, `rupture_signature_ratio`); this one does not.
So it cannot bind at n=500, or at n=1000, or at any population — not because the
fields stay small, but because no code path consults it. Same shape as ADR-003's
own inert-filter finding.

The observed field sizes are reported anyway, since they are what a real cap
would have to bound:

| Scale | Ticks with declarations | Candidates declared per such tick | Nominal cap |
|---|---|---|---|
| pop 100 | 24 | 1–5 | 20 (inert) |
| pop 500 | 66 | 1–7 | 20 (inert) |

## Party nomination arity — what `party_nomination_choice` arbitrates over

Pure computation from (config, population, seed): no simulation, no LLM.

| Scale | Eligible citizens | Eligible share | Contenders per party | Nominees per party, over 8 elections |
|---|---|---|---|---|
| pop 100 | 24 | 24.0% | 4–7 | 8 |
| pop 500 | 98 | 19.6% | 15–26 | 8 |

## Class B — declaration paths

| Scale | Dominant declarations | Rupture declarations |
|---|---|
| pop 100 | 40 | 17 |
| pop 500 | 40 | 82 |

## What this settles, and what it does not

**The 75-seat decision is safe, and better than the shipped pair.** Strict
one-shot-ever eligibility survives to rotation #7 at (500, 75) versus #4 at the
shipped (100, 30) — a longer strict phase, not a shorter one, because 75 seats is
15% of the population where 30 is 30%. Every rotation fills every seat at both
scales, before and after relaxation. `sortition_chamber.py`'s own pool-exhaustion
finding is scoped to (100, 30) and explicitly does not transfer; re-measured here,
it transfers in the favourable direction.

**Nomination arity changes materially, exactly as predicted.**
`party_nomination_choice` arbitrates over 4–7 contenders per party at pop 100 and
15–26 at pop 500 — a ~20-way arbitration where the shipped calibration was derived
for a ~5-way one. ADR-002's own derivation criterion (>= 2 eligible per party) is
comfortably met at both scales, so `ambition_threshold: 0.30` does not need
re-deriving. What is NOT settled here is whether the model *decides well* across 20
options — a decision-quality question no deterministic run can answer, and one this
project already has open evidence about on other decision types.

**`max_candidates_hard_cap` is dead config.** The plan expected a counting
question and it turned out to be a structural one: nothing in the engine reads the
field, so the §2.3 rule-based bounding it was supposed to backstop has no numeric
cap behind it at any scale. Not a problem for the flagship — the observed fields are
nowhere near 20 — but it should be either wired up or removed rather than left
looking like a live guard-rail. Not done here; it is its own scoping decision, the
same disposition ADR-003 gave the inert ballot-access filter.

**Class B: rupture declarations scale linearly, as predicted** — 17 at pop 100,
82 at pop 500, a 4.8x increase against a 5x population increase. Nothing anomalous.

**A correction this measurement forced.** The first version of these runs reported
zero rupture declarations and a flat 5-candidate field at both scales. That was not
a finding, it was a config bug in the flagship runner: `candidacy.rupture_path_enabled`
is shipped `false` and "full richness" had not turned it on. Same for
`institutions.blank_vote_competitive`. Both are now set in `_flagship_config`, and
the numbers above are from runs with them on.

