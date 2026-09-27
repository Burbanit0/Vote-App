---
name: project-polity-v6-lot3-neighbors-acting
description: "v6 Lot 3 done (PR #149) — neighbors_acting: awakening-gate extension + dt=10 wiring (§5), third lot of v6a"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T13:25:00.638Z
---

Polity v6 Lot 3 (`neighbors_acting` — the awakening-gate extension + dt=10 wiring, §5) merged to
`develop` (PR #149, squash commit `2f74580`). Third of v6a's four planned lots (config/codebook →
`social_graph.py` → **this lot** → acceptance). First lot to make [[project_polity_v6_lot2_social_graph]]'s
graph actually do anything.

**"Déjà mobilisée" judgment call**: the design doc's own §5/§7bis.9c text uses that specific verb
twice, not "already acted" — resolved as counting only a neighbor's most recently *applied*
`PressureAct.MOBILIZE`, never sign/launch (the petition lever is institutional/consequential per
§7bis.4a; mobilization is expressive/visibility-only per §7bis.4b — conflating them would blur a
distinction v4 Lot 5 already kept separable). Scoped to the **same target**: `neighbors_acting`
counts `(citizen_id -> target citizen_id)`, not a bare bool, so a neighbor's mobilization against a
now-departed officeholder doesn't wrongly count toward a new one — costs one extra dict value,
removes an ambiguity `current_office_holders`'s own "generalizes later" precedent already flags as
worth protecting.

**One-tick lag, threaded functionally**: `_run_accountability_phase`'s signature changed from `-> None`
to `-> Mapping[int, int]` — additive (every pre-existing direct-call test ignores the return value
and keeps passing unmodified). `mobilized_last_tick` is a bare local in `run_simulation`'s own
run-setup scope (same register as `economy_x`), fully **replaced** each tick from that tick's own
applied MOBILIZE decisions, never accumulated — mirrors dt=6's own `street_pressure` lag (v4 Lot 6):
`decide_pressure_actions` batches a whole cohort's decisions before anything lands, so a neighbor's
same-tick action can't be seen by construction.

**`PressureContext.neighbors_acting` activation is deliberately decoupled from the awakening gate's
own modulation flag** — a direct, intended consequence of v6 Lot 1's own cross-field rule
(`neighbors_acting modulation ⟹ social_graph.enabled`, never the reverse). The ctx field populates a
real `[0,1]` float whenever `config.social_graph.enabled`, regardless of whether
`awakening.context_modulation.neighbors_acting` additionally gates *who* gets consulted — the graph
can feed dt=10's `ctx` as a pure observability signal without mechanically gating the sampling, a
real experimental arm Lot 1 explicitly preserved and this lot makes real.

**306 FOLLOWING_NEIGHBORS wired into `PressureDecision`'s `Literal`, no coherence rule, no
`CODEBOOK_VERSION` bump.** 306 deliberately breaks the old "motif is a strict function of act"
partition (301/304/305 used to partition {1,2,3}/{0}/{4} exactly) — it's a second, genuinely
informative code for act∈{1,2,3} (own mandate deviation vs. seeing neighbors already act), but the
conclusion stays "no `model_validator`": the rejection-surface argument (a cross-field rule
constrained decoding can't enforce, at dt=10's own largest-batch/highest-call-volume decision type)
is if anything stronger with v6's added call volume. No version bump — the enum itself didn't change
since Lot 1 (`"1.5"`), consuming an already-reserved code is the "wire later" half of the
"reserve now, wire later" split, same as v4 Lot 6/7 and v5 Lot 4's own precedent.

Full offline suite green (1414 passed), mypy/flake8 clean, every pre-existing byte-for-byte
reproducibility test unmodified. New tests included a one-tick-lag pin (mirrors dt=6's own), an
end-to-end "marginal citizen only gets consulted once contagion crosses their threshold" pin with the
modulation flag on vs off, and an isolated-node run (Erdős–Rényi at shipped seed=42 deterministically
isolates citizen_id=3 — confirmed directly, not assumed).

**v6a is now 3 of 4 lots complete.** Next: **Lot 4 — acceptance**, the atomized-vs-contagion
comparison §7bis.9f itself names as the palier's own scientific deliverable ("pression atomisée" v4
vs "pression avec contagion" v6a). **Not yet authorized** — needs its own planning pass. Its own
already-flagged budget risk (§7bis.9g): a genuine tipping point is a *synchronous* LLM call spike
(a large fraction of the population crosses threshold in the same tick), not the steady per-tick load
every prior acceptance run has budgeted for — sizing must target the peak, not the mean.
v6b (chambre de sortition, [[project_polity_v6_lot1_social_graph_config]]'s own top-level split)
remains named and entirely unstaged.
