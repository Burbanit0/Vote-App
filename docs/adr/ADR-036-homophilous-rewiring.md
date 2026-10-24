# ADR-036: the social ties can move toward like views

**Status**: Accepted — built, **off everywhere** (plan-scenarios-v1, step 3c, part 2); `social_graph.evolving` is false by default and the scenario profile does not turn it on, because the ten-seed reading below shows it does not move the divergence test the way the plan hoped.
**Date**: 2026-10-24
**Update 2026-10-24**: this ADR's table was measured with the scenario profile's economic voting at 1.0 and the version-2 archetype labels; both have since changed ([ADR-038](ADR-038-economic-voting-calibrated-on-volatility.md): 0.3; [ADR-037](ADR-037-realignment-against-the-populations-spread.md): version 3), so `probe_rewiring.py` no longer reproduces it.
**Context**: The social graph was drawn once and never changed (`social_graph.evolving: true` was rejected at parse time, the design doc's §5 "static or evolving?" point). People in a real society choose who they talk to, and choose people who already think like them, so ties both follow and reinforce the views (homophily; Holme and Newman's coevolving voter model). Step 3c part 2 of plan-scenarios-v1 was "homophilous rewiring once a year", gated on the divergence test and the panel band.

## Decision

**`social_graph.evolving: true`** now parses. It needs `social_graph.enabled` and `dynamics.enabled` (a config rule: the views that ties follow are the dynamics' latent factors). Three settings:

- **`rewire_per_year`** (0 by default): each tick a number of ties drawn from Binomial(ties, `rewire_per_year / ticks_per_year`) is picked, without replacement, weighted toward the ties whose two citizens' views are furthest apart. So the share sets how many ties move (the same at every `homophily`, which is what makes the arms below comparable) and the homophily sets which ones. It goes with `evolving`: a config rule fails a share without `evolving: true` and `evolving: true` without a share, both of which would silently leave the ties fixed.
- **`homophily`** (0 by default): the strength of both pulls below. 0 rewires at random, the control that shows what the pull adds.
- **The move**: a tie's weight to be picked is `exp(homophily * (gap - largest gap))` (the further apart the two citizens' views, the likelier it breaks); one end of it, picked at random, drops it and ties to a citizen they are not yet tied to, chosen with weight `exp(-homophily * (distance - smallest distance))` (the nearer that citizen's views, the likelier; relative to the nearest candidate and the furthest tie, so a very large `homophily` makes the choice nearly deterministic instead of underflowing, and when it leaves fewer ties with any weight than the count drawn, only those move). Distance is Euclidean in the latent factors, the same space the opinion update works in.

Ties stay symmetric, nobody ties to themselves or twice, and **the number of ties never changes** (the degree of the dropper's old partner falls by one and the new partner's rises by one, so the degree distribution can spread: a popular citizen can become more popular, which is a feature of the model, not tuned away). A citizen already tied to everyone cannot move a tie.

**When**: last in the opinion-dynamics phase, after the views moved and after the generation turned over (ADR-035), so a newcomer's circle is the one it was born into and the ties then follow its views.

**The graph is state now.** Until this ADR the graph was a function of `(config, population size, seed)` and was regenerated on resume, never checkpointed. A graph that rewires depends on the views, year after year, so it is not: the ties are kept in the checkpoint (`graph_edges`, each tie once as a sorted `(low, high)` pair) and read back on resume, with the stream. Both keys are written only when `evolving` is on, so a run that keeps its ties checkpoints exactly as before (the explorer fixture's journal and census are byte-identical; its config hash moved with the three new keys). `TickState.graph` holds them; the run loop reads the ties from the state at the top of every tick and rebuilds the edge arrays only when they changed.

**Its own random stream** (`rewiring_rng`, seeded `[seed, 36]`, in the checkpoint, `None` unless evolving), so no other stream moves. Each tick's move is journaled as `ties_rewired` (`moved`, `ties`, `mean_gap`: the average distance between the views of two tied citizens, after the move).

## Measured

Ten seeds, 30 years, 100 citizens, the rule-only twin (`--engine deterministic --profile scenario`: ADR-033 to ADR-035 on), the profile with only the two knobs changed. Not pre-registered: a reading, reproduced by `python scripts/probe_rewiring.py --output-dir <dir>` (`--arm share,homophily` re-runs one row). `tie gap` is the average distance between tied citizens' views at the first and the last rewiring; D1 is the four-year panel stability (ADR-012's band is 0.70 to 0.90), D2 the final spread of positions over the initial one.

| share | homophily | tie gap | D1 | D2 | archetypes (entropy) | divergence | in band | panel stability fails |
|---:|---:|---|---:|---:|---|---|---:|---:|
| 0 | - (fixed graph) | - | 0.901 | 1.83 | realignment 7, alternation 1, churn 1, stasis 1 (1.36 bits) | grows, varied | 0/10 | 6 |
| 0.2 | 0 (random) | 1.77 → 2.67 | 0.899 | 1.76 | realignment 8, alternation 1, stasis 1 (0.92) | grows, not varied | 1/10 | 6 |
| 0.2 | 1 | 1.70 → 0.99 | 0.909 | 1.93 | realignment 7, stasis 2, churn 1 (1.16) | grows, varied | 1/10 | 6 |
| 0.2 | 2 | 1.65 → 0.85 | 0.912 | 2.03 | realignment 9, stasis 1 (0.47) | grows, not varied | 2/10 | 7 |
| 0.2 | 4 | 1.62 → 0.77 | 0.919 | 2.10 | realignment 8, stasis 2 (0.72) | grows, not varied | 1/10 | 9 |
| 0.5 | 2 | 1.49 → 0.77 | 0.913 | 2.01 | realignment 6, alternation 2, stasis 2 (1.37) | grows, varied | 2/10 | 7 |

- **The mechanism does what it says to the ties.** With a pull, the average distance between tied citizens halves over thirty years (1.65 to 0.77–0.99); rewiring at random lets it grow (1.77 to 2.67) because the opinion update pulls tied citizens together and random new ties are between strangers.
- **It does not do what the plan hoped to the runs.** The static graph (first row) already reads 1.36 bits of archetype entropy; only the 0.5/2 arm matches it (1.37), and the other pulled arms read 0.47 to 1.16 bits. Panel stability, which is already near the top of ADR-012's band, rises with the pull (0.909 to 0.919) and fails the band in 7 to 9 seeds against 6, and the spread of positions grows more (D2 1.93 to 2.10 against 1.83) instead of less. That is the expected sign for a coevolving model: like ties cluster, clusters are not diluted by the people they no longer talk to, and each settles. The divergence test and the plausibility band do not move.
- **Read it as a hint, not a result**: the arms share seeds, ten per arm is small, and the entropy of the labels moves by a seed or two. What the table does support is that nothing here is a reason to switch it on.

## Not settled

- **Shipped off.** The scenario profile (`run_polity_flagship.py`) is unchanged. A later step that wants echo chambers as such, a polarised-clusters archetype, or an analysis of who talks to whom, can turn it on with these knobs; it was not worth a profile default for a diversity gate it does not move.
- **Only the ties follow the views, not the other way round.** The confidence bound already makes views follow ties (ADR-012); this adds the reverse. There is no rule that dissolves ties through anger or an election's outcome, nobody leaves a tie out of a scandal, and no newcomer ties are drawn (a replaced citizen keeps the slot's ties and then rewires like anyone).
- **Distance is the latent factors**, not the voter's stated issue positions or party: ties do not follow party membership directly. A citizen's weight to be picked does not depend on their degree, so there is no preferential attachment.
- **Visualisations show the first graph.** `viz_export.export_social_graph` and the engine atlas read the graph from the config, so for a run that rewires they show the ties the run started with; the journal's `ties_rewired` carries the aggregate (`mean_gap`) but not the edges, which are only in the final checkpoint.
- **Cost.** A move scans every citizen for candidates (`O(n)` per moved tie, a few hundred ties a year at population 500): negligible next to a model call, not tuned for populations in the tens of thousands.
- **A checkpoint written before these fields cannot resume after them**: the three keys change `config_hash` for every configuration (loud, at resume time), and the YAML parser requires them, as it does for every other field.
