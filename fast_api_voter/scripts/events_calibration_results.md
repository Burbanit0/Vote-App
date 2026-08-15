# Exogenous events calibration sweep (v5 Lot 2, §8)

## Scandal arrival rate (Bernoulli-per-tick vs. configured `scandal_rate_per_tick`)

| configured rate | empirical rate | total ticks |
|---|---|---|
| 0.05 | 0.0331 | 121 |
| 0.10 | 0.0826 | 121 |
| 0.20 | 0.1983 | 121 |

## AR(1) economic climate: uncensored series vs. closed-form steady state

x(t) = phi*x(t-1) + sigma*epsilon(t), epsilon ~ N(0,1); theoretical steady-state mean=0, std=sigma/sqrt(1-phi^2). Trace length 10000 steps, seed=42, computed via shock.economic_shock_step directly (not journaled -- economic_shock_tick is threshold-gated, so this is the only way to see the uncensored series).

| phi | sigma | empirical mean | empirical std | theoretical std | max |x| |
|---|---|---|---|---|---|
| 0.8 | 0.1 | -0.0052 | 0.1684 | 0.1667 | 0.6145 |
| 0.5 | 0.1 | -0.0021 | 0.1165 | 0.1155 | 0.4655 |
| 0.95 | 0.05 | -0.0105 | 0.1658 | 0.1601 | 0.6248 |

## `economic_shock_tick` crossing rate at the shipped `economy_shock_threshold` (0.5)

| phi | sigma | threshold | crossing rate | total ticks |
|---|---|---|---|---|
| 0.8 | 0.1 | 0.5 | 0.0000 | 121 |
| 0.5 | 0.1 | 0.5 | 0.0000 | 121 |
| 0.95 | 0.05 | 0.5 | 0.0000 | 121 |

## Findings

- **Scandal arrival matches the configured rate within ordinary sampling noise.** At 121 ticks
  (30 years, the shipped `run.duration_years`), the expected count at `rate=0.05` is ~6.05 with a
  binomial std of ~2.4 -- the observed 0.0331 (4/121) is well within one std of the configured
  value, not a discrepancy. All three configured rates land inside their own small-N confidence
  band; no systematic bias in the Bernoulli-per-tick reading (see shock.py's own docstring for why
  this is the correct discretization of "processus de Poisson" under `EventsConfig`'s already-
  shipped `[0,1]`-ratio-typed `scandal_rate_per_tick`).
- **AR(1) is genuinely mean-reverting and matches its closed-form steady state closely at every
  swept `(phi, sigma)`**, over a long (10,000-step) uncensored trace: empirical std tracks
  `sigma/sqrt(1-phi^2)` to within ~1-3% at every configuration, and empirical mean stays near 0.
  `x(t)` is confirmed well-behaved and predictable from its two parameters alone -- no runaway or
  non-stationary behavior at any swept combination, including `phi=0.95` (the most persistent).
- **The shipped `economy_shock_threshold` (0.5) is a rare, roughly-3-sigma event at the shipped
  `(phi=0.8, sigma=0.1)`** (steady-state std ~0.167, so 0.5 is ~3 std away) -- zero crossings in a
  121-tick run at every swept `(phi, sigma)` combination is the expected outcome, not a bug (the
  30-year run in this sweep is simply too short to observe a 3-sigma tail event reliably). This is
  exactly why `test_economic_shock_tick_only_journals_above_threshold` (v5 Lot 2's own test suite)
  deliberately uses a tuned, non-shipped `economy_ar1_sigma=0.3` (steady-state std ~0.5, right at
  the threshold) rather than the shipped default -- the same "tuned config to make a rare branch
  observable in a short test" precedent v4 Lot 4's `test_mobilization_moves_and_recovers_legitimacy`
  already established for `base_threshold_dist`. No change to any shipped value is recommended by
  this sweep.
