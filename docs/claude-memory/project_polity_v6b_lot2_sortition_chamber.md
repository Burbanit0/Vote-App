---
name: project-polity-v6b-lot2-sortition-chamber
description: "v6b Lot 2 done (PR #152) — sortition_chamber.py selection+rotation (§6bis.3), measured pool-exhaustion finding, election-collision ordering fix"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T21:03:32.052Z
---

Polity v6b Lot 2 (`sortition_chamber.py` — selection + whole-chamber rotation, §6bis.3) merged to
`develop` (PR #152). Second of four planned v6b lots
([[project_polity_v6b_lot1_sortition_config]] → this lot → `chamber_deliberation` LLM decision →
acceptance).

**The pool-exhaustion calibration finding, measured from a real run, not hand-derived**: at shipped
defaults (`population_size=100`, `seats=30`, `term_years=1`), strict one-shot-ever eligibility would
leave the chamber **completely empty from tick 16 onward** (105 of 120 ticks, 87.5% of a full run) —
confirmed by a real `calibrate_sortition.py` run before committing to the design, matching v4 Lot 4's
own calibration-gate discipline. Resolved with a two-tier `select_sortition_chamber`: strict pool
(never served, not the sitting president) while it can fill `seats`; once it can't, relaxes to "not
currently seated." The real run showed this is even cleaner than the hand math suggested — relaxation
engages *proactively* (first relaxed draw at tick 12) so the chamber is **never actually undersized**,
not just eventually recovered.

**A second real ordering finding, caught during planning before any code was written**:
`sortition_term_ticks=4` divides evenly into `president_term_ticks`/`assembly_term_ticks`/
`assembly_offset_ticks` at the shipped defaults — every presidential AND legislative election tick is
*also* a rotation tick, confirmed by direct calculation. This is the common case, not an edge case.
Resolved by dispatching sortition rotation **after** both election blocks in the tick loop (mirrors
why `_run_accountability_phase` itself already runs last) — so a newly-elected president is correctly
excluded from that same tick's sortition draw. Pinned by
`test_sortition_rotation_excludes_a_citizen_at_the_sitting_president`, which also checks event-id
ordering (rotation after election).

**A real signature-change bug caught during implementation, not left in the plan**: the plan's own
sketch had `InstitutionalClock.from_config` reading `institutions.sortition_chamber.term_years` —
but `sortition_chamber` is a **top-level** `PolityConfig` field, not nested under `InstitutionsConfig`
(confirmed by v6b Lot 1's own implementation). Fixed by adding `sortition_chamber` as a third
parameter to `from_config`, then fixing all four call sites — the two real ones
(`run_polity_simulation.py`, `test_polity_institutional_clock.py`'s own helper) plus four pre-existing
**direct** `InstitutionalClock(...)` constructions in that same test file, which would otherwise have
failed with a missing-required-argument error the moment `sortition_term_ticks` was added with no
default.

Two new `Citizen` fields (`sortition_seat_until_tick`, `sortition_terms_served`), appended last, never
RNG-drawn — same precedent every prior palier's own new-field lot has used. A fourth dedicated RNG
stream (`sortition_rng`, alongside `rupture_rng`/`events_rng`), drawn only on a rotation tick when
`sortition_chamber.enabled`.

**v6b is 2 of 4 planned lots done.** Next: Lot 3 (`chamber_deliberation`, dt=11 — the LLM decision,
the fourth 5-file increment built from scratch this session). Already flagged for that lot's own
planning pass: `chamber_deliberation`'s batch cohort is legitimately empty on most ticks (the chamber
only exists between rotation ticks), making the "empty cohort ⇒ no client call" guard the *common*
path rather than an edge case — deserves its own explicit test. Full plan in
`C:\Users\burba\.claude\plans\merry-hugging-hamming.md`. Not yet authorized past Lot 2.
