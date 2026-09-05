---
name: project-polity-v6b-lot1-sortition-config
description: "v6b Lot 1 done (PR #151) — config + codebook for the sortition chamber (§6bis.3), MVP scope agreed with user, veto power deferred"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T17:44:09.187Z
---

Polity v6b Lot 1 (config + codebook reservations for the sortition chamber, §6bis.3) merged to
`develop` (PR #151). First lot of v6b — the second half of v6's own top-level split
([[project_polity_v6_lot1_social_graph_config]]), started immediately after
[[project_polity_v6a_lot4_acceptance]] closed out v6a.

**§6bis.3 is the only 🔴-marked ("most open") section in the whole design doc**, and grep-confirmed
to be the least-specified feature ever planned in this project: only 4 total mentions in the ~1730-line
design doc, no `§3.6.x` subsection, no reserved `DecisionType` anywhere, and — the load-bearing
finding — **no "law"/bill/policy-proposal concept exists anywhere in this codebase** for the
chamber's own veto power (point ouvert n°11) to act on. This was surfaced to the user via
`AskUserQuestion` before any planning was written (a genuine case where the scope choice — full
lawmaking substrate vs. MVP control-group comparison — was the user's to make, not a judgment call
with enough textual grounding to resolve alone): **user chose "MVP first, defer veto"**. Veto power
is out of scope for all of v6b's own four lots, named explicitly as its own future palier requiring
a lawmaking concept nobody has designed yet.

**MVP scope, agreed and now partly implemented**: a genuine control-group cohort — uniform-random
selection, non-renewable short terms, structurally immune to every §7bis pressure channel — compared
against the elected president's own `mandate_deviation` trajectory, per §6bis.5's own "groupe de
contrôle élu vs tiré-au-sort" framing.

**Real correction caught during implementation, not assumed from the plan**: the plan proposed
`ChamberMotif` codes 501/502, but live-verifying `codebook.py` before writing anything (the
project's own standing "verify, don't assume" discipline) found **500-599 already belongs to
`CoalitionMotif`** (`IDEOLOGICAL_PROXIMITY=501`, `OFFICE_SEEKING=502`) — a real collision that
`motif_labels()`'s own collision-check would have caught at runtime. Corrected to a fresh **700-799
range** (`SINCERE_POSITION=701`, `DELIBERATIVE_SHIFT=702`) before implementing, with a dedicated
regression test (`test_chamber_motif_does_not_collide_with_coalition_motifs_500_range`) pinning it.

**`DecisionType.CHAMBER_DELIBERATION = 11`** — verified decision_type `3` is genuinely unallocated
(no docstring, no test, no reference) before choosing `11` rather than reusing `3` on a guess;
pinned by its own regression test so a future palier can't assume `3` was reserved for anything
without re-checking.

**Three TRANCHÉ parse-time rejections**, same register as `recall_floor_indexed_on_l0`/
`social_graph.evolving`: `selection: stratified_demographic` (not implemented);
`overlaps_with_assembly: true` (no individual deputy `Citizen` exists anywhere in this codebase —
`Office.DEPUTY` is reserved but never assigned — so `false` is already true by construction, `true`
asks for per-deputy tracking that doesn't exist); `renewable: true` (v6b's own selection design,
built in Lot 2, assumes strict one-shot-ever eligibility via a `sortition_terms_served` counter).

**New cross-field rule**: `sortition_chamber.enabled ⟹ population_size >= seats`.

**`CODEBOOK_VERSION` bumped `1.5`→`1.6`** — the first lot in this whole session that both reserves
new wire surface AND bumps the version in the same step (v4/v5/v6a Lot 1 all reserved first, bumped
later at consumption; v6b had no prior reservation lot to bump at).

**A real, already-flagged calibration risk for Lot 2**: at the shipped defaults
(`population_size=100`, `seats=30`, `term_years=1` ⇒ rotating every 4 ticks), strict one-shot-ever
eligibility exhausts the never-served pool after roughly 3.3 rotations (~13 ticks) — long before a
120-tick run ends. Lot 2 must measure the real exhaustion point and choose an explicit fallback
(shrink the chamber / relax to "not currently serving" / reject at config-load time) — not yet
resolved, this palier's own version of v4 Lot 4's calibration gate.

**v6b is 1 of 4 planned lots done**: config/codebook (this lot) → `sortition_chamber.py` (selection +
rotation, next) → `chamber_deliberation` (dt=11, the LLM decision) → acceptance (elected-vs-sortition
deviation-trajectory comparison). Full plan in `C:\Users\burba\.claude\plans\merry-hugging-hamming.md`.
Not yet authorized past Lot 1 — Lot 2 needs its own short planning pass, same discipline as every lot
in this project.
