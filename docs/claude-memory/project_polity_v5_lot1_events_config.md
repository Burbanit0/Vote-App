---
name: project-polity-v5-lot1-events-config
description: "v5 Lot 1 (§8 exogenous events, config + codebook reservations) shipped in PR #142, merged to develop — first lot of the new v5 palier, roadmap plan appended to the same plan file as v4's"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T14:15:38.978Z
---

v5 ("événements exogènes", §8) is now underway — the palier after v4's full completion (v4 palier +
vLLM switch + §16.6 storage/DuckDB + Lot 9 competitive blank voting, all merged). A full top-level
roadmap plan (5 lots) was written and approved via Plan Mode, appended to the same plan file that
holds v4's own top-level plan (`C:\Users\burba\.claude\plans\merry-hugging-hamming.md` — this file is
the durable record of every judgment call for both paliers; read it before starting v5 Lot 2+).

**v5's shape**: Lot 1 (config+codebook, done) → Lot 2 (`shock.py` — Poisson scandal + AR(1) economic
climate) → Lot 3 (`event_salience` + awakening extension + deterministic reaction baseline) → Lot 4
(dt=8 `reaction_to_event`, LLM) → Lot 5 (acceptance run + THEORY.md sync).

**Key judgment calls already made (won't need re-litigating)**:
- `reaction_to_event` (dt=8) is a **population-wide broadcast**, not awakening-gated — every citizen
  reacts to a shock, unlike dt=10's consulted-cohort pattern. Invented wire shape (design doc cites a
  nonexistent §3.6.7): `{cid, event_type, target, ctx, salience_delta ∈[0,max], motif}`.
- Scandal (Poisson) + economic shock (AR(1)) **bundle into one lot** (Lot 2) — same decision type,
  same sequencing slot, same landing point; splitting them would produce an uninterpretable
  intermediate stopping point.
- **No fourth `écart(t)` term.** A shock never touches legitimacy directly — it perturbs the
  **awakening gate** via a new decaying `event_salience` field, which raises consultation, and
  everything downstream stays exactly the existing LLM-mediated `pressure_action` path. This was the
  single most consequential call — directly required by §8's own text rejecting "une formule d'impact
  directe sur legitimacy_perceived".
- `legitimacy_perceived` (named in §8) is confirmed a genuinely different, never-built field from
  `legitimacy_capital` (v4's real quantity) — not a stale synonym. Verified via the design doc's own
  §2.2 Citizen table, zero repo hits.
- §9 (persona library) is **unlocked by v5, not built by it** — `economy_shock_threshold` gives point
  ouvert n°5 (persona regeneration trigger) its first concrete definition, but the rest of §9's schema
  stays open; dt=8 doesn't need personas to function (raw fields suffice, same as dt=6/dt=10).
- A **third independent RNG stream**, `events_rng`, reserved (docstring only, not yet instantiated)
  next to the existing `rupture_rng` — never reuses it, same "fresh stream per concern" precedent.

**What Lot 1 shipped** (PR #142, merged 2026-08-15): `EventsConfig` dataclass + `_parse_events`
(`enabled`/`scandal_enabled`/`economic_shock_enabled` + 7 tunables), `AwakeningContextModulation`
gained `event_salience: bool` (raises `NotImplementedError` in `awakening_threshold` until Lot 3
implements it — mirrors the existing `neighbors_acting` v6 guard), two new cross-field rules in
`load_config` (`events.enabled` requires `awakening.enabled` + `event_salience` modulation on).
`codebook.py`: `DecisionType.REACTION_TO_EVENT = 8` (was reserved-but-absent), new `EventType`
enum (`SCANDAL=1`/`ECONOMIC_SHOCK=2`), new `ReactionMotif` enum in the 400-499 range (`401`/`402` are
the design doc's own codes kept verbatim, `403 EVENT_PERSONALLY_IRRELEVANT` is new, grounding the
`salience_delta==0` branch — only reachable via the LLM path, Lot 4). `CODEBOOK_VERSION` bumped
`"1.3"`→`"1.4"` (also bumped the shipped `llm.codebook_version` YAML value and the
`codebook_motifs` row-count test 29→32 for the 3 new codes). Zero behavior change at the shipped
default (`events.enabled: false`) — all 1282 tests pass, every byte-for-byte reproducibility test
unmodified.

**How to apply**: v5 Lot 2 (`shock.py`) needs its own short planning pass before starting, same
discipline as every v4 lot — not yet authorized. See [[project_polity_lot9_blank_vote]] for the
sibling "verify claims against real output" discipline this palier's plan continues to apply (the
Plan agent verified `CODEBOOK_VERSION`, the `legitimacy_perceived` gap, and the RNG-stream precedent
directly against the live codebase before the plan was finalized, not just from the design doc).
