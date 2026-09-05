---
name: project-polity-v5-lot5-acceptance
description: "v5 Lot 5 done (PR #146) — acceptance run verifies the §7bis.9e \"spark\" claim; all five v5 lots complete, v5 palier done"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T02:45:49.868Z
---

Polity v5 Lot 5 (acceptance — the last lot of the v5 palier, §8) merged to `develop` (PR #146, squash commit `e25b244`). All five v5 lots are now complete: config+codebook ([[project_polity_v5_lot1_events_config]]), the shock generators ([[project_polity_v5_lot2_shock]]), the awakening extension ([[project_polity_v5_lot3_event_salience]]), the LLM decision ([[project_polity_v5_lot4_reaction_to_event]]), and now the acceptance measurement. **The v5 palier is done.**

**A real correction found live, mid-implementation, not assumed in advance**: the plan's original design used the `both` (full pressure menu) arm for the acceptance run. A calibration dry-run showed the president getting recalled within 1-2 ticks of nearly every election under a tuned events config, leaving the office vacant ~82% of an 8-year run — most scandal ticks landed during a vacancy, where `select_consulted` never runs at all, crushing the very signal the lot exists to measure. Switched to `electoral_only`, v4's own designated control arm: no petition/mobilization means the office stays continuously occupied for the whole run, and the awakening gate (what this lot measures) runs identically regardless of menu — only the *act* a consulted citizen may choose is restricted. This is the same "verify the assumption live during implementation, correct it with real data" pattern that's recurred at every v5 lot (Lot 2's Poisson-vs-Bernoulli check, Lot 3's step-ordering/scandal-target-timing bugs, Lot 4's wire-shape correction).

**A second bug caught during the calibration loop itself**: `Journal` opens its file in append mode (`journal.py`, deliberate — §16.1's append-only contract), so re-running the acceptance script into the same default output directory at a different tuning value was silently concatenating two runs into one journal, corrupting the calibration dry-run's own counts. Fixed by keying each run's directory to its own `scandal_rate`/`economy_sigma` values (`run_v5_acceptance.py`'s own `run_arm` now also refuses to overwrite an existing run dir, raising `FileExistsError` rather than silently appending).

**Calibrated events config** (shipped defaults essentially never fire — `scripts/events_calibration_results.md` measured zero `economic_shock_tick` crossings over a full 121-tick run at shipped `(phi=0.8, sigma=0.1, threshold=0.5)`): `scandal_rate_per_tick=0.15` (vs shipped 0.05), `economy_ar1_sigma=0.25` (vs shipped 0.1) — escalated once from a `sigma=0.2` starting point after a dry-run showed 0 shocks, confirmed via a cheap deterministic dry-run before committing to the expensive LLM run.

**Real acceptance numbers** (`scripts/acceptance_v5_results.md`, `electoral_only` arm, seed=42, population_size=100, duration=8y):
- LLM arm: elapsed 15743.8s (~4.37h), 0 replays, 4 scandals + 2 shocks fired. Firing-tick consultation rate 0.695 vs quiet-tick 0.595 — **ratio 1.168, the "spark" is real and in the predicted direction** (~17% higher).
- `electoral_only`/llm/8y is v4's own most expensive arm (it never recalls, so every tick keeps consulting the same standing population) — confirmed again here (~4.37h, close to v4 Lot 8's own 11776.3s/~3.27h for the same arm without events).
- **Nuanced finding on `mandate_deviation`**: not continuous "gradual drift" as the plan's own phrasing assumed — the real series shows `0.0` for the first tick after each election, a jump to `0.0231` at tick 2, then **flat at exactly 0.0231 for the rest of the term**, resetting to `0.0` at the next election. A one-time concession followed by stability, consistent with `electoral_only`'s own stance-mix profile (93.9% `SILENCE`, per v4's own prior measurement of this exact arm). Still real, still 100% LLM-attributable (§10.4's control-case guarantee — the deterministic arm's own `mandate_deviation` series is empty, `[]`), still a different *shape* from the punctual shock spikes — the spark claim holds, just phrased more precisely.
- Explicitly **not claimed**: a cascade. `neighbors_acting` stays structurally `null` through v5 — that remains v6 scope per §7bis.9e's own text ("n'est pas atteignable avant v6").

**`THEORY.md`** gained a new §10.7 "Les événements exogènes — l'étincelle" (the two generators, the "no fourth écart(t) term" design, the spark-not-cascade honest limit), with the old §10.7/§10.8 (limits/references) renumbered to §10.8/§10.9. Two new limits bullets added: the cascade/spark boundary, and the shipped-config-rarity note.

**Doc sync outside this worktree** (both gitignored, quoted verbatim in PR #146's body, no commit possible for either): `c:/Users/burba/Vote-App/docs/research/traceability.md:65` (the whole `docs/` dir is gitignored in that repo, confirmed via `git check-ignore`) — polity row status `implémenté (v4)` → `implémenté (v4, v5)`; and `polity-simulation-design-v2.md`'s point ouvert n°5 (persona regeneration triggers) — one line noting `economy_shock_threshold` now gives it a concrete trigger definition, informing but not closing the point (the persona library itself, §9, remains unbuilt).

The v5 palier is complete. Next per the design doc's own roadmap: **v6** (the social graph, §5 — the cascade prerequisite §7bis.9e names). **Not authorized to start** — needs its own planning pass when the user gives the next "go for the next step" instruction, per this project's standing lot discipline.
