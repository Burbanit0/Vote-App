---
name: project_polity_v6b_lot3_chamber_deliberation
description: "Polity v6b Lot 3 — chamber_deliberation (dt=11, §6bis.3) LLM decision shipped (PR #153); reliability spike found + fixed 2 real bugs; Lot 4 (acceptance) next, not yet authorized"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T23:53:31.118Z
---

v6b Lot 3 (`chamber_deliberation`, dt=11, §6bis.3) is merged to develop (PR #153, squash). Gives
each currently-seated sortition-chamber member (drawn by [[project_polity_v6b_lot2_sortition_chamber]]'s
`select_sortition_chamber`) an LLM-driven deliberation, fully insulated from every §7bis pressure
channel — no mandate deviation exposure, no street pressure, no petitions, no legitimacy floor.
Produces `chamber_deviation`, directly comparable to the elected president's own `mandate_deviation`,
for Lot 4's elected-vs-sortition acceptance comparison (the whole point of v6b's control-group design).

**Why:** v6b Lot 2 shipped selection/rotation but nothing moved a seated member's own position —
this lot is the last piece before Lot 4 has anything to compare.

**Design decisions:**
- Dispatched directly from the tick loop, never nested inside `_run_accountability_phase` — that
  function's own early-return guard (`if not (mandate.enabled or legitimacy.enabled or
  awakening.enabled): return {}`) has no `sortition_chamber.enabled` disjunct, and the chamber is
  architecturally independent of the presidency's accountability loop.
- No one-tick lag (unlike dt=6's `street_pressure` lag) — §6bis.3 requires full insulation from all
  §7bis pressure channels, so there's no same-tick external mutation to protect against.
- `ChamberContext` is deliberately minimal: one field, `ticks_left`.
- Config gap found and fixed: v6b Lot 1 omitted a deliberation-shift bound (unlike every other
  position-shift decision type) — added `SortitionChamberConfig.max_deliberation_delta`/
  `max_deliberation_shifts` at the same magnitude as `mandate.max_response_delta`/`max_response_shifts`
  (0.3/3) so Lot 4's comparison isolates the effect of pressure-insulation, not a different drift
  ceiling.
- Deterministic fallback = absence of the call: `chamber_position` pinned to `issue_positions` at
  seating time, nothing else ever touches it under `llm.enabled=False` — mirrors dt=6's own precedent.
  `chamber_position` resets to `issue_positions` at every new seating (inside `_run_sortition_rotation`'s
  seat loop), so a redrawn member (Lot 2's relaxed-pool fallback) never inherits stale drift.
- No `CODEBOOK_VERSION` bump — `DecisionType.CHAMBER_DELIBERATION=11`/`ChamberMotif` (701/702) were
  already reserved and bumped by v6b Lot 1.

**Two real reliability bugs found by the pre-flight spike and fixed in code (not assumed):**
1. Shifts↔motif coherence rule failed at a high rate against the real model (9/10 rejected at size
   10, 6/6 at size 30) — resolved by removing the validator entirely, mirroring `PressureDecision`'s
   own already-shipped precedent (v6a Lot 3) for dropping an over-constraining cross-field rule.
2. One call of 30 (and even a `chunk_voters`-shaped chunk of 15) silently drops all but the last 6
   decisions — root cause: `ChamberContext`'s prompt sends two full 20-dim float arrays per member
   (`sincere_position`, `chamber_position`), unlike dt=10's scalar-only ctx. Resolved via a new
   dedicated constant `_CHAMBER_MAX_CHUNK_SIZE = 10` (distinct from `MIN_SAFE_BATCH_SIZE=20`),
   chunked via `chunk_voters(members, _CHAMBER_MAX_CHUNK_SIZE, min_batch_size=1)` — confirmed
   reliable (3/3 chunks) on the real 30-member cohort.

**How to apply:** Both fixes are the deciding evidence for their own design choices — read
`llm_schemas.py`'s `ChamberDecision` docstring and `fast_api_voter/scripts/lot3_chamber_reliability_results.md`
before touching this decision type. Full offline suite: 1498 tests pass. Live smoke test confirmed
end-to-end (108 `chamber_deliberation` events across ticks 0-4, both motifs present, rotations seat
exactly 12/12). v6b Lot 4 (acceptance — elected-vs-sortition `mandate_deviation`-vs-`chamber_deviation`
trajectory comparison, closes out the whole v6b palier) is next, **not yet authorized**.
