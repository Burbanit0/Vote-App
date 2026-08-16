# v6a acceptance run — atomized vs. contagion (§7bis.9f), Lot 4

n=1 (one seed, no Monte Carlo band), the same limit v4 Lot 8's own acceptance run already named. Isolates §7bis.9f's own one-variable comparison — whether the awakening threshold's f(contexte) includes the neighborhood term — on top of an already-mobilization-capable population. `events.enabled` stays OFF throughout: v5 Lot 5 already separately demonstrated the "spark" claim, and adding it here would reintroduce a second simultaneously-changing variable §7bis.9f's own table doesn't ask for. **Not claimed here**: a full, shock-triggered, Gilets-Jaunes-scale basculement (§7bis.9e's own three-ingredient claim, v4+v5+v6 together) — that composite run was never executed.

| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | petition success/removal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| contagion | deterministic | 8 | 0.7 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | 0.507 | 0=0.496, 1=0.000, 2=0.000, 3=0.504, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| contagion | llm | 8 | 6932.1 | 0 | 0.475 | legitimacy_floor=2 | 0.000 (ctx) | 0.309 | 0=0.371, 1=0.000, 2=0.000, 3=0.629, 4=0.000 | 1=1.000, 2=0.000, 3=0.000, 4=0.000 | —/— |

## Atomized reference (v4 Lot 8, `scripts/acceptance_v4_results.md`, NOT re-run here)

| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | petition success/removal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mobilization_only | deterministic | 8 | 0.0 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | 0.507 | 0=0.511, 1=0.000, 2=0.000, 3=0.489, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |
| mobilization_only | llm | 8 | 6525.0 | 0 | 0.370 | legitimacy_floor=2 | 0.000 (ctx) | 0.000 | 0=0.301, 1=0.000, 2=0.000, 3=0.699, 4=0.000 | 1=1.000, 2=0.000, 3=0.000, 4=0.000 | —/— |

Same seed (42), same `population_size` (100), same `ambition_threshold` (0.0), same `mobilization_only` menu, same duration (8y), same `legitimacy`/`mandate`/`awakening` enabled — differing only in `social_graph.enabled`/`awakening.context_modulation.neighbors_acting`. Cited verbatim, not re-derived.

## Contagion metrics (v6 Lot 3's own `neighbors_acting`, not in `RunMetrics`)

| arm | engine | mean consult./tick | max consult./tick | mean mobilize/tick | max mobilize/tick | mean realized neighbors_acting | max realized neighbors_acting |
|---|---|---|---|---|---|---|---|
| contagion | deterministic | 10.636 | 75 | 5.364 | 39 | — | — |
| contagion | llm | 14.697 | 85 | 9.242 | 85 | 0.184 | 1.000 |

## §7bis.9f's own headline question

*« Une population isolée se mobilise-t-elle jamais, ou la contagion sociale est-elle la condition nécessaire de toute mobilisation d'ampleur ? »*
- Compare the `lever mix` `3=` (MOBILIZE) share and the `recalls` column between the contagion row above and the atomized reference — a materially higher mobilize share and/or recall count under contagion is the signature of the neighborhood term actually amplifying collective action, not just individual decisions.
- Compare `max mobilize/tick` (this run's own new metric, absent from the atomized reference) against the run's own `mean mobilize/tick` — the ratio is the size of any single tick's own collective spike, the closest this lot gets to observing a bandwagon moment without claiming a full cascade.
- `mean/max realized neighbors_acting` confirms the channel was genuinely active and non-degenerate in this run, not just theoretically wired.
