"""ADR-032 option D: a stance taken in the forum is partly kept, because the citizen's anchor follows it."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import generate_population, latent_structure
from api.domain.polity.config import PolityConfigError, SocialGraphConfig, load_config, validate_config
from api.domain.polity.opinion_dynamics import NeighbourEdges, apply_dynamics, current_factors, shift_stance
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.social_graph import generate_social_graph
from api.tests.test_polity_forum import _agent_run_config, _ForumClient, _forum, _moving

N = 40


def _world() -> tuple[list[Any], Any, NeighbourEdges, Any]:
    config = load_config()
    citizens_config = dataclasses.replace(config.citizens, static_population=False)
    citizens = generate_population(citizens_config, N, seed=4)
    structure = latent_structure(citizens_config, N, seed=4)
    for c, row in zip(citizens, structure.anchors):
        c.latent_factors = tuple(float(x) for x in row)
    graph = generate_social_graph(SocialGraphConfig(enabled=True, topology="watts_strogatz", mean_degree=6, rewiring_prob=0.1, evolving=False), N, 4)
    dynamics = dataclasses.replace(config.dynamics, enabled=True, susceptibility=0.9, influence_step=0.1, confidence_bound=1.0)
    return citizens, structure, NeighbourEdges.from_graph(graph), dynamics


# ── config ────────────────────────────────────────────────────────────────

def test_the_setting_ships_neutral_and_needs_dynamics_and_a_susceptibility_below_one() -> None:
    config = load_config()
    assert config.dynamics.anchor_follow == 0.0
    wants = dataclasses.replace(config, dynamics=dataclasses.replace(config.dynamics, anchor_follow=0.5))
    with pytest.raises(PolityConfigError, match="anchor_follow"):
        validate_config(wants)  # no dynamics
    dynamic = dataclasses.replace(wants, dynamics=dataclasses.replace(wants.dynamics, enabled=True))
    with pytest.raises(PolityConfigError, match="susceptibility"):
        validate_config(dynamic)  # at 1 the anchor is never read
    validate_config(dataclasses.replace(dynamic, dynamics=dataclasses.replace(dynamic.dynamics, susceptibility=0.9)))


# ── the shift ─────────────────────────────────────────────────────────────

def test_the_anchor_moves_the_share_of_the_shift_asked_and_nothing_else_changes() -> None:
    citizens, structure, _, _ = _world()
    plain, followed = citizens[0], citizens[1]
    shift_stance(plain, structure, 3, 0.25)
    assert plain.anchor_factors is None  # off: the citizen keeps the structure's anchor
    twin = dataclasses.replace(citizens[1])
    shift_stance(twin, structure, 3, 0.25, 0.4)
    shift_stance(followed, structure, 3, 0.25)
    assert twin.latent_factors == followed.latent_factors and twin.issue_positions == followed.issue_positions  # the views move as before
    step = np.array(followed.latent_factors) - structure.anchors[1]
    assert np.allclose(twin.anchor_factors, structure.anchors[1] + 0.4 * step)


def test_a_citizen_with_their_own_anchor_moves_it_from_there() -> None:
    citizens, structure, _, _ = _world()
    newcomer = citizens[2]
    newcomer.latent_factors = newcomer.anchor_factors = (1.0, -1.0)
    before = np.array(newcomer.latent_factors)
    shift_stance(newcomer, structure, 3, -0.25, 1.0)
    step = np.array(newcomer.latent_factors) - before
    assert np.allclose(newcomer.anchor_factors, np.array([1.0, -1.0]) + step)  # follow 1: the anchor goes where the view went


def _kept_after_a_year(follow: float) -> float:
    """How much of a shift applied to everyone is still there four ticks later, along the shift."""
    citizens, structure, edges, dynamics = _world()
    start = current_factors(citizens, structure)
    for c in citizens:
        shift_stance(c, structure, 3, 0.25, follow)
    shifted = current_factors(citizens, structure)
    direction = (shifted - start).mean(axis=0)
    for _ in range(4):
        apply_dynamics(citizens, structure, edges, dataclasses.replace(dynamics, anchor_follow=follow), np.random.default_rng(1))
    after = current_factors(citizens, structure)
    return float(((after - start).mean(axis=0) @ direction) / (direction @ direction))


def test_following_anchors_keep_more_of_a_shift_after_a_year() -> None:
    assert _kept_after_a_year(0.5) > _kept_after_a_year(0.0) + 0.1
    assert _kept_after_a_year(1.0) > _kept_after_a_year(0.5)


# ── in a run ──────────────────────────────────────────────────────────────

def _run_config(tmp_path: Path, follow: float) -> Any:
    config = _moving(_forum(_agent_run_config(tmp_path)))
    return dataclasses.replace(config, dynamics=dataclasses.replace(config.dynamics, susceptibility=0.9, anchor_follow=follow))


def test_a_run_whose_citizens_change_their_minds_moves_their_anchors_and_checkpoints_them(tmp_path: Path) -> None:
    journal = run_simulation(_run_config(tmp_path / "on", 0.5), run_id="mind", llm_client=_ForumClient(shift=True))
    citizens = load_checkpoint(journal.parent / "checkpoint.json").state.citizens
    posts = [json.loads(line) for line in journal.read_text().splitlines() if '"forum_post"' in line]
    shifters = {e["citizen_id"] for e in posts if e["payload"]["shift_logit"] != 0}
    assert shifters
    assert {c.citizen_id for c in citizens if c.anchor_factors is not None} == shifters  # exactly those who changed their mind

    off = run_simulation(_run_config(tmp_path / "off", 0.0), run_id="mind", llm_client=_ForumClient(shift=True))
    assert all(c.anchor_factors is None for c in load_checkpoint(off.parent / "checkpoint.json").state.citizens)
