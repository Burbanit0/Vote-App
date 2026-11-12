---
name: project-polity-v5-lot4-reaction-to-event
description: "v5 Lot 4 done (PR #145) — dt=8 reaction_to_event, the LLM decision; all four v5 decision-type lots now complete"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T20:11:12.266Z
---

Polity v5 Lot 4 (`reaction_to_event`, dt=8 — the LLM decision, §8) merged to `develop` (PR #145, squash commit `f61924f`). This closes out the v5 palier's decision-type work: config/codebook ([[project_polity_v5_lot1_events_config]]), the shock generators ([[project_polity_v5_lot2_shock]]), the awakening extension ([[project_polity_v5_lot3_event_salience]]), and now the LLM decision itself are all shipped.

**Corrected wire shape, the central judgment call**: an early roadmap-level sketch invented `ReactionDecision = {cid, event_type, target, ctx:{magnitude, self_gap, mandate_dev}, salience_delta, motif}`. Re-derived against `ResponseDecision`/`PressureDecision`'s actual shipped shape and shipped down to `{cid, salience_delta, motif}`:
- `event_type`/`target` are call-level constants (same call for every citizen in one call), dropped — mirrors why `ResponseDecision` has no `dt` field.
- `ctx.self_gap`/`mandate_dev` dropped for a hard reason, not a style preference: both take a real `Citizen` officeholder and raise on `None` platforms; on a vacancy tick there is no officeholder object to compute either from, and dt=8 runs population-wide regardless of vacancy by design — so requiring these fields would force either silently skipping the LLM branch on vacancy (a bug) or computing against a nonexistent object (impossible). Replaced by `event_salience` — the one per-citizen signal needing no officeholder, and directly the quantity the decision revises.
- Cross-field rule: `salience_delta == 0 ⟺ motif == 403 (EVENT_PERSONALLY_IRRELEVANT)`.

**Vacancy-safe by construction**: dt=8 always runs population-wide over all citizens (never gated on `current_office_holders`), so a scandal firing during a presidential vacancy still produces a full LLM call with `target=None` — no special-casing needed anywhere.

**Two independent calls per tick per firing event_type**: `decide_reaction_to_event` takes exactly one `event_type` per call; a tick where both scandal and economic shock fire calls it twice, in a fixed scandal-then-shock order. The second call's `ReactionContext.event_salience` reflects the first call's already-applied `update_event_salience` mutation (sequential, not simultaneous) — deliberate, pinned by a dedicated test.

**Single-conjunct gate**: `config.llm.enabled` alone (unlike dt=6/dt=10's two-conjunct gates) — the LLM branch only ever runs inside `if exogenous.scandal_fired/shock_crossed`, both of which already imply `events.enabled=True` via config.py's own cross-field rule, so a second conjunct would be redundant.

**Reliability spike**: real `ReactionMotif`/`EventType` enums from the start (no toy-schema stage, unlike the pre-v4-Lot-6 spike). Swept sizes 1/5/25 × 2 repeats × both event types — **12/12 PASS** against live `qwen3:8b` via the `ollama-polity` Docker container. One notable finding: a `SCANDAL` batch at size 25 produced 4 real `403` (irrelevant) responses, confirming the LLM path genuinely reaches the branch the deterministic baseline structurally cannot.

All four v5 decision-type/mechanism lots (config, shock generators, awakening extension, LLM decision) are now complete. Next: **Lot 5 (acceptance)** — flip `events.enabled` on for a dedicated run atop the v4 palier, verify §7bis.9e's "spark" claim (a shock tick's consultation-rate spike distinct from v4's gradual mandate-deviation erosion), sync `THEORY.md`/`traceability.md`. Not yet authorized — needs its own planning pass, per this project's standing lot discipline (see [[feedback_llm_reliability_investigation]] and prior `project_polity_v5_lot*` memories for the pattern).
