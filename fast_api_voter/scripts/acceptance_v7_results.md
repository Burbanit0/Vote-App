# v7 acceptance run — coalition negotiation, rounds=1 vs rounds=3 (§3.4 Cas 2)

n=1 per arm (one seed, no Monte Carlo band), the same limit every prior acceptance run in this palier already named. Isolates the one variable §13 assigns v7 --  `parties.coalition_max_negotiation_rounds` -- on top of the `electoral_only` baseline. Not statistically powered on the "does a revision ever happen" question at this scale (~2 formations/arm); see this script's own docstring for what this run can and cannot answer.

| arm | rounds | engine | years | elapsed(s) | replays | mean L (last) | mandate_dev (last) | effective_parties (last) | cohabitation_rate |
|---|---|---|---|---|---|---|---|---|---|
| rounds1 | 1 | deterministic | 8 | 0.8 | 0 | 0.770 | — | 4.596 | 0.000 |
| rounds1 | 1 | llm | 8 | 4038.7 | 0 | 0.710 | 0.000 | 4.596 | 0.667 |
| rounds3 | 3 | deterministic | 8 | 0.8 | 0 | 0.770 | — | 4.596 | 0.000 |
| rounds3 | 3 | llm | 8 | 4068.6 | 0 | 0.710 | 0.000 | 4.596 | 0.667 |

## Coalition negotiation detail (v7's own new fields, not in `RunMetrics`)

| arm | engine | formations | formed | failed | rounds_used distribution | aborted | ticks with a revision |
|---|---|---|---|---|---|---|---|
| rounds1 | deterministic | 2 | 2 | 0 | — | 0 | — |
| rounds1 | llm | 2 | 2 | 0 | 1=2 | 0 | — |
| rounds3 | deterministic | 2 | 2 | 0 | — | 0 | — |
| rounds3 | llm | 2 | 2 | 0 | 2=2 | 0 | — |

## Reading this table

- **Parity check**: with identical seed/config apart from `rounds`, do `rounds1` and `rounds3`'s pre-coalition quantities (effective_parties, mean_legitimacy, mandate_deviation) match up to the point coalition formation could plausibly diverge? Divergence anywhere upstream of the first coalition formation would indicate a bug unrelated to negotiation itself (a config leak), not a real effect of the variable being isolated.
- **rounds_used distribution** on the `rounds1` arm should be `{1: N}` for every N -- the hard cap fires immediately, exactly like the pre-v7 single-shot call (this is the direct, real-data version of Lot 2's own parity tests, which only checked this with fakes).
- **rounds_used distribution** on the `rounds3` arm and **ticks with a revision**: this is the real-data continuation of Lot 3's own open finding (30/30 live spike trials converged in exactly 2 rounds with no revision, including one scenario engineered to force one). A revision or a rounds_used=3 here, on REAL journaled party/seat/platform state rather than a hand-built fixture, would be the first evidence either way -- reported honestly regardless of which way it comes out, and not treated as conclusive at n~2 either way.
