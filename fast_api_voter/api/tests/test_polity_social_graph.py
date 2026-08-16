"""social_graph.py — §5's deterministic social-graph generation (v6 Lot 2).

Contract: the same (config, population_size, seed) always produces the same
graph (mirrors generate_population's own reproducibility contract). Nothing
in this project consumes SocialGraph yet -- that's Lot 3's job.
"""
import pytest

from api.domain.polity.config import SocialGraphConfig
from api.domain.polity.social_graph import generate_social_graph

_POPULATION_SIZE = 100
_SEED = 42


def _config(**overrides) -> SocialGraphConfig:
    base = SocialGraphConfig(enabled=True, topology="watts_strogatz", mean_degree=8, rewiring_prob=0.1, evolving=False)
    return SocialGraphConfig(**{**base.__dict__, **overrides})


@pytest.mark.parametrize("topology", ["watts_strogatz", "erdos_renyi", "barabasi_albert"])
def test_generate_social_graph_is_deterministic(topology):
    config = _config(topology=topology)
    graph_a = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    graph_b = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    assert dict(graph_a.neighbors) == dict(graph_b.neighbors)


@pytest.mark.parametrize("topology", ["watts_strogatz", "erdos_renyi", "barabasi_albert"])
def test_generate_social_graph_node_keys_match_the_citizen_id_range(topology):
    config = _config(topology=topology)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    assert set(graph.neighbors.keys()) == set(range(_POPULATION_SIZE))


@pytest.mark.parametrize("topology", ["watts_strogatz", "erdos_renyi", "barabasi_albert"])
def test_generate_social_graph_has_no_self_loops(topology):
    config = _config(topology=topology)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    for cid, neighbors in graph.neighbors.items():
        assert cid not in neighbors


@pytest.mark.parametrize("topology", ["watts_strogatz", "erdos_renyi", "barabasi_albert"])
def test_generate_social_graph_neighbor_relation_is_symmetric(topology):
    config = _config(topology=topology)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    for cid, neighbors in graph.neighbors.items():
        for neighbor in neighbors:
            assert cid in graph.neighbors[neighbor]


def test_watts_strogatz_at_shipped_defaults_has_exact_mean_degree_eight():
    # Hand-verified during this lot's own planning pass: n=100, k=8, p=0.1
    # produces mean degree EXACTLY 8.0 (k is already even, no flooring).
    config = _config(topology="watts_strogatz", mean_degree=8, rewiring_prob=0.1)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    total_degree = sum(len(neighbors) for neighbors in graph.neighbors.values())
    assert total_degree / _POPULATION_SIZE == 8.0


def test_watts_strogatz_floors_an_odd_mean_degree_to_the_nearest_even_value():
    # networkx's own ring-lattice construction needs an even lattice degree
    # per node -- k=7 silently behaves like k=6. Documented, not "fixed":
    # pinned so a future networkx upgrade that changes this is caught.
    config = _config(topology="watts_strogatz", mean_degree=7, rewiring_prob=0.1)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    total_degree = sum(len(neighbors) for neighbors in graph.neighbors.values())
    assert total_degree / _POPULATION_SIZE == 6.0


def test_erdos_renyi_at_shipped_scale_can_produce_an_isolated_node():
    # A real, documented property of Erdős–Rényi at this density -- not a
    # bug. A future neighbors_acting aggregator must handle an empty
    # neighbor set gracefully, never treat it as an error.
    config = _config(topology="erdos_renyi", mean_degree=8)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    assert any(len(neighbors) == 0 for neighbors in graph.neighbors.values())


def test_barabasi_albert_never_produces_an_isolated_node():
    # Every node attaches with >= m edges by construction (m = mean_degree
    # // 2), unlike Erdős–Rényi -- contrast with the test above.
    config = _config(topology="barabasi_albert", mean_degree=8)
    graph = generate_social_graph(config, _POPULATION_SIZE, _SEED)
    assert all(len(neighbors) > 0 for neighbors in graph.neighbors.values())


def test_unsupported_topology_raises_a_clear_value_error():
    # Defensive re-check: config.py's own _get_enum already makes this
    # unreachable through the loader, but generate_social_graph must stay
    # correct when called directly, the same precedent every other
    # deterministic primitive in this project already follows.
    config = _config(topology="random_forest")
    with pytest.raises(ValueError, match="random_forest"):
        generate_social_graph(config, _POPULATION_SIZE, _SEED)
