---
name: project-polity-v6a-lot4-acceptance
description: "v6a Lot 4 done (PR #150) — atomized-vs-contagion acceptance run (§7bis.9f), v6a fully complete"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T16:06:18.791Z
---

Polity v6a Lot 4 (acceptance — the atomized-vs-contagion comparison §7bis.9f names as the palier's
own scientific deliverable) merged to `develop` (PR #150). Fourth and final lot of v6a
([[project_polity_v6_lot1_social_graph_config]] → [[project_polity_v6_lot2_social_graph]] →
[[project_polity_v6_lot3_neighbors_acting]] → this lot). **v6a is now fully complete.**

**Experimental design: only one new arm needed, not two.** v4 Lot 8's own already-committed
`mobilization_only` rows (`scripts/acceptance_v4_results.md`) were confirmed by direct inspection
to never touch `social_graph`/`events` — both stay at shipped `enabled: false` — so they serve
verbatim as the "atomized" reference. The one new arm run: identical config (seed 42,
`population_size=100`, `mobilization_only` menu, 8 years, both engines) + `social_graph.enabled=True`
+ `awakening.context_modulation.neighbors_acting=True`. `events.enabled` stayed off throughout
(v5 Lot 5 already separately demonstrated the "spark" claim; adding it here would reintroduce a
second simultaneously-changing variable §7bis.9f's own table doesn't ask for).

**Real finding, honestly nuanced — not the naive "contagion amplifies mobilization" story.** On the
*cumulative* lever mix, contagion's `MOBILIZE` share was actually slightly *lower* (0.629 vs 0.699
atomized) and final mean legitimacy *higher* (0.475 vs 0.370), same recall count (2, both
legitimacy-floor) — contagion is not a simple amplitude multiplier. What it *did* produce: a genuine
tick-level synchronization spike with no atomized-regime analogue — up to 85 of ~100 citizens
mobilizing in a single tick under contagion+LLM, vs a max of 39 on the matched deterministic
baseline (`neighbors_acting` realized: mean 0.184, max 1.000 — channel genuinely active, not just
wired). Written up in `THEORY.md` §10.8 as "the contagion channel changes the temporal *form* of
mobilization (synchronized spikes), not its aggregate volume, on this one seed (n=1)" — the honest
"spark, not cascade" framing, consistent with §7bis.9e's own three-ingredient claim (v4+v5+v6a
together) never having been run as one composite.

**A real bug was caught by testing, not assumed away.** `scripts/run_v6a_acceptance.py`'s own
`_metrics_to_json` never serialized `petition_success_rate`/`petition_removal_rate`/
`petition_downgrades` even though `summarize()` read them — `KeyError` on the very first
`--summarize` invocation, after the ~2-hour LLM run had already completed. Fixed by adding the three
fields to the serializer and **re-indexing both already-run journals directly from disk** (via
`index_run` against the reconstructed config) rather than re-running the expensive simulation —
`indexer.py`'s own read-only, journal-replay design made this cheap and safe.

**Live LLM run measured**: `contagion/llm/8y`: 6932.1s (~1.9h), 0 replays, recalls=2. Deterministic
calibration dry-run (`contagion/deterministic/8y`: 0.7s, recalls=2, mean L 0.345) matched the
`mobilization_only`/deterministic/8y anchor almost exactly before the expensive LLM run was
committed to — the same "measure before committing" go/no-go checkpoint every prior acceptance lot
has used, here with no tunable parameter to sweep (topology/amplitude both shipped defaults).

**v6a is fully complete**: config/codebook (Lot 1), graph generation (Lot 2), the awakening-gate
extension + dt=10 wiring (Lot 3), and this acceptance measurement (Lot 4). `THEORY.md` §10.8 syncs
the mechanism and the real finding; `traceability.md`'s polity row status cell now reads
`implémenté (v4, v5, v6a)`; the design doc's own §5 point ouvert (static vs. evolving graph) carries
an informing-not-closing annotation. **v6b (chambre de sortition, [[project_polity_v6_lot1_social_graph_config]]'s
own top-level split)** remains named and entirely unstaged — not authorized to start, needs its own
planning pass when the user authorizes it.
