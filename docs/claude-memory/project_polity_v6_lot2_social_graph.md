---
name: project-polity-v6-lot2-social-graph
description: "v6 Lot 2 done (PR #148) — social_graph.py: deterministic graph generation (§5), second lot of v6a"
metadata:
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-16T12:37:25.721Z
---

Polity v6 Lot 2 (`social_graph.py` — deterministic social-graph generation, §5) merged to `develop`
(PR #148, squash commit `a88ce54`). Second lot of [[project_polity_v6_lot1_social_graph_config]]'s
own **v6a** sequence (social graph / contagion half of v6, independent from the deferred sortition
chamber v6b).

**Central judgment call — networkx vs. hand-rolled numpy — resolved by real measurement, not a
guess.** Installed `networkx==3.5` and tested it directly against this project's own RNG
convention before committing to it: `pip show networkx` → zero transitive dependencies;
`np.random.default_rng(seed)` (the project's own `Generator` type) accepted natively as the `seed=`
argument to `watts_strogatz_graph`/`erdos_renyi_graph`/`barabasi_albert_graph`; confirmed
byte-reproducible (same seed → identical edge sets); node IDs are exactly `0..n-1`, matching
`citizen_id` numbering. At the real shipped scale (n=100, mean_degree=8): `watts_strogatz` mean
degree exactly 8.000, connected; `barabasi_albert` mean degree 7.680, min degree 4, never isolated,
connected. This is the same "one pinned dependency, real justification" register the DuckDB storage
lot ([[project_polity_storage_duckdb]]) already used successfully.

**Two real, measured topology properties, documented rather than "fixed" (neither is a bug)**:
- Erdős–Rényi can produce isolated nodes and a disconnected graph at this density — confirmed
  directly at shipped scale (min degree 0, graph disconnected). A citizen with an empty neighbor set
  is a legitimate `SocialGraph` state; flagged for Lot 3's `neighbors_acting` aggregator to handle
  gracefully, not treat as an error.
- Watts-Strogatz silently floors an odd `mean_degree` to the nearest even value (`k=7` behaves like
  `k=6`) — networkx's own ring-lattice construction needs an even per-node degree. Not enforced or
  corrected at the config level.

**`SocialGraph` is a project-owned frozen dataclass** (`neighbors: Mapping[int, frozenset[int]]`) —
`networkx` never leaks past `social_graph.py`; no other module in the package imports it. Mirrors
`Citizen.petition_signers`'s own frozenset convention for a citizen-keyed membership set.
`generate_social_graph(config, population_size, seed) -> SocialGraph` re-checks `topology` at the
call site (raises `ValueError`, not a bare networkx exception), mirroring the project's own
"re-check rather than trust the loader transitively" precedent.

**Mid-implementation correction**: the approved plan called for wiring an unused
`graph: SocialGraph | None` local into `run_polity_simulation.py`'s run-setup block, mirroring how
v5 Lot 2's `shock.py` ([[project_polity_v5_lot2_shock]]) was staged inert-but-wired ahead of its own
consuming lot. Caught during implementation that this doesn't actually fit: `shock.py`'s generators
have real per-tick journal-writing side effects to observe even before their own Lot 3, but the
social graph is a one-time, population-level artifact with **nothing to observe** until Lot 3 reads
it — the unused local trips flake8's `F841` with no real behavior to test against it. Reverted the
`run_polity_simulation.py` edit entirely; Lot 2 is scoped strictly to `social_graph.py` + its own
17 tests, so "existing tests still pass" is unconditional (the file is untouched) rather than
something to newly prove.

**Next: Lot 3** (`neighbors_acting` — the awakening-gate extension removing
`awakening_threshold`'s `NotImplementedError` guard, plus dt=10 wiring: `PressureContext.
neighbors_acting` becoming real, `PressureMotif.FOLLOWING_NEIGHBORS` (306, reserved by Lot 1)
reaching `PressureDecision`'s wire `Literal` and the engine's `validate_pressure_decision`/
`build_pressure_system_prompt`). **Not yet authorized** — needs its own planning pass. Already
flagged open question for that lot: the aggregation must be lagged by one tick, the same structural
reason `street_pressure` is lagged for dt=6 (v4 Lot 6) — `decide_pressure_actions` batches an entire
cohort's decisions in one call, frozen before any land, so a citizen's neighbor's *same-tick*
decision cannot be seen by construction.
