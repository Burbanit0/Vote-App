# v3 readiness checklist — what to verify *before* `population_size: 100 → 1000`

**Status**: open gate — Class A1 and A2 resolved 2026-08-29, everything else unrun
**Owner of the trigger**: whoever starts §13's v3 milestone
**Date opened**: 2026-08-29 (out of `ADR-003-ballot-access-filter-is-inert.md`)

> **Why this sits in `docs/adr/` rather than `docs/`**: `.gitignore` excludes
> `/docs/*` and re-includes only `/docs/adr/` and `/docs/journal/`, for the
> reason stated there — a document that exists on one machine cannot do its
> job. A checklist nobody can read is the same failure as an ADR nobody can
> read, so it lives with them. `BACKLOG-alternatives.md` is the existing
> precedent for a non-ADR process document in this directory.

## Why this file exists

`polity-simulation-design-v2.md` §13 specifies v3 as *"passage à 1 000
citoyens : aucun nouveau paramètre, uniquement un test de robustesse au
changement d'échelle."* That is true, and it is not sufficient. **"No new
parameter" does not mean "no parameter changes behaviour."**

The generalisable rule, found while measuring ADR-003:

> **Any threshold expressed as a ratio of the population changes regime with
> `n` whenever the measured quantity has a reachable floor of `k/n`.** A bar
> the population can never fall below is inert; the same bar becomes live the
> moment `k/n` drops under it. Nothing in the codebase announces the crossing —
> the config value does not change, so a diff shows nothing.

Three further classes below it (per-citizen rates, absolute counts, and
calibrations whose *derivation* assumed the scale) have the same property:
invisible in a diff, visible only in results.

This is a **gate to run**, not background reading. Each item names what to
measure and what would count as a surprise.

---

## Class A — ratio thresholds whose measured quantity floors at `k/n`

All 27 ratio-valued parameters (`_get_ratio` in `config.py`) were audited
against this rule. **Exactly two are affected, and one of them is dead code.**

| Parameter | Compared against | Floor | Affected? |
|---|---|---|---|
| `candidacy.rupture_signature_ratio` (0.005) | `ballot_access_signature_ratio` (was `sympathizer_ratio`) | ~~`1/n`~~ **fixed 2026-08-29** | **RESOLVED — see A1** |
| ~~`candidacy.independent_signature_ratio` (0.01)~~ **deleted 2026-08-29** | nothing — **parsed, validated, read by no domain code** | `1/n` | **RESOLVED — see A2 (deletion, not a fix)** |
| `institutions.electoral_threshold` (0.05) | `votes / total_votes` (`ballot_and_aggregation.py:117`) | `1/total_votes` | no — floor is far below 0.05 at both scales |
| `institutions.blank_invalidation_threshold` (0.5) | `blank_share`, a share of cast ballots | `1/len(ballots)` | no |
| `petition.signature_threshold` (0.25) | share of the population signing | `1/n` | no — 0.01 ≪ 0.25 already at n=100 |
| `parties.coalition_majority_ratio` (0.5) | seat share, keyed to `assembly_seats` (100) | independent of `population_size` | no |
| the other 21 | decay rates, amplitudes, probabilities, per-tick deltas — never a population-derived share | — | no |

### A1. `rupture_signature_ratio` — RESOLVED 2026-08-29, kept here for the record

**Was**: `sympathizer_ratio` floored at `1/n` (every citizen counts
themself), which made the bar structurally unreachable at
`population_size <= 200` and would have flipped it live above 200 —
477 495 draws at n=100, 476 coin-flip passes, **476 signature passes, zero
rejections**, the rupture path a pure per-tick coin flip.

**Fix (ADR-003, option 1)**: `attempt_rupture_candidacy` now gates on a new
`ballot_access_signature_ratio`, which excludes the citizen from their own
count. `sympathizer_ratio` itself is untouched — it has two other call sites
feeding the LLM's "perceived support" signal, out of scope of this fix.

**Re-run at both scales, not assumed**: the predicted "strictly positive
rejection rate at n=1000" **did not happen**. Same 40-seed protocol, both
shipped `position_dist` values, both formulas, both scales:

| `population_size` | `position_dist` | evaluations | OLD rejects | NEW rejects |
|---|---|---|---|---|
| 100 | `factor_structure` | 472 | 0 | 0 |
| 100 | `uniform` | 477 | 0 | 0 |
| 1000 | `factor_structure` | 4 858 | 0 | 0 |
| 1000 | `uniform` | 4 859 | 0 | 0 |

