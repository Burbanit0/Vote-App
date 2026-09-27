# ADR-003: §2.3's ballot-access filter is inert on both candidacy paths — and its inertness is population-size-dependent

**Status**: Fully resolved 2026-08-29. Option 1 (the rupture-path signature
bar) fixed same-day. Option 3 (`independent_signature_ratio`) resolved by
deletion, closing `docs/adr/v3-readiness-checklist.md`'s Class A2 item — see
"Decision on option 3" below. (Was: Open, defect measured and fix
deliberately deferred, earlier the same day.)
**Date**: 2026-08-29
**Context**: found while discharging Phase 1 of `plan-calibration-ambition.md`
(the ADR-002 calibration chantier), not while looking for it

> **Where the supporting evidence lives**: an instrumented deterministic probe
> (seconds, no LLM), run from a scratchpad script per this project's own
> convention for such probes — it is not committed. Its protocol and its
> counts are written into `plan-calibration-ambition.md` §1.1, which is the
> authority for the numbers quoted below.

## Context

Design doc §2.3 is explicit that the candidate pool is bounded **by rules, not
by an arbitrary cap** — `max_candidates_hard_cap` is described there as a
"garde-fou de dernier recours". Two rules are named as doing the real work:
party nomination, and a **ballot-access threshold** ("seuil de candidature
indépendante… parrainages simulés"). §2.4 then resolves contradiction C1 by
insisting the rupture path is **not exempt** from that filter — it merely gets
a *reduced* bar (`rupture_signature_ratio: 0.005` against `0.01` for an
ordinary independent), "pas d'une exemption totale. Sans ça, le mécanisme de
bornage du §2.3 était purement et simplement annulé."

**Neither bar is doing anything.**

### 1. The rupture bar cannot reject anyone at the shipped population size

`attempt_rupture_candidacy` (`simple_rules.py`) gates on
`sympathizer_ratio(citizen, population) >= config.rupture_signature_ratio`.
`sympathizer_ratio` iterates over the whole population **including the citizen
themself**, and `weighted_distance(c, c.issue_positions)` is `0`, which is
`<= c.blank_threshold` for any citizen (`blank_threshold_dist: beta(3,5)` is
strictly positive). So the ratio is bounded below by `1 / population_size`.

At the shipped `population_size: 100` that floor is `0.01`, always
`>= 0.005`. **The bar is unreachable from below.** Measured across the same 40
seeds used for ADR-002's own probe, over full shipped-duration runs with
`rupture_path_enabled: true`:

| draws | passed the `rupture_base_probability` coin flip | passed the signature bar | rejected by the bar |
|---|---|---|---|
| 477 495 | 476 | 476 | **0** |

The rupture path, at the shipped configuration, is a **pure per-tick coin
flip**. C1's stated resolution ships as a no-op.

### 2. The independent bar is parsed but never read

`candidacy.independent_signature_ratio: 0.01` is declared in the config
dataclass and validated by `_parse_candidacy` (`config.py`), and appears in one
test fixture. **No domain code reads it** — not `simple_rules.py`, not
`run_polity_simulation.py`, not `llm_behavior_engine.py`. There is no
independent-candidacy path for it to gate: every candidacy is either a party
nomination or a rupture declaration.

### 3. The inertness is not stable — it flips with population size

`1 / population_size >= rupture_signature_ratio` holds exactly while
`population_size <= 200`. At the §11.1 v3 target of `population_size: 1000`
the floor drops to `0.001`, below the `0.005` bar, and the filter **silently
becomes live**: a citizen would then need at least five sympathizers to
declare. This is the part that makes the finding worth its own entry rather
than a footnote — it is not a dormant parameter, it is a **regime change
waiting on a scale increase that is already on the roadmap**, and nothing in
the codebase would announce it.

## Decision (2026-08-29, partially superseding the deferral recorded below)

**Option 1 implemented: `attempt_rupture_candidacy` now gates on a new
`ballot_access_signature_ratio`, which excludes the citizen from their own
count.** `sympathizer_ratio` itself is untouched — see "Why a new function,
not a change to `sympathizer_ratio`" below. Options 2 and 3 remain open;
option 2 is now redundant with option 1 (both remove the `1/n` floor, no
reason to do both), option 3 is a separate, smaller decision not made here.

This became decidable once ADR-002 closed (2026-08-29, same day): the
deferral below explicitly named ADR-002 as the blocker ("both change who
reaches the ballot"), and it no longer applies — `ambition_threshold` is
settled at 0.30 and this fix touches a disjoint code path
(`attempt_rupture_candidacy`, not `decide_candidacy`).

**Why a new function, not a change to `sympathizer_ratio`.**
`sympathizer_ratio` has two call sites beyond this one — both in
`llm_behavior_engine.py`, both feeding the LLM a "perceived support" input
signal for the dominant candidacy path and party nomination. A citizen's own
trivial self-agreement (distance 0 to their own position) is a defensible
part of "how the population would receive you" for that use — this ADR was
never about it, and changing it would perturb the exact bytes sent to the
model in every LLM run, past and future, for a concern out of scope here.
`ballot_access_signature_ratio` is scoped to the one call site this ADR is
about.

**n=100 invariance, verified two ways, not assumed.**

1. **Structural.** `sympathizer_ratio` is untouched (diff-verifiable), and
   `rupture_path_enabled` ships `false` with no acceptance script setting it
   (grepped, confirmed) — so no published result can be affected by
   construction, at any population size.
2. **Empirical, and the result was a genuine surprise.** Re-running this
   ADR's own 40-seed protocol against the real pipeline, comparing the OLD
   formula (self counted, reconstructed for comparison) against the NEW one,
   at **both** `population_size=100` and `population_size=1000`, under
   **both** shipped position distributions:

   | `population_size` | `position_dist` | signature-bar evaluations | OLD rejects | NEW rejects |
   |---|---|---|---|---|
   | 100 | `factor_structure` | 472 | 0 | 0 |
   | 100 | `uniform` | 477 | 0 | 0 |
   | 1000 | `factor_structure` | 4 858 | 0 | 0 |
   | 1000 | `uniform` | 4 859 | 0 | 0 |

   **Not one rejection, in either formula, at either scale, under either
   distribution.** This is stronger than "n=100 is unaffected" — the fix
   changes *zero* observable behaviour in every regime measured, including
   n=1000. Confirmed directly (not just inferred from the zero count) with a
   hand-built isolated citizen — nobody within anybody's tolerance, n=101 —
   where the OLD formula still accepts (`1/101 ≈ 0.0099 ≥ 0.005`) and the NEW
   one correctly rejects (`0.0 < 0.005`): the mechanism the fix targets is
   real, it is just apparently never triggered by the population this project
   actually generates.

**This refines §3's own "silently becomes live" framing, and the correction
matters.** The floor crossing at `population_size > 200` (`1/n < 0.005`) is a
*necessary* condition for the old formula to ever reject anyone — it is not
*sufficient*. Whether it does depends on the population's tolerance structure
(`blank_threshold_dist: beta(3,5)`, mean 0.375, fairly generous), and under
every distribution this project ships, apparently nobody is ever isolated
enough to fall under even the un-fixed bar. The defect was real and worth
fixing on its own terms — the old formula made it *structurally impossible*
to ever reject a genuinely isolated citizen, at any population size, which is
wrong independent of whether the shipped distributions happen to produce one
— but the "silently becomes live" urgency should be read as a latent risk
under a *different* future `blank_threshold_dist` or a genuinely polarized
population, not as something already caught in the act at n=1000 under
today's distributions.

**Regression guard**: `test_attempt_rupture_candidacy_rejects_a_fully_isolated_citizen_at_the_shipped_signature_ratio`
(`test_polity_simple_rules.py`) — verified to fail against the old formula
before being kept, not merely written and trusted.

**Option 3, `independent_signature_ratio`, is untouched and still open.**
Wiring it or deleting it is a separate, smaller decision; nothing here forces
it either way.

## Decision on option 3 (2026-08-29, closing v3-readiness-checklist.md's Class A2)

Deleted, not wired. "Wire it" turned out not to be the small config change it
looked like: `party_affiliation` is typed `int | None`, but the only place
that ever assigns it (`run_polity_simulation.py`'s population setup,
`assign_party_affiliation`) always returns the *nearest* party's id — it
never returns `None`. No citizen in this simulation is ever actually
unaffiliated today. Wiring `independent_signature_ratio` would therefore mean
designing and implementing a whole new "independent citizen" category and its
own candidacy path from scratch, not connecting an existing one to an unread
threshold — a real feature addition, out of scope for both this cleanup item
and §13's own "v3 adds no new parameter" rule for the scale-up milestone this
checklist gates.

Removed from `CandidacyConfig` (`config.py`), `polity_config.yaml`, and the
one test fixture that carried it (`test_polity_simple_rules.py`). If an
independent-candidacy path is ever designed, it gets its own lot, its own
ADR, and a freshly-chosen threshold — resurrecting this specific unread value
would not save any real work.

## Consequences

- **The rupture-path signature bar is now structurally correct**: a
  genuinely isolated citizen can no longer clear it purely by counting
  themselves, at any population size. Empirically (see above) this changes
  no observed behaviour at `population_size` 100 or 1000 under either shipped
  `position_dist`, because the shipped `blank_threshold_dist` apparently
  never produces a citizen isolated enough to fail even the old, self-
  inclusive bar. The fix is a correctness fix for a latent defect, not a
  response to an observed one.
- §2.3's "bornage par les règles" still reduces to `max_candidates_hard_cap`
  alone in practice, since the (now-correct) bar has never been observed to
  reject anyone under any shipped configuration — a structural fix, not yet
  an empirically load-bearing one.
- `polity_config.yaml`'s `rupture_signature_ratio` comment is updated to
  point at the fixed function and this decision, replacing the "no rejections
  possible" warning it previously carried.
- Nothing was blocked by the fix: `rupture_path_enabled` still ships `false`,
  so no shipped configuration and no published acceptance run was ever
  exercising either bar, before or after.
- **`docs/adr/v3-readiness-checklist.md`'s Class A1 and A2 items are both
  resolved.** A1 (`rupture_signature_ratio`): its `1/n` floor is gone at every
  population size, not just raised past a higher `n`. A2
  (`independent_signature_ratio`, option 3 above): deleted, not wired — see
  "Decision on option 3". The checklist's general rule (any population-ratio
  threshold with a `k/n` floor changes regime with `n`) stays as documentation
  for future parameters, not specific to either of these anymore.

## Consequences of deferring (superseded for option 1 — kept for the record)

- Any run that enables `rupture_path_enabled` at `population_size <= 200` must
  be read as a **flat per-tick lottery over the whole electorate**, with no
  support requirement whatsoever. `plan-calibration-ambition.md` §1.1's Phase-1
  measurement is the first run of that kind this project has published, and it
  is annotated accordingly.
- §2.3's "bornage par les règles" currently reduces to `max_candidates_hard_cap`
  alone — precisely the arbitrary numeric cap §2.3 exists to avoid.
- The shipped `polity_config.yaml` comment "RÉSOLUTION C1 : seuil réduit, pas
  d'exemption totale" overstates what ships; a pointer to this ADR now sits at
  the value itself, the same treatment ADR-002 got.
- Nothing is blocked: `rupture_path_enabled` ships `false`, so no shipped
  configuration and no published acceptance run exercises either bar.
- **The scale flip is registered as a runnable gate, not only as a finding
  here**: `docs/adr/v3-readiness-checklist.md` carries it, together with the
  generalised rule it is an instance of — *any* threshold expressed as a ratio
  of the population changes regime with `n` when the measured quantity floors
  at `k/n`. That file audits all 27 ratio-valued parameters against the rule
  (exactly two are affected, one of which is this ADR's unread
  `independent_signature_ratio`) and adds three further scale-sensitivity
  classes: per-citizen rates whose counts scale linearly, absolute counts
  calibrated at n=100, and calibrations whose *derivation* assumed the scale.
  The point is that §13 specifies v3 as "aucun nouveau paramètre, uniquement un
  test de robustesse" — true, and still leaving existing parameters changing
  behaviour underneath it. Documenting the flip only in this ADR would have
  left it to be rediscovered from the results.
