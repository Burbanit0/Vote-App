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
from typing import Iterable, Mapping

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


def graph_edges(graph: SocialGraph) -> list[tuple[int, int]]:
    """Each tie once, as (low id, high id), in ascending order: the form a checkpoint keeps."""
    return sorted((i, j) for i, neighbours in graph.neighbors.items() for j in neighbours if i < j)


def graph_from_edges(population_size: int, edges: Iterable[tuple[int, int]]) -> SocialGraph:
    """The graph those ties make: every citizen is a node, tied or not."""
    adjacent: dict[int, set[int]] = {i: set() for i in range(population_size)}
    for i, j in edges:
        adjacent[i].add(j)
        adjacent[j].add(i)
    return SocialGraph(neighbors={i: frozenset(ties) for i, ties in adjacent.items()})


def mean_gap(graph: SocialGraph, factors: np.ndarray) -> float:
    """The average distance between the views of two tied citizens (0 for a graph without ties)."""
    ties = graph_edges(graph)
    if not ties:
        return 0.0
    ends = np.array(ties)
    return float(np.linalg.norm(factors[ends[:, 0]] - factors[ends[:, 1]], axis=1).mean())


def rewire(graph: SocialGraph, factors: np.ndarray, share: float, homophily: float, rng: np.random.Generator) -> tuple[SocialGraph, int]:
    """ADR-036: a number of ties drawn from Binomial(ties, `share`) is picked, without replacement and weighted toward
    the ties whose two citizens' views are furthest apart (so `share` sets how many move, `homophily` which ones);
    one end of each, either at random, drops it and ties to someone else, the more likely the nearer that someone's
    views. `homophily` is the strength of both pulls: 0 rewires at random, so it is the control that shows what the
    pull adds. The weights are taken relative to the furthest tie and the nearest candidate, so a large `homophily`
    makes the choice nearly deterministic instead of underflowing. Ties stay symmetric, nobody ties to themselves or
    twice, and the number of ties does not change. Returns the new graph and how many ties moved."""
    ties = graph_edges(graph)
    if not ties or share <= 0:
        return graph, 0
    ends = np.array(ties)
    gap = np.linalg.norm(factors[ends[:, 0]] - factors[ends[:, 1]], axis=1)
    odds = np.exp(homophily * (gap - gap.max()))
    count = min(int(rng.binomial(len(ties), min(share, 1.0))), int(np.count_nonzero(odds)))  # a huge pull leaves few picks
    adjacent = {i: set(ties_of) for i, ties_of in graph.neighbors.items()}
    moved = 0
    for k in rng.choice(len(ties), size=count, replace=False, p=odds / odds.sum()):
        i, j = ties[k]
        keeper, dropper = (i, j) if rng.integers(2) else (j, i)
        taken = adjacent[keeper] | {keeper}
        candidates = np.array([c for c in range(len(factors)) if c not in taken])
        if not len(candidates):
            continue
        away = np.linalg.norm(factors[candidates] - factors[keeper], axis=1)
        near = np.exp(-homophily * (away - away.min()))
        chosen = int(candidates[rng.choice(len(candidates), p=near / near.sum())])
        adjacent[keeper].discard(dropper)
        adjacent[dropper].discard(keeper)
        adjacent[keeper].add(chosen)
        adjacent[chosen].add(keeper)
        moved += 1
    return SocialGraph(neighbors={i: frozenset(ties_of) for i, ties_of in adjacent.items()}), moved
