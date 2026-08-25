# Composite cascade acceptance run — v4 + v5 + v6a together (§7bis.9e's full claim)

n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this project has already named. Runs `events.enabled=True` (scandal + economic shock) AND `social_graph.enabled=True` + `awakening.context_modulation.neighbors_acting=True` TOGETHER, under `mobilization_only`, for the first time — v5 Lot 5 and v6a Lot 4 each isolated exactly one of these two ingredients on top of v4's own pressure levers. `office_occupancy` is the pre-registered go/no-go signal this run's own calibration dry-run used before committing to the LLM arm.

| arm | engine | seed | years | elapsed(s) | replays | scandal_rate | economy_sigma | office_occupancy | mean L (last) | recalls | mandate_dev (last, src) | mandate_dev unified (last) | lever mix |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cascade | deterministic | 42 | 8 | 1.6 | 0 | 0.08 | 0.12 | 0.152 | 0.345 | legitimacy_floor=2 | — (recorded) | — | 0=0.496, 1=0.000, 2=0.000, 3=0.504, 4=0.000 |

## Reference rows — one ingredient at a time (NOT re-run here)

| arm | engine | years | elapsed(s) | replays | scandal_rate | economy_sigma | office_occupancy | mean L (last) | recalls | mandate_dev (last, src) | lever mix | scandals | shocks | firing consult. | quiet consult. | ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| electoral_only | llm | 8 | 15743.8 | 0 | 0.15 | 0.2 | 0.710 |  | 0.000 (ctx) | 0=0.143, 1=0.000, 2=0.000, 3=0.000, 4=0.857 | 4 | 2 | 0.695 | 0.595 | 1.168 |
| mobilization_only | llm | 8 | 6932.1 | 0 | — | — | 0.475 | legitimacy_floor=2 | 0.000 (ctx) | 0=0.371, 1=0.000, 2=0.000, 3=0.629, 4=0.000 | — | — | — | — | — |

Both rows: same seed (42), same `population_size` (100), same `ambition_threshold` (0.0), same duration (8y), same `legitimacy`/`mandate`/`awakening` enabled. The v5 row is `electoral_only` + `events.enabled=True`, `social_graph` off (the "spark" alone, `acceptance_v5_results.md`). The v6a row is `mobilization_only` + `social_graph.enabled=True`/`neighbors_acting=True`, `events` off (the "contagion" alone, `acceptance_v6a_results.md`). Cited verbatim, never re-derived.

## Contagion metrics (mean/max consultation and mobilization per tick)

| arm | engine | mean consult./tick | max consult./tick | mean mobilize/tick | max mobilize/tick | mean realized neighbors_acting | max realized neighbors_acting |
|---|---|---|---|---|---|---|---|
| cascade | deterministic | 10.636 | 75 | 5.364 | 39 | — | — |

## Cascade metrics — mobilization on firing-adjacent ticks vs. quiet ticks

| arm | engine | firing ticks | firing-adjacent mean mobilization | firing-adjacent max mobilization | quiet mean mobilization | ratio |
|---|---|---|---|---|---|---|
| cascade | deterministic | 0 | — | — | 5.364 | — |

## GO/NO-GO outcome: the LLM arm was never run

*« un basculement de type Gilets jaunes n'est pas atteignable avant v6 ... il requiert simultanément le graphe social (v6), les chocs exogènes (v5) et les leviers de pression (v4) »*
**The deterministic dry-run's own `office_occupancy=0.152` never cleared the pre-registered `>= 0.5` go/no-go bar, and every lever this run's own plan permits to fix that was tried and exhausted — the LLM arm (~2.5-5h forecast) was deliberately never run.**

1. **Halving the event rates does not converge.** Two calibration attempts, `r0.08/s0.12` and `r0.04/s0.06`, produced BYTE-IDENTICAL outcomes (`office_occupancy=0.152, recalls=2, scandals=0, shocks=0`) — the events never fire before the collapse either way, so they were never the cause and no amount of retuning can be the fix.
2. **The collapse is pre-existing and menu/event-independent, traced to source.** The election/journal timeline (seed=42) shows: `elected` tick 0 -> `recalled` tick 1 (`L: 0.345 -> 0.026`, floor `0.2`) -> vacant through tick 15 -> `elected` tick 16 -> `recalled` tick 17 -> vacant through tick 31 -> `elected` tick 32. At tick 0 the awakening gate is maximally permissive (`proximity=0`, no other modulation term has a chance to be nonzero yet), consulting 67/100 and mobilizing 33/100 — exactly v4 Lot 4's own committed "mobilize max ~=0.33 right after election" number. That rate alone is already inside the "33.3x amplification" wall v4 Lot 4's own docstring names (`street_pressure` decay=0.85, `w_mob`=0.5, legitimacy decay=0.9). This exact outcome (`legitimacy_floor=2` recalls, `mean L (last)=0.345`) is byte-identical to v4 Lot 8's own committed `mobilization_only` row and v6a Lot 4's own committed contagion row — proof this is a pre-existing property of the `mobilization_only` deterministic baseline itself, present since v4 Lot 8, never flagged before because no prior acceptance script computed an explicit `office_occupancy` metric.
3. **Seed-hunting does not help, and generalizes into a separate, larger finding.** An 11-seed sweep (1, 2, 3, 5, 7, 10, 13, 21, 99, 100, 123) found 0/11 clearing the go/no-go bar: 9/11 never elect a president at all (`election_no_winner` at every scheduled election — `Blank` wins the `two_round` runoff outright whenever enough voters find all 5 party platforms unacceptable), and the 2 that do elect someone (seeds 10, 99) still collapse via the same mobilize-driven recall. Confirmed directly this is unrelated to `pressure_menu`/`social_graph`/`events` (elections resolve before any of those mechanisms run): `electoral_only` at seeds 1 and 7 hits the identical `election_no_winner` outcome. Seed=42 -- the seed every acceptance run in this project (v4 Lot 8 through v6b Lot 4) has used -- is not a representative draw for this failure mode; it sits just under a ~32-34%-forced-blank threshold by coincidence, not by any distinguishing population property (its own mean `blank_threshold` and mean distance-to-nearest-nominee are not systematically more favorable than several failing seeds). This is a separate, larger finding about every prior acceptance script's own `ambition_threshold=0.0` "guarantees a real elected president" comment, noted here but not otherwise acted on by this script.
4. **Raising `legitimacy.recall_floor` toward zero was ruled out on purpose** -- this project's own v6b Lot 4 write-up already named that fix "scientifically inelegant... disables accountability rather than testing it" after making that exact mistake once.

**Conclusion**: §7bis.9e's full three-ingredient claim is not testable under `mobilization_only` at the current shipped `population_size=100`/seed=42 scale -- not because contagion or events fail to interact usefully, but because the office is vacant before they get the chance to. This is itself the honest result of this run: a structural precondition gap, not a null result from a bug. v6a Lot 4's own committed LLM arm (same menu, no events) also shows `legitimacy_floor=2` recalls, suggesting (not proving -- office_occupancy was never computed there) the LLM engine likely does not escape this either.
