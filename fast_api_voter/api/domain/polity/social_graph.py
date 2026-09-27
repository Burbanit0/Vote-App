"""
api.domain.polity.social_graph — §5's social network (v6 Lot 2): deterministic
generation of a citizen-keyed social graph, feeding `pressure_action`'s
(dt=10) `neighbors_acting` field and the awakening gate's own contagion term
once a later lot wires both up (§7bis.9f). Nothing in this lot consumes the
graph this module produces -- see run_polity_simulation.py's own wiring.

Exposes a project-owned `SocialGraph` type, never a raw `networkx.Graph`:
networkx is this module's own implementation detail, imported by nothing
else in this package. `SocialGraph.neighbors[cid]` is a plain
`frozenset[int]` of neighbor citizen_ids -- symmetric ("friendship" is
undirected) and never contains `cid` itself (no self-loops, by construction
of every supported topology) -- mirroring `Citizen.petition_signers`'s own
already-established frozenset convention for a citizen-keyed membership set.

Two real, measured properties of the supported topologies, documented here
rather than "fixed" (neither is a bug):

- Erdős–Rényi can produce isolated nodes and a disconnected graph at typical
  densities -- confirmed directly at this project's own shipped scale
  (n=100, mean_degree=8: min degree 0, graph disconnected). A citizen with
  an empty neighbor set is a legitimate, reachable SocialGraph state that
  any future consumer (e.g. a `neighbors_acting` aggregator) must handle
  gracefully, not treat as an error.
- Watts-Strogatz silently floors an odd `mean_degree` to the nearest even
  value (`k=7` behaves like `k=6`) -- networkx's own ring-lattice
  construction needs an even number of lattice neighbors per node. Not
  enforced or corrected at the config level: `_get_positive_int` only
  validates positivity, and nothing in the design doc asks for evenness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import networkx as nx
import numpy as np

from api.domain.polity.config import SocialGraphConfig


@dataclass(frozen=True)
class SocialGraph:
    neighbors: Mapping[int, frozenset[int]]


def generate_social_graph(config: SocialGraphConfig, population_size: int, seed: int) -> SocialGraph:
    """Deterministic: the same (config, population_size, seed) always
    produces the same graph (Lot 2 test contract, mirroring
    generate_population's own). A dedicated np.random.default_rng(seed)
    stream, independent of every other stream in this codebase
    (rupture_rng/events_rng) -- callers only ever invoke this when
    config.enabled is true (see run_polity_simulation.py), so no wasted
    work when the feature is off.

    `topology` is re-checked here even though config.py's own _get_enum
    already makes an invalid YAML value unreachable through the loader --
    the same defensive-re-check precedent as mandate_deviation's own
    deviation_metric guard and generate_population's position_dist/
    priority_dist guards -- raising ValueError, not a bare networkx
    exception, for an unsupported value."""
    rng = np.random.default_rng(seed)
    if config.topology == "watts_strogatz":
        graph = nx.watts_strogatz_graph(n=population_size, k=config.mean_degree, p=config.rewiring_prob, seed=rng)
    elif config.topology == "erdos_renyi":
        p = config.mean_degree / (population_size - 1)
        graph = nx.erdos_renyi_graph(n=population_size, p=p, seed=rng)
    elif config.topology == "barabasi_albert":
        graph = nx.barabasi_albert_graph(n=population_size, m=max(1, config.mean_degree // 2), seed=rng)
    else:
        raise ValueError(f"unsupported social_graph.topology: {config.topology!r}")

    neighbors = {node: frozenset(graph.neighbors(node)) for node in graph.nodes()}
    return SocialGraph(neighbors=neighbors)
