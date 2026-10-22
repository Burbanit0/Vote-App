"""ADR-035: cohort replacement -- generations turn over in place."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.checkpoint import _citizen_from_dict, _citizen_to_dict, load_checkpoint
from api.domain.polity.citizen import ACTIVE, Citizen, Office, Role, generate_population, latent_structure
from api.domain.polity.config import PolityConfig, PolityConfigError, SocialGraphConfig, load_config, validate_config
from api.domain.polity.demography import replaceable, replace_generation
from api.domain.polity.opinion_dynamics import NeighbourEdges, apply_dynamics, current_factors
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.social_graph import generate_social_graph
from api.tests.test_polity_run_simulation import _SimulatedCrash

N = 16


def _world(replacement: float = 4.0, spread: float = 0.0) -> tuple[list[Citizen], Any, Any, list[Party], Any]:
    """A 16-citizen population on a small-world graph, the latent structure it came from and three parties; the rate is
    in replacements per year, so 4 with four ticks a year is a chance of 1 per tick."""
    base = load_config()
    citizens_config = dataclasses.replace(base.citizens, static_population=False, replacement_per_year=replacement, newcomer_spread=spread)
    citizens = generate_population(citizens_config, N, seed=5)
    structure = latent_structure(citizens_config, N, seed=5)
    for c, row in zip(citizens, structure.anchors):
        c.latent_factors = tuple(float(x) for x in row)
    graph = generate_social_graph(SocialGraphConfig(enabled=True, topology="watts_strogatz", mean_degree=4, rewiring_prob=0.1, evolving=False), N, 5)
    parties = [Party(party_id=i, platform=citizens[i].issue_positions) for i in (0, 1, 2)]
    return citizens, structure, graph, parties, citizens_config


# ── config ────────────────────────────────────────────────────────────────

def test_the_replacement_settings_ship_neutral_and_need_dynamics_and_a_living_population() -> None:
    config = load_config()
    assert config.citizens.replacement_per_year == 0.0 and config.citizens.static_population
    wants = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, replacement_per_year=0.03, static_population=False))
    with pytest.raises(PolityConfigError, match="dynamics.enabled"):
        validate_config(wants)  # no dynamics: no latent factors to draw a newcomer from
    with pytest.raises(PolityConfigError, match="static_population"):
        validate_config(dataclasses.replace(wants, citizens=dataclasses.replace(wants.citizens, static_population=True)))


# ── who can be replaced ───────────────────────────────────────────────────

def test_office_holders_candidates_and_the_sitting_chamber_are_exempt_a_former_president_is_not() -> None:
    plain = Citizen(citizen_id=0, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.3, ambition_score=0.1)
    assert replaceable(plain)
    assert not replaceable(dataclasses.replace(plain, office=Office.PRESIDENT, role=Role.ELECTED))
    assert not replaceable(dataclasses.replace(plain, role=Role.CANDIDATE))
    assert not replaceable(dataclasses.replace(plain, sortition_seat_until_tick=20))
    assert replaceable(dataclasses.replace(plain, mandates_served=2))  # retired: an elector with a record


# ── replacing a generation ────────────────────────────────────────────────

def test_a_replaced_slot_keeps_its_id_and_ties_and_gets_a_new_person_with_their_own_anchor() -> None:
    citizens, structure, graph, parties, config = _world()
    holder, seated = citizens[3], citizens[7]
    holder.office, holder.role = Office.PRESIDENT, Role.ELECTED
    seated.sortition_seat_until_tick = 99
    old = {c.citizen_id: c for c in citizens}
    for c in citizens:  # a tracked run: emotions and engagement exist
        c.anger, c.anxiety, c.enthusiasm, c.engagement = 0.9, 0.8, 0.1, "exited"
    replaced = replace_generation(citizens, structure, graph, parties, config, 4, np.random.default_rng(0))
    assert sorted(r.citizen_id for r in replaced) == [i for i in range(N) if i not in (3, 7)]  # everyone but the two exempt
    assert citizens[3] is holder and citizens[7] is seated  # untouched, the same objects
    assert [c.citizen_id for c in citizens] == list(range(N))  # ids are still range(n), which the dynamics require
    for r in replaced:
        new = citizens[r.citizen_id]
        assert new is not old[r.citizen_id] and new.anchor_factors == new.latent_factors
        assert (new.anger, new.anxiety, new.enthusiasm, new.engagement) == (0.0, 0.0, 0.0, ACTIVE)  # fresh
        assert new.role == Role.ELECTOR and new.office == Office.NONE and new.mandates_served == 0
        assert new.issue_positions == tuple(float(x) for x in structure.positions(np.array([new.latent_factors]), [r.citizen_id])[0])
        assert new.party_affiliation == r.party_id == min(parties, key=lambda p: (np.linalg.norm(np.subtract(new.issue_positions, p.platform)), p.party_id)).party_id
        assert abs(sum(new.issue_priorities) - 1.0) < 1e-9 and new.base_threshold > 0.0


def test_a_newcomer_takes_the_average_views_of_the_circle_that_stays_plus_noise() -> None:
    citizens, structure, graph, parties, config = _world(replacement=0.4)  # chance 0.1 a tick: a few leave, most stay
    before = current_factors(citizens, structure)
    rng = np.random.default_rng(11)
    replaced = replace_generation(citizens, structure, graph, parties, dataclasses.replace(config, newcomer_spread=0.0), 4, rng)
    assert replaced, "seed 11 should replace somebody"
    leaving = {r.citizen_id for r in replaced}
    for r in replaced:
        circle = sorted(j for j in graph.neighbors[r.citizen_id] if j not in leaving)
        assert r.circle == len(circle)
        expected = before[circle].mean(axis=0) if circle else before.mean(axis=0)  # a slot with no tie left: the whole population
        assert np.allclose(citizens[r.citizen_id].latent_factors, expected)


def test_the_stream_is_drawn_once_per_slot_whoever_is_eligible() -> None:
    a, structure, graph, parties, config = _world(replacement=1e-9)
    b = [dataclasses.replace(c) for c in a]
    b[0].office, b[0].role = Office.PRESIDENT, Role.ELECTED
    for c in b[1:4]:
        c.sortition_seat_until_tick = 9
    rng_a, rng_b = np.random.default_rng(3), np.random.default_rng(3)
    assert replace_generation(a, structure, graph, parties, config, 4, rng_a) == [] == replace_generation(b, structure, graph, parties, config, 4, rng_b)
    assert rng_a.bit_generator.state == rng_b.bit_generator.state  # the next tick's draws do not depend on who held office


def test_no_replacement_at_a_rate_of_zero_draws_nothing_that_matters() -> None:
    citizens, structure, graph, parties, config = _world(replacement=0.0)
    assert replace_generation(citizens, structure, graph, parties, config, 4, np.random.default_rng(0)) == []


# ── anchors ───────────────────────────────────────────────────────────────

def test_opinion_dynamics_draw_a_newcomer_back_to_their_own_anchor_not_the_slots() -> None:
    citizens, structure, _, _, config = _world()
    edges = NeighbourEdges.from_graph(None)
    pull = dataclasses.replace(load_config().dynamics, enabled=True, susceptibility=0.5, influence_step=0.0, drift_std=0.0)
    own = (3.0, -3.0)
    citizens[2].anchor_factors = own
    citizens[2].latent_factors = (0.0, 0.0)
    apply_dynamics(citizens, structure, edges, pull, np.random.default_rng(0))
    moved = np.array(citizens[2].latent_factors)
    assert np.allclose(moved, 0.5 * np.array(own))  # (1 - s) own anchor + s x where they were
    other = np.array(citizens[5].latent_factors)
    assert np.allclose(other, structure.anchors[5])  # an ordinary citizen is still drawn to the structure's row


def test_a_newcomers_anchor_survives_the_checkpoint_and_an_ordinary_citizen_writes_none() -> None:
    citizens, structure, graph, parties, config = _world(replacement=4.0)
    replace_generation(citizens, structure, graph, parties, config, 4, np.random.default_rng(1))
    back = _citizen_from_dict(json.loads(json.dumps(_citizen_to_dict(citizens[0]))))
    assert back == citizens[0] and isinstance(back.anchor_factors, tuple)
    ordinary = Citizen(citizen_id=1, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.3, ambition_score=0.1)
    assert "anchor_factors" not in _citizen_to_dict(ordinary)


# ── in a run ──────────────────────────────────────────────────────────────

def _twin(flagship: Any, output_dir: Path, replacement: float, years: int = 3) -> PolityConfig:
    config = flagship._flagship_config(
        engine="deterministic", years=years, population=60, seats=9, seed=2, output_dir=output_dir,
        max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    return dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, static_population=replacement == 0, replacement_per_year=replacement))


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_run_replaces_about_the_expected_share_never_an_office_holder_and_journals_each_one(flagship: Any, tmp_path: Path) -> None:
    journal = run_simulation(_twin(flagship, tmp_path, 0.2), run_id="run")
    events = _lines(journal)
    replaced = [e for e in events if e["event_type"] == "citizen_replaced"]
    expected = 60 * 0.2 * 3
    assert 0.5 * expected < len(replaced) < 1.6 * expected
    holders = [(e["tick"], e["citizen_id"]) for e in events if e["event_type"] == "elected"]  # a president serves from their election
    for event in replaced:
        assert not any(tick <= event["tick"] and who == event["citizen_id"] and event["tick"] < tick + 16 for tick, who in holders)  # not while in office
    checkpoint = load_checkpoint(journal.parent / "checkpoint.json").state
    assert [c.citizen_id for c in checkpoint.citizens] == list(range(60))
    assert 0 < sum(c.anchor_factors is not None for c in checkpoint.citizens) <= len(replaced)
    assert json.loads((journal.parent / "checkpoint.json").read_text())["demography_rng_state"]


def test_a_run_with_no_replacement_writes_none_of_it(flagship: Any, tmp_path: Path) -> None:
    journal = run_simulation(_twin(flagship, tmp_path, 0.0), run_id="run")
    assert not [e for e in _lines(journal) if e["event_type"] == "citizen_replaced"]
    checkpoint = json.loads((journal.parent / "checkpoint.json").read_text())
    assert "demography_rng_state" not in checkpoint and not any("anchor_factors" in c for c in checkpoint["citizens"])


def test_a_run_with_replacement_resumed_after_a_crash_matches_an_uninterrupted_one(flagship: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import api.domain.polity.run_polity_simulation as engine

    uninterrupted = run_simulation(_twin(flagship, tmp_path / "a", 0.3), run_id="run")
    real_phase = engine._run_accountability_phase

    def crash_at_tick_6(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 6:
            raise _SimulatedCrash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash_at_tick_6)
    with pytest.raises(_SimulatedCrash):
        run_simulation(_twin(flagship, tmp_path / "b", 0.3), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_twin(flagship, tmp_path / "b", 0.3), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()
    assert (resumed.parent / "snapshots.jsonl").read_bytes() == (uninterrupted.parent / "snapshots.jsonl").read_bytes()