**Zero rejections in every cell, both before and after the fix.** The floor
crossing at n>200 is necessary for a rejection to be *possible*, not
sufficient for one to actually happen — under this project's
`blank_threshold_dist: beta(3,5)` (mean 0.375), nobody the generator produces
is ever isolated enough to fail even the old, self-inclusive bar, at either
scale. Confirmed the mechanism is nonetheless real with a hand-built isolated
citizen (n=101, nobody within anybody's tolerance): OLD accepts
(`1/101 ≈ 0.0099 ≥ 0.005`), NEW correctly rejects (`0.0 < 0.005`).

**Lesson for the next Class-A item found**: "the floor crosses the threshold
mathematically" is not the same claim as "the bar will actually bind" — the
second one needs the same re-measurement this one got, against the real
population generator, not inferred from the arithmetic alone.

Full writeup: `docs/adr/ADR-003-ballot-access-filter-is-inert.md`.

### A2. `independent_signature_ratio` — RESOLVED 2026-08-29, deleted not wired

It was validated at parse time and read nowhere. "Wire it" turned out not to
be the small change it looked like: `party_affiliation` is typed
`int | None`, but the only assignment site (`assign_party_affiliation`)
always returns the nearest party's id — no citizen is ever actually
unaffiliated in this simulation today. Wiring the threshold would mean
designing a whole new independent-citizen category and candidacy path from
scratch, a real feature addition out of scope for both this cleanup item and
§13's "v3 adds no new parameter" rule. Deleted from `CandidacyConfig`,
`polity_config.yaml`, and its one test fixture. Full reasoning:
`docs/adr/ADR-003-ballot-access-filter-is-inert.md`'s "Decision on option 3".

---

## Class B — per-citizen rates whose expected counts scale linearly with `n`

- **`candidacy.rupture_base_probability` (0.001 per citizen per tick).**
  Expected declarations scale with `n × ticks`. Measured at n=100: ~476
  declarations across 40 runs of 121 ticks (~11.9 per run); at n=1000, ~4 860
  (~10×, as expected — confirmed directly while re-measuring A1, not just
  extrapolated). A1's fix does **not** cut into this at n=1000 the way it was
  expected to: zero of those ~4 860 were rejected by the (now-correct)
  signature bar, so the 10× growth in declarations is not damped by A1 at
  all under the shipped `blank_threshold_dist`.
- **To run**: report expected and observed declaration counts at both scales
  *before* interpreting any v3 electoral result.

## Class C — absolute counts calibrated at n=100

These are integers, not ratios, so they do not scale at all — which is exactly
the problem.

- **`candidacy.max_candidates_hard_cap` (20).** Never binding at n=100. With
  Class B's 10× more rupture declarations it may start binding, silently
  converting §2.3's "bornage par les règles" into the arbitrary numeric cap
  §2.3 exists to avoid. **Check whether it ever binds.**
- **`sortition_chamber.seats` (30).** 30% of the population at n=100, **3% at
  n=1000** — a different institution, not a scaled one. `sortition_chamber.py`
  documents its pool-exhaustion and relaxed-eligibility behaviour explicitly
  "at the shipped defaults (`population_size=100`, `seats=30`)"; that analysis
  does not transfer. **Re-measure pool exhaustion before trusting any v3
  sortition arm.**

## Class D — calibrations whose *derivation* assumed n=100

- **`candidacy.ambition_threshold` (0.30, ADR-002).** The value is not
  arbitrary: its floor was derived from "§2.3 needs ≥ 2 eligible contenders
  per party on average", computed at **5 parties × ~20 members**. At n=1000
  with `parties.initial_count` still 5, each party has ~200 members and 20%
  eligible gives **~40 contenders per party**. The pre-registered criterion
  still passes trivially — but the party nomination it was protecting becomes
  a **40-way** arbitration instead of a 4-way one, and §3.6.3 routes that
  decision to the LLM. **The threshold does not need re-deriving; the
  mechanism it protects does need re-examining**, together with whether
  `parties.initial_count` should scale with population at all.
- **To run**: report contenders-per-party at n=1000 alongside the eligible
  rate. The criterion in `plan-calibration-ambition.md` §2.2 is written in
  election units and transfers as-is; its *justification* was scale-bound.

---

## Order of operations

1. ~~Decide A1's intended design, then measure it at both scales.~~ **Done
   2026-08-29** — see A1 above.
2. ~~Settle A2 (wire or delete the unread parameter).~~ **Done 2026-08-29** —
   deleted, see A2 above.
3. Measure B and C at both scales; they interact (B feeds C's cap). B is
   partly done (A1's re-measurement confirmed the ~10× growth directly), C is
   not.
4. Re-examine D's mechanism, not its value.
5. Only then run the v3 robustness comparison §13 actually asks for.

Running step 5 first is the failure mode this file exists to prevent: a v3
result set that differs from v2 for reasons nobody separated.
