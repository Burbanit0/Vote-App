# v6b acceptance run — elected vs. sortition (§6bis.3), Lot 4

n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this project has already named. The elected side reuses `run_acceptance_comparison.py`'s own `both` arm shape (full pressure menu, legitimacy/mandate/awakening enabled) -- §6bis.3's own comparison is against a president "soumise aux trois canaux du §7bis", all three, not one isolated lever. `social_graph.enabled`/`events.enabled` stay OFF throughout, the same confound-avoidance call v5 Lot 5 and v6a Lot 4 already made independently. Unlike v6a Lot 4, this comparison needs BOTH quantities from the SAME run at the SAME ticks, so there is no prior acceptance row to cite -- this is one new, self-contained run.

| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | mandate_dev (mean/max) | chamber_dev (mean/max) | motif mix | last seated size |
|---|---|---|---|---|---|---|---|---|---|---|
| sortition | deterministic | 8 | 1.6 | 0 | 0.345 | legitimacy_floor=2 | —/— | 0.000/0.000 (known 0.0, no LLM call) | — | 30 |
| sortition | llm | 8 | 16384.8 | 38 | 0.450 | legitimacy_floor=2 | 0.000/0.000 | 0.000/0.035 | 701=0.993, 702=0.007 | 30 |

## §6bis.3's own headline question

*« L'absence de pression électorale produit-elle des décisions plus « sincères » (alignées sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de responsabilité) ? »*
- Compare `mandate_dev (mean/max)` against `chamber_dev (mean/max)` in the `llm` row above: a materially LOWER chamber_deviation than mandate_deviation is the signature of insulation producing more sincere (less drifted) decisions; a comparable or higher chamber_deviation would say the opposite -- that accountability pressure alone doesn't explain the elected side's own drift.
- `motif mix` (701 SINCERE_POSITION vs 702 DELIBERATIVE_SHIFT) is the model's own stated label for each decision -- not enforced by any coherence rule (v6b Lot 3's own removed validator), so it is informative but non-binding: a chamber that stays mostly 701 is sincere by its own account; a chamber that trends toward 702 is not, independent of whether the resulting `chamber_deviation` values are themselves large or small.
- `last_seated_size` cross-checks v6b Lot 2's own pool-exhaustion calibration finding (`sortition_calibration_results.md`) lands the same way inside a real LLM run: the chamber should stay at or near `seats=30` for the whole run once the relaxed-pool fallback engages.
- **Not claimed here**: the sortition chamber's own institutional consequence (veto power, design doc point ouvert n°11) -- this MVP is comparison-only, with no lawmaking concept for a veto to act on.
