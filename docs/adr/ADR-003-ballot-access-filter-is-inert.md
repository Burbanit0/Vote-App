# ADR-003: §2.3's ballot-access filter is inert on both candidacy paths — and its inertness is population-size-dependent

**Status**: Open — defect measured, fix deliberately deferred
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

## Decision

**None today. The defect is named, measured, and deferred.**

Deferred for the same reason ADR-002 defers its own question, and with the same
discipline: the repair is a modelling judgment, not a bug fix, and there are at
least three distinguishable ones —

1. **Exclude the citizen from their own sympathizer count.** Cheapest, and
   arguably the correct reading: a "parrainage" one gives oneself is not a
   signature. Makes the bar reachable at every population size, and removes the
   `1/n` floor that causes the scale dependence.
2. **Express the bar in absolute signatures rather than a ratio**, which is how
   real ballot-access rules are written and would make the parameter
   scale-invariant by construction.
3. **Wire `independent_signature_ratio` to something**, or delete it. Keeping a
   validated-but-unread institutional parameter in `candidacy:` is the same
   class of defect ADR-002 documents: a config site that reads as load-bearing
   and is not.

Choosing between these interacts with the calibration decision currently open
in ADR-002 — both change who reaches the ballot — so they should be decided
together, not raced.

## Consequences of deferring

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
