# v3 readiness checklist — what to verify *before* `population_size: 100 → 1000`

**Status**: open gate, nothing here has been run
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
| `candidacy.rupture_signature_ratio` (0.005) | `sympathizer_ratio`, which counts the citizen themself | `1/n` | **YES — flips between 200 and 1000** |
| `candidacy.independent_signature_ratio` (0.01) | nothing — **parsed, validated, read by no domain code** | `1/n` | **YES in theory, moot in fact** (ADR-003) |
| `institutions.electoral_threshold` (0.05) | `votes / total_votes` (`ballot_and_aggregation.py:117`) | `1/total_votes` | no — floor is far below 0.05 at both scales |
| `institutions.blank_invalidation_threshold` (0.5) | `blank_share`, a share of cast ballots | `1/len(ballots)` | no |
| `petition.signature_threshold` (0.25) | share of the population signing | `1/n` | no — 0.01 ≪ 0.25 already at n=100 |
| `parties.coalition_majority_ratio` (0.5) | seat share, keyed to `assembly_seats` (100) | independent of `population_size` | no |
| the other 21 | decay rates, amplitudes, probabilities, per-tick deltas — never a population-derived share | — | no |

### A1. `rupture_signature_ratio` — the confirmed flip

- **Today (n=100)**: `sympathizer_ratio` floors at `1/100 = 0.01 ≥ 0.005`, so
  the bar rejects **nobody**. Measured over 40 seeds at shipped duration:
  477 495 draws, 476 coin-flip passes, **476 signature passes, zero
  rejections**. The rupture path is a pure per-tick coin flip.
- **At n=1000**: the floor drops to `0.001 < 0.005`. The bar becomes live — a
  citizen needs **at least 5 sympathisers** to declare.
- **To run**: re-execute the ADR-003 probe at both scales with
  `rupture_path_enabled: true` and publish the **rejection rate** of the
  signature bar. Expected: 0% at n=100, strictly positive at n=1000.
- **What would be a surprise**: a rejection rate still at 0% at n=1000 (means
  `sympathizer_ratio` is saturating and the bar is inert for a *different*
  reason — worth knowing), or a rate so high that the rupture path effectively
  closes.
- **Decide before running, not after**: whether the intended design is a bar
  that binds at scale or one that never binds. ADR-003 lists three candidate
  repairs (exclude self from the count; express the bar in absolute
  signatures; wire or delete `independent_signature_ratio`) and deliberately
  picks none. **Pick one before v3, not during.**

### A2. `independent_signature_ratio` — fix before, not during

It is validated at parse time and read nowhere. Deleting it or wiring it is a
decision that belongs *before* the scale change, so v3 does not silently
acquire a second live ballot-access bar at the same moment as A1.

---

## Class B — per-citizen rates whose expected counts scale linearly with `n`

- **`candidacy.rupture_base_probability` (0.001 per citizen per tick).**
  Expected declarations scale with `n × ticks`. Measured at n=100: ~476
  declarations across 40 runs of 121 ticks (~11.9 per run). At n=1000, expect
  **~10× that per run**, interacting with A1 in the opposite direction (more
  attempts, each now filterable).
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

1. Settle A2 (wire or delete the unread parameter) — cheapest, and it removes
   a confound from every measurement below.
2. Decide A1's intended design, then measure it at both scales.
3. Measure B and C at both scales; they interact (B feeds C's cap).
4. Re-examine D's mechanism, not its value.
5. Only then run the v3 robustness comparison §13 actually asks for.

Running step 5 first is the failure mode this file exists to prevent: a v3
result set that differs from v2 for four documented reasons nobody separated.
