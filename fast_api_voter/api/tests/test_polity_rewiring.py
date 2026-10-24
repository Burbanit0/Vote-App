"""ADR-036: homophilous rewiring -- the social ties move toward like views."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.config import PolityConfig, PolityConfigError, SocialGraphConfig, load_config, validate_config
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.social_graph import generate_social_graph, graph_edges, graph_from_edges, mean_gap, rewire
from api.tests.test_polity_run_simulation import _SimulatedCrash

N = 60


def _ring() -> tuple[Any, np.ndarray]:
    """60 citizens on a small-world graph, their views spread along a line so that distance is easy to read."""
    graph = generate_social_graph(SocialGraphConfig(enabled=True, topology="watts_strogatz", mean_degree=6, rewiring_prob=0.3, evolving=False), N, 3)
    return graph, np.column_stack([np.linspace(0.0, 4.0, N), np.zeros(N)])


# ── config ────────────────────────────────────────────────────────────────

def test_the_rewiring_settings_ship_neutral_and_need_a_graph_and_dynamics() -> None:
    config = load_config()
    assert not config.social_graph.evolving and config.social_graph.rewire_per_year == 0.0 and config.social_graph.homophily == 0.0
    wants = dataclasses.replace(config, social_graph=dataclasses.replace(config.social_graph, evolving=True))
    with pytest.raises(PolityConfigError, match="social_graph.enabled"):
        validate_config(wants)
    with pytest.raises(PolityConfigError, match="dynamics.enabled"):
        validate_config(dataclasses.replace(wants, social_graph=dataclasses.replace(wants.social_graph, enabled=True)))
    validate_config(dataclasses.replace(
        wants, social_graph=dataclasses.replace(wants.social_graph, enabled=True), dynamics=dataclasses.replace(wants.dynamics, enabled=True),
    ))


# ── the move itself ───────────────────────────────────────────────────────

def test_rewiring_keeps_the_graph_a_graph_and_the_number_of_ties() -> None:
    graph, factors = _ring()
    after, moved = rewire(graph, factors, 0.5, 1.0, np.random.default_rng(1))
    assert 0 < moved <= len(graph_edges(graph))
    assert len(graph_edges(after)) == len(graph_edges(graph))
    for i, ties in after.neighbors.items():
        assert i not in ties  # nobody ties to themselves
        assert all(i in after.neighbors[j] for j in ties)  # a tie is mutual
    assert set(after.neighbors) == set(graph.neighbors)


def test_a_share_of_zero_moves_nothing_and_the_same_seed_moves_the_same_ties() -> None:
    graph, factors = _ring()
    same, moved = rewire(graph, factors, 0.0, 1.0, np.random.default_rng(1))
    assert same is graph and moved == 0
    a, _ = rewire(graph, factors, 0.4, 1.0, np.random.default_rng(7))
    b, _ = rewire(graph, factors, 0.4, 1.0, np.random.default_rng(7))
    assert graph_edges(a) == graph_edges(b) != graph_edges(graph)


def test_the_pull_brings_tied_citizens_closer_and_rewiring_at_random_does_not() -> None:
    graph, factors = _ring()
    pulled, random_ = graph, graph
    for year in range(6):
        pulled, _ = rewire(pulled, factors, 0.3, 4.0, np.random.default_rng(year))
        random_, _ = rewire(random_, factors, 0.3, 0.0, np.random.default_rng(year))
    assert mean_gap(pulled, factors) < 0.5 * mean_gap(graph, factors)  # like attracts like
    assert mean_gap(random_, factors) > mean_gap(pulled, factors)  # the control shows what the pull adds


def test_a_citizen_tied_to_everyone_cannot_move_their_ties() -> None:
    full = graph_from_edges(4, [(i, j) for i in range(4) for j in range(i + 1, 4)])
    after, moved = rewire(full, np.arange(8.0).reshape(4, 2), 1.0, 1.0, np.random.default_rng(1))
    assert moved == 0 and graph_edges(after) == graph_edges(full)


def test_the_gap_between_tied_citizens_is_their_mean_distance_and_zero_without_ties() -> None:
    line = graph_from_edges(3, [(0, 1), (1, 2)])
    assert mean_gap(line, np.array([[0.0, 0.0], [3.0, 4.0], [3.0, 5.0]])) == pytest.approx(3.0)  # (5 + 1) / 2
    assert mean_gap(graph_from_edges(3, []), np.zeros((3, 2))) == 0.0


def test_the_ties_survive_the_checkpoint_form() -> None:
    graph, _ = _ring()
    assert graph_from_edges(N, graph_edges(graph)).neighbors == graph.neighbors


# ── in a run ──────────────────────────────────────────────────────────────

def _twin(flagship: Any, output_dir: Path, rewire_per_year: float, years: int = 3) -> PolityConfig:
    config = flagship._flagship_config(
        engine="deterministic", years=years, population=60, seats=9, seed=2, output_dir=output_dir,
        max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    graph = dataclasses.replace(config.social_graph, evolving=rewire_per_year > 0, rewire_per_year=rewire_per_year, homophily=3.0)
    return dataclasses.replace(config, social_graph=graph)


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_run_rewires_journals_each_move_and_keeps_the_ties_in_its_checkpoint(flagship: Any, tmp_path: Path) -> None:
    journal = run_simulation(_twin(flagship, tmp_path, 0.5), run_id="run")
    moves = [e for e in _lines(journal) if e["event_type"] == "ties_rewired"]
    assert len(moves) == 3 * 4 + 1  # one per tick, from tick 0 through the last of the three years
    assert sum(m["payload"]["moved"] for m in moves) > 0
    assert len({m["payload"]["ties"] for m in moves}) == 1  # moving a tie never creates or removes one
    assert moves[-1]["payload"]["mean_gap"] < moves[0]["payload"]["mean_gap"]  # ties settle among like views
    stored = json.loads((journal.parent / "checkpoint.json").read_text())
    assert stored["rewiring_rng_state"] and len(stored["graph_edges"]) == moves[0]["payload"]["ties"]
    assert graph_edges(load_checkpoint(journal.parent / "checkpoint.json").state.graph) == [tuple(e) for e in stored["graph_edges"]]


def test_a_run_that_keeps_its_ties_writes_none_of_it(flagship: Any, tmp_path: Path) -> None:
    journal = run_simulation(_twin(flagship, tmp_path, 0.0), run_id="run")
    assert not [e for e in _lines(journal) if e["event_type"] == "ties_rewired"]
    stored = json.loads((journal.parent / "checkpoint.json").read_text())
    assert "rewiring_rng_state" not in stored and "graph_edges" not in stored


def test_a_run_that_rewires_resumed_after_a_crash_matches_an_uninterrupted_one(flagship: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import api.domain.polity.run_polity_simulation as engine

    uninterrupted = run_simulation(_twin(flagship, tmp_path / "a", 0.5), run_id="run")
    real_phase = engine._run_accountability_phase

    def crash_at_tick_6(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 6:
            raise _SimulatedCrash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash_at_tick_6)
    with pytest.raises(_SimulatedCrash):
        run_simulation(_twin(flagship, tmp_path / "b", 0.5), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_twin(flagship, tmp_path / "b", 0.5), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()
    assert (resumed.parent / "checkpoint.json").read_bytes() == (uninterrupted.parent / "checkpoint.json").read_bytes()
