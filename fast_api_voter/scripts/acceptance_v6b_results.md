# v6b acceptance run — elected vs. sortition (§6bis.3), Lot 4

**n=1, one seed (seed=42, `both` pressure menu) — this required two runs and one corrected metric to get a comparable answer.** Same limit every prior acceptance run in this project has already named. The elected side reuses `run_acceptance_comparison.py`'s own `both` arm shape (full pressure menu, legitimacy/mandate/awakening enabled) — §6bis.3's own comparison is against a president "soumise aux trois canaux du §7bis", all three, not one isolated lever. `social_graph.enabled`/`events.enabled` stay OFF throughout, the same confound-avoidance call v5 Lot 5 and v6a Lot 4 already made independently.

## Two runs

The first acceptance run (`scripts/acceptance_v6b_runs/`, shipped `legitimacy.recall_floor`) confounded the comparison by construction: under the full pressure menu, the elected president's legitimacy collapses within one tick of **both** presidential elections (`L` 0.43→0.12, then 0.44→0.11), triggering a `legitimacy_floor` recall each time (`recalls_by_trigger: {"legitimacy_floor": 2}`, elapsed 16384.8s, 38 replays — verified against that run's own `metrics.json`). The office sits vacant for most of the run's 33 ticks, so `mandate_deviation` reads exactly 0.0 throughout — not fidelity, just lack of exposure.

A second run, identical except `legitimacy.recall_floor=0.0` (`scripts/acceptance_v6b_runs_recallfloor0/`), removes that confound by construction: `office_occupancy=1.0`, zero recalls for the whole run. But `mandate_deviation` **still** read 0.0 — a different, second problem: `pledge_scope: top_k_priorities` (the shipped default) only weights an officeholder's own top-5 priority dimensions, and the three dimensions this president actually drifted on (weights 0.0745 / 0.0395 / 0.0205) fell outside his own top-5. The metric was structurally blind to the drift, not merely under-weighting it — documented as a metric-design bug in `accountability.py`'s docstrings and in `traceability.md`, distinct from this run's own scientific question.

## Results — second run (`legitimacy.recall_floor=0.0`)

| arm | engine | years | elapsed(s) | replays | office_occupancy | mean L (last) | recalls | mandate_dev shipped (mean/max) | mandate_dev unified (mean/max) | chamber_dev (mean/max) | motif mix (chamber) | last seated size |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sortition | deterministic | 8 | 2.6 | 0 | — | 0.345 | none | —/— (no LLM call) | —/— (no LLM call) | 0.000/0.000 (known 0.0, no LLM call) | — | 30 |
| sortition | llm | 8 | 15874.6 | 28 | 1.0 | 0.405 | none | 0.000/0.000 (top_k_priorities blind spot) | **0.1496/0.2312** | 0.000036/0.0353 | 701=0.9970, 702=0.0030 | 30 |

`mandate_dev unified` recomputed post-hoc with the same method already used by `chamber_dev` — `weighted_euclidean` over the officeholder's **full**, untruncated `issue_priorities` (no top-k restriction) — applied identically to both sides for a fair, same-basis comparison. Method: an ad hoc, read-only replay of `representative_response`'s own journaled `shifts` via `apply_shifts`, over a population reconstructed deterministically from the run's own `(config, seed)`.

## The clamp-saturation finding — a lower bound, not a stop

The unified `mandate_dev` series is not monotone continuous: it plateaus at exactly two points — 0.194070 from tick 10 to tick 15 (end of the first mandate), and 0.231248 from tick 27 to tick 31 (end of the second). Verified directly against the journal: at every one of those ticks, `representative_response` keeps emitting a non-empty `shifts` (motif `302 STREET_PRESSURE_RESPONSE`, `stance=1` concession) on the same three dimensions, with a positive delta — the pressure never stops. What plateaus is `apply_shifts`'s own `[0,1]` clamp: all three dimensions have already reached `1.0`, and every subsequent delta targets an unbounded value above 1.0 (typically 1.15 / 1.10 / 1.05), silently absorbed.

A parallel, diagnostic-only reconstruction — same journaled shifts, replayed without ever applying the `[0,1]` clamp — confirms it quantitatively: the unbounded "shadow" deviation reaches **0.701** by the end of the first mandate (vs. 0.194 clamped — **×3.6**) and **0.642** by the end of the second (vs. 0.231 clamped — **×2.8**). This second number does not replace the first: they answer different questions. The clamped value is what the system actually measures and acts on (`écart(t)`, the confidence vote, the awakening gate all read `revealed_position`, i.e. the clamped version); the unclamped shadow exists nowhere in the model — it estimates how much pressure the clamp is absorbing. **The officially reported deviation is therefore a lower bound on the real magnitude of drift, never an exact ceiling.**

Also flagged, separately from this run's own scientific result: `apply_shifts` clamps silently, with no return value, log, or journal event — a broader observability gap in the primitive itself (shared by dt=5 campaign_positioning, dt=6 representative_response, dt=11 chamber_deliberation), not specific to `mandate_deviation`. Documented in `apply_shifts`'s own docstring (`llm_behavior_engine.py`) and in `traceability.md`; not fixed here.

## §6bis.3's own headline question

*« L'absence de pression électorale produit-elle des décisions plus « sincères » (alignées sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de responsabilité) ? »*

- On this run, the answer leans clearly toward **sincere for the chamber, erratic — in the sense of continuous, substantial drift under street pressure — for the elected president**: `chamber_dev` stays essentially inert (mean 0.000036, 99.70% of decisions self-labeled `SINCERE_POSITION`) while the president's own unified deviation climbs steadily to a clamp-saturated ceiling.
- The clamp does not soften this conclusion, it strengthens it: the reported `mandate_dev` (0.1496 mean) is itself an understatement of the true gap between the two trajectories, by a factor of ×2.8 to ×3.6 on the measurable portion.
- Not a general conclusion: n=1, one seed, no Monte Carlo band. The first run (confounded by the recall calendar under the shipped `recall_floor`) remains a distinct, informative data point about `both`-menu recall dynamics, not a result to discard.
- `motif mix` (701 SINCERE_POSITION vs 702 DELIBERATIVE_SHIFT) is the model's own stated label for each decision — not enforced by any coherence rule (v6b Lot 3's own removed validator), so it is informative but non-binding.
- `last_seated_size` cross-checks v6b Lot 2's own pool-exhaustion calibration finding (`sortition_calibration_results.md`) lands the same way inside a real LLM run: the chamber stays at `seats=30` for all 9 rotations.
- **Not claimed here**: the sortition chamber's own institutional consequence (veto power, design doc point ouvert n°11) — this MVP is comparison-only, with no lawmaking concept for a veto to act on.
