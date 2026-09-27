# v5 acceptance run — the "spark" (§7bis.9e), events atop the v4 `electoral_only` control arm (Lot 5)

n=1 (one seed, no Monte Carlo band), same limit as v4 Lot 8's own acceptance run. Verifies the narrow claim v5 can actually demonstrate: a shock tick's consultation-rate spike, distinct from v4's own gradual mandate-deviation erosion, in the same run. A full cascade needs v6's social graph too (§7bis.9e: "n'est pas atteignable avant v6") — not claimed here.

| arm | engine | years | elapsed(s) | replays | scandal_rate | economy_sigma | mean L (last) | recalls | mandate_dev (last, src) | lever mix | scandals | shocks | firing consult. | quiet consult. | ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| electoral_only | deterministic | 8 | 3.7 | 0 | 0.15 | 0.25 | 0.510 |  | — (recorded) | 0=0.493, 1=0.000, 2=0.000, 3=0.000, 4=0.507 | 4 | 2 | 0.795 | 0.701 | 1.135 |
| electoral_only | llm | 8 | 15743.8 | 0 | 0.15 | 0.25 | 0.710 |  | 0.000 (ctx) | 0=0.143, 1=0.000, 2=0.000, 3=0.000, 4=0.857 | 4 | 2 | 0.695 | 0.595 | 1.168 |

## No-spark reference (v4 Lot 8, `scripts/acceptance_v4_results.md`, NOT re-run here)

| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | petition success/removal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| electoral_only | llm | 8 | 11776.3 | 0 | 0.710 |  | 0.000 (ctx) | 0.343 | 0=0.112, 1=0.000, 2=0.000, 3=0.000, 4=0.888 | 1=0.061, 2=0.000, 3=0.939, 4=0.000 | —/— |

Same seed (42), same `population_size` (100), same `ambition_threshold` (0.0), same full menu, same duration (8y), same `legitimacy`/`mandate`/`awakening` enabled — differing only in `events.enabled`. Cited verbatim, not re-derived (see `indexer.py`'s own module docstring for why the shipped calibration/acceptance evidence is never re-run through new code).

## The spark claim

- **Punctual, not gradual**: compare `firing consult.` against `quiet consult.` in the table above — the ratio column is the size of the spike. A shock tick's consultation rate should measurably exceed the run's own quiet-tick average.
- **Distinct from v4's own erosion, in the same run**: `mandate_dev` is dt=6's own gradual, monotonic-ish drift (already documented in `THEORY.md` §10.4/§10.7) — read its full series from this run's own `metrics.json` (`mandate_deviation`) alongside the punctual spikes above; the two should read as two different shapes off one journal, not two journals compared to each other.
- **Not a cascade**: `neighbors_acting` stays structurally `null` through v5 — no citizen sees another citizen's action, so nothing here demonstrates collective bandwagon behavior. That remains v6 scope (§7bis.9e).
