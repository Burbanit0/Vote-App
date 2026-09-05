---
name: project-polity-v5-lot2-shock
description: "v5 Lot 2 (§8 exogenous events, shock.py generators) shipped in PR #143, merged to develop — second lot of v5, a real awakening-gate landmine found and routed around during planning"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T15:25:34.950Z
---

v5 Lot 2 (`shock.py` — Poisson scandal process + AR(1) economic climate, §8) is implemented and
merged to `develop` 2026-08-15 (PR #143). Second lot of the v5 palier, following Lot 1's config/
codebook reservations (see [[project_polity_v5_lot1_events_config]]).

**What it does**: `shock.py` ships two pure generator functions — `scandal_arrival(rng, config)`
(Bernoulli-thinned per-tick arrival, gated at the sub-mechanism level before any draw) and
`economic_shock_step(previous_x, rng, config)` (AR(1): `x(t) = phi*x(t-1) + sigma*epsilon(t)`,
same pre-draw gating). A new `_run_exogenous_events` orchestration function in
`run_polity_simulation.py`, called unconditionally every tick right after
`_attempt_rupture_candidacies`, journals `scandal_occurred` (targets the sitting president,
`target: null` on vacancy) and the anti-saturation-gated `economic_shock_tick`. A third independent
RNG stream, `events_rng`, is instantiated for the first time (never reuses `rupture_rng`).

**Key modeling call, worth remembering**: `scandal_rate_per_tick` is implemented as a **Bernoulli
draw per tick** (`rng.random() < rate`), not a Poisson λ — forced by the fact that Lot 1 already
shipped the field `_get_ratio`-constrained to `[0,1]`, which is a probability's domain, not an
intensity's. This is a standard, defensible discretization of "processus de Poisson" at unit time
resolution, not a deviation from the design doc — documented explicitly in `shock.py`'s own
docstring so a future reader doesn't mistake it for a shortcut.

**A real, load-bearing landmine was found during planning and routed around, not just noted**:
`accountability.awakening_threshold`'s `event_salience` `NotImplementedError` guard (shipped by
Lot 1) turned out to be reachable **independent of `llm.enabled`** — it fires the moment
`awakening.enabled` is true (forced whenever `events.enabled` is true) AND any officeholder has a
non-`None` `revealed_position`, which `declare_candidacy` sets on the **deterministic** path too
(not LLM-only, as a first-pass reading assumed). What actually keeps Lot 2's own tests safe is that
the shipped `candidacy.ambition_threshold` (0.7) never produces a winner at seed=42, so
`current_office_holders` stays empty for the whole run — a narrow, easily-broken safety margin, not
a structural guarantee. The one test needing a real elected president
(`test_scandal_occurred_targets_the_sitting_president...`) was redesigned to call
`_run_exogenous_events` **directly** against a hand-built citizen list rather than through
`run_simulation`, sidestepping the guard entirely (also just the better-isolated test). **Lesson for
Lot 3** (whose actual job is to remove this guard): any test combining `events.enabled=True` with a
real elected president will crash until Lot 3 lands — this is now a known, load-bearing constraint on
every test written in the meantime, not a surprise to rediscover.

**Calibration evidence** (`scripts/calibrate_events.py` → `scripts/events_calibration_results.md`):
scandal arrival rate matches the configured rate within ordinary small-N sampling noise; the AR(1)
series' empirical std matches its closed-form steady state (`sigma/sqrt(1-phi²)`) to within ~1-3% at
every swept `(phi, sigma)`, confirming it's genuinely mean-reverting; the shipped
`economy_shock_threshold` (0.5) is a rare ~3σ event at shipped `(phi=0.8, sigma=0.1)` — zero
crossings in a 121-tick sweep is expected, not a bug, which is why the test suite uses a tuned
`sigma=0.3` to make that branch observable. No shipped value changed as a result.

**How to apply**: v5 Lot 3 (`event_salience` field + the awakening extension that finally removes
the `event_salience` `NotImplementedError` guard + the deterministic reaction baseline) needs its own
planning pass — not yet authorized. See [[project_polity_v5_lot1_events_config]] for the palier's
top-level judgment calls (no fourth `écart(t)` term, §9 unlocked-not-built, etc.) and
[[project_polity_lot9_blank_vote]] for the sibling "verify claims against real output" discipline —
this lot's landmine was caught the same way, by tracing actual code rather than trusting a first-pass
summary.
