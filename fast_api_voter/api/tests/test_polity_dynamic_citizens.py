"""S4.3: dynamic citizens (docs/adr/ADR-012-dynamic-citizens.md) -- Friedkin-Johnsen with
bounded confidence on the latent factors, and anger, anxiety and enthusiasm acting on the
awakening gate and the pressure rule. The static population stays the control arm."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import api.domain.polity.run_polity_simulation as engine
from api.domain.polity.accountability import awakening_threshold, select_consulted
from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import Citizen, generate_population, latent_structure
from api.domain.polity.codebook import PressureAct
from api.domain.polity.config import (
    DynamicsConfig,
    EmotionsConfig,
    PolityConfig,
    PolityConfigError,
    PressureMenuConfig,
    load_config,
    validate_config,
)
from api.domain.polity.emotions import Appraisal, appraise, awakening_pull, feel, tolerance_scale
from api.domain.polity.llm_behavior_engine import (
    PRESSURE_EMOTION_SIGNALS,
    PRESSURE_THRESHOLD_SIGNAL,
    PressureContext,
    _deterministic_pressure_fallback,
    decide_pressure_actions,
    pressure_shipped_signal_values,
    pressure_signals,
)
from api.domain.polity.opinion_dynamics import NeighbourEdges, apply_dynamics, update_latent_factors
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import deterministic_pressure_action
from api.domain.polity.social_graph import SocialGraph
from api.tests.polity_golden import golden_config
from api.tests.test_polity_run_simulation import _SimulatedCrash

NEUTRAL = DynamicsConfig(enabled=True, susceptibility=1.0, influence_step=0.0, confidence_bound=1.0, drift_std=0.0)
QUIET = EmotionsConfig(enabled=True, decay=0.7, awakening_anger=0.0, awakening_anxiety=0.0, awakening_enthusiasm=0.0,
                       mobilization_anger=0.0)
MOVING = DynamicsConfig(enabled=True, susceptibility=0.9, influence_step=0.3, confidence_bound=1.5, drift_std=0.05)
FELT = EmotionsConfig(enabled=True, decay=0.5, awakening_anger=0.6, awakening_anxiety=0.3, awakening_enthusiasm=0.2,
                      mobilization_anger=0.5)


def _graph(ties: list[tuple[int, int]], n: int) -> SocialGraph:
    neighbours: dict[int, set[int]] = {cid: set() for cid in range(n)}
    for a, b in ties:
        if a != b:
            neighbours[a].add(b)
            neighbours[b].add(a)
    return SocialGraph(neighbors={cid: frozenset(ids) for cid, ids in neighbours.items()})


def _citizen(cid: int, positions: tuple[float, ...] = (0.5,), threshold: float = 0.5, **overrides: Any) -> Citizen:
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=(1.0,) * len(positions),
                   blank_threshold=threshold, ambition_score=0.5, **overrides)


# ── config ────────────────────────────────────────────────────────────────

def test_the_shipped_config_is_the_static_control_arm_with_neutral_settings() -> None:
    config = load_config()
    assert config.dynamics == dataclasses.replace(NEUTRAL, enabled=False)
    assert config.emotions == dataclasses.replace(QUIET, enabled=False)


def test_the_rules_refuse_dynamics_without_a_latent_space_or_a_graph_and_emotions_without_awakening() -> None:
    config = load_config()
    dynamic = dataclasses.replace(config, dynamics=NEUTRAL)
    validate_config(dynamic)
    uniform = dataclasses.replace(dynamic, citizens=dataclasses.replace(config.citizens, position_dist="uniform"))
    with pytest.raises(PolityConfigError, match="factor_structure"):
        validate_config(uniform)
    with pytest.raises(PolityConfigError, match="social_graph.enabled"):
        validate_config(dataclasses.replace(dynamic, dynamics=MOVING))
    validate_config(dataclasses.replace(dynamic, dynamics=MOVING, social_graph=dataclasses.replace(config.social_graph, enabled=True)))
    with pytest.raises(PolityConfigError, match="awakening.enabled"):
        validate_config(dataclasses.replace(config, emotions=QUIET))


# ── the latent structure ──────────────────────────────────────────────────

def test_the_latent_structure_redrawn_from_the_seed_rebuilds_the_generated_positions_exactly() -> None:
    citizens_config = load_config().citizens
    population = generate_population(citizens_config, 30, seed=7)
    structure = latent_structure(citizens_config, 30, seed=7)
    assert [c.issue_positions for c in population] == [tuple(float(x) for x in row) for row in structure.positions(structure.anchors)]
    with pytest.raises(ValueError, match="no latent structure"):
        latent_structure(dataclasses.replace(citizens_config, position_dist="uniform"), 30, seed=7)


# ── the update ────────────────────────────────────────────────────────────

@st.composite
def _worlds(draw: st.DrawFn) -> tuple[np.ndarray, np.ndarray, NeighbourEdges, float, float, float]:
    n = draw(st.integers(1, 8))
    coordinate = st.floats(-3.0, 3.0, allow_nan=False)
    factors = np.array(draw(st.lists(st.tuples(coordinate, coordinate), min_size=n, max_size=n)), dtype=float)
    anchors = np.array(draw(st.lists(st.tuples(coordinate, coordinate), min_size=n, max_size=n)), dtype=float)
    ties = draw(st.lists(st.tuples(st.integers(0, n - 1), st.integers(0, n - 1)), max_size=12))
    unit = st.floats(0.0, 1.0)
    return factors, anchors, NeighbourEdges.from_graph(_graph(ties, n)), draw(unit), draw(unit), draw(st.floats(0.0, 5.0))


@settings(max_examples=300, deadline=None)
@given(_worlds())
def test_at_the_neutral_settings_nobody_moves_at_all(world: tuple) -> None:
    factors, anchors, edges, _, _, bound = world
    step = update_latent_factors(factors, anchors, edges, dataclasses.replace(NEUTRAL, confidence_bound=bound), np.random.default_rng(0))
    assert np.array_equal(step.factors, factors)
    assert step.mean_shift == 0.0 and step.max_shift == 0.0


@settings(max_examples=300, deadline=None)
@given(_worlds())
def test_without_drift_every_citizen_stays_within_the_span_of_where_citizens_are_and_started(world: tuple) -> None:
    factors, anchors, edges, susceptibility, step_size, bound = world
    config = DynamicsConfig(enabled=True, susceptibility=susceptibility, influence_step=step_size, confidence_bound=bound, drift_std=0.0)
    moved = update_latent_factors(factors, anchors, edges, config, np.random.default_rng(0)).factors
    known = np.vstack([factors, anchors])
    assert (moved >= known.min(axis=0) - 1e-9).all() and (moved <= known.max(axis=0) + 1e-9).all()


def test_one_update_by_hand_bounded_confidence_excludes_the_far_neighbour() -> None:
    # A path 0 - 1 - 2. Citizen 1 is within the bound of 0 (distance 1) but not of 2 (distance
    # 2); citizen 2 has nobody within it, so only its anchor pulls it.
    factors = np.array([[0.0, 0.0], [1.0, 0.0], [3.0, 0.0]])
    anchors = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 0.0]])
    config = DynamicsConfig(enabled=True, susceptibility=0.5, influence_step=0.5, confidence_bound=1.5, drift_std=0.0)
    step = update_latent_factors(factors, anchors, NeighbourEdges.from_graph(_graph([(0, 1), (1, 2)], 3)), config, np.random.default_rng(0))
    np.testing.assert_allclose(step.factors, [[0.25, 0.0], [1.25, 0.0], [2.5, 0.0]])
    assert (step.influenced, step.max_shift) == (2, pytest.approx(0.5))
    assert step.mean_shift == pytest.approx(1 / 3)


def test_the_stream_advances_the_same_whatever_the_drift() -> None:
    factors, anchors = np.zeros((4, 2)), np.zeros((4, 2))
    edges = NeighbourEdges.from_graph(None)
    quiet, noisy = np.random.default_rng(3), np.random.default_rng(3)
    update_latent_factors(factors, anchors, edges, NEUTRAL, quiet)
    drifted = update_latent_factors(factors, anchors, edges, dataclasses.replace(NEUTRAL, drift_std=0.5), noisy)
    assert drifted.mean_shift > 0 and quiet.random() == noisy.random()


def test_apply_dynamics_writes_factors_and_the_positions_they_imply_and_needs_the_whole_ordered_population() -> None:
    citizens_config = load_config().citizens
    population = generate_population(citizens_config, 12, seed=5)
    structure = latent_structure(citizens_config, 12, seed=5)
    edges = NeighbourEdges.from_graph(_graph([(i, (i + 1) % 12) for i in range(12)], 12))
    apply_dynamics(population, structure, edges, MOVING, np.random.default_rng(5))
    factors = np.array([c.latent_factors for c in population])
    assert not np.array_equal(factors, structure.anchors)
    assert [c.issue_positions for c in population] == [tuple(float(x) for x in row) for row in structure.positions(factors)]
    with pytest.raises(ValueError, match="ordered by citizen_id"):
        apply_dynamics(population[::-1], structure, edges, MOVING, np.random.default_rng(5))


# ── emotions ──────────────────────────────────────────────────────────────

def test_appraisal_reads_the_president_against_the_tolerance_and_the_economy_against_the_shock_threshold() -> None:
    assert appraise(None, 0.5, 0.0, 0.5) == Appraisal(anger=0.0, anxiety=0.0, enthusiasm=0.0)
    assert appraise(0.25, 0.5, -0.25, 0.5) == Appraisal(anger=0.0, anxiety=0.5, enthusiasm=0.5)
    assert appraise(0.75, 0.5, 2.0, 0.5) == Appraisal(anger=0.5, anxiety=1.0, enthusiasm=0.0)
    assert appraise(0.1, 0.0, 0.1, 0.0) == Appraisal(anger=1.0, anxiety=1.0, enthusiasm=0.0)
    assert appraise(0.0, 0.0, 0.0, 0.0) == Appraisal(anger=0.0, anxiety=0.0, enthusiasm=1.0)


def test_emotions_start_at_zero_and_move_toward_the_appraisal() -> None:
    citizen = _citizen(0)
    feel(citizen, Appraisal(anger=1.0, anxiety=0.5, enthusiasm=0.0), decay=0.75)
    assert (citizen.anger, citizen.anxiety, citizen.enthusiasm) == (0.25, 0.125, 0.0)
    feel(citizen, Appraisal(anger=1.0, anxiety=0.5, enthusiasm=0.0), decay=0.75)
    assert citizen.anger == pytest.approx(0.4375)


def test_untracked_emotions_exert_nothing_and_tracked_ones_are_weighted() -> None:
    calm, angry = _citizen(0), _citizen(1, anger=1.0, anxiety=0.5, enthusiasm=0.5)
    assert (awakening_pull(calm, FELT), tolerance_scale(calm, FELT)) == (0.0, 1.0)
    assert awakening_pull(angry, FELT) == pytest.approx(0.6 + 0.15 - 0.1)
    assert tolerance_scale(angry, FELT) == 0.5
    assert (awakening_pull(angry, QUIET), tolerance_scale(angry, QUIET)) == (0.0, 1.0)


def test_the_pull_moves_the_awakening_threshold_inside_its_bound() -> None:
    awakening = load_config().awakening  # amplitude 0.5
    citizen = _citizen(0, base_threshold=0.4)
    kwargs: dict[str, Any] = {"mandate_dev": 0.0, "proximity": 0.0, "config": awakening}
    assert awakening_threshold(citizen, **kwargs) == 0.4
    assert awakening_threshold(citizen, emotion_pull=0.5, **kwargs) == pytest.approx(0.3)
    assert awakening_threshold(citizen, emotion_pull=-0.5, **kwargs) == pytest.approx(0.5)
    assert awakening_threshold(citizen, emotion_pull=5.0, **kwargs) == pytest.approx(0.2)


def test_an_angry_citizen_is_consulted_and_acts_where_a_calm_one_would_not() -> None:
    awakening = load_config().awakening
    holder = _citizen(9, positions=(0.9,), revealed_position=(0.9,), term_end_tick=None)
    calm = _citizen(0, positions=(0.55,), threshold=0.5, base_threshold=0.4)       # gap 0.35
    angry = _citizen(1, positions=(0.55,), threshold=0.5, base_threshold=0.4, anger=1.0, anxiety=0.0, enthusiasm=0.0)
    consulted = select_consulted([calm, angry, holder], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=awakening, emotions=FELT)
    assert [c.citizen_id for c, _ in consulted] == [1]
    assert select_consulted([calm, angry], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=awakening, emotions=QUIET) == []
    menu = PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False)
    assert deterministic_pressure_action(angry, 0.35, menu) is PressureAct.NOTHING
    assert deterministic_pressure_action(angry, 0.35, menu, tolerance_scale=tolerance_scale(angry, FELT)) is PressureAct.MOBILIZE


# ── the pressure prompt ───────────────────────────────────────────────────

class _CapturingPressureClient:
    def __init__(self) -> None:
        self.prompts: list[tuple[str, str]] = []

    def complete_json(self, *, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int, think: bool = True) -> str:
        self.prompts.append((system_prompt, user_prompt))
        consulted = json.loads(user_prompt)["consulted"]
        return json.dumps({"decisions": [{"cid": c["cid"], "target": c["target"], "act": 0, "motif": 304} for c in consulted]})


def _pressure_config(emotions: EmotionsConfig) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True), emotions=emotions,
                               awakening=dataclasses.replace(config.awakening, enabled=True))


def _pressure_context(cid: int) -> PressureContext:
    return PressureContext(cid=cid, target=9, self_gap=0.35, mandate_dev=0.0, ticks_to_election=4, available=(0, 3, 4),
                           petition_open=False, petition_expires_at_tick=None, already_signed=False)


def test_tracked_emotions_reach_the_pressure_prompt_with_their_definitions_and_untracked_ones_do_not() -> None:
    angry = _citizen(1, anger=0.81234, anxiety=0.2, enthusiasm=0.0)
    assert pressure_signals(_pressure_config(QUIET)) == (PRESSURE_THRESHOLD_SIGNAL, *PRESSURE_EMOTION_SIGNALS)
    assert pressure_signals(load_config()) == (PRESSURE_THRESHOLD_SIGNAL,)
    assert pressure_shipped_signal_values(angry) == {"blank_threshold": 0.5, "anger": 0.8123, "anxiety": 0.2, "enthusiasm": 0.0}
    assert pressure_shipped_signal_values(_citizen(0)) == {"blank_threshold": 0.5}

    client = _CapturingPressureClient()
    decide_pressure_actions([angry], {1: _pressure_context(1)}, _pressure_config(QUIET), client)
    system_prompt, user_prompt = client.prompts[0]
    assert all(signal.definition.strip() in system_prompt for signal in PRESSURE_EMOTION_SIGNALS)
    assert json.loads(user_prompt)["consulted"][0]["ctx"].items() >= {"anger": 0.8123, "anxiety": 0.2, "enthusiasm": 0.0}.items()


def test_the_fallback_applies_the_angry_tolerance_too() -> None:
    angry = _citizen(1, anger=1.0, anxiety=0.0, enthusiasm=0.0)
    config = dataclasses.replace(
        _pressure_config(FELT), pressure_menu=PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False),
    )
    [decision] = _deterministic_pressure_fallback([angry], {1: _pressure_context(1)}, config)
    assert decision.act == int(PressureAct.MOBILIZE)


# ── the engine ────────────────────────────────────────────────────────────

def _config(output_dir: Path, dynamics: DynamicsConfig, emotions: EmotionsConfig) -> PolityConfig:
    return dataclasses.replace(golden_config(output_dir, llm=False), dynamics=dynamics, emotions=emotions)


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_dynamic_run_journals_each_tick_s_update_and_snapshots_the_moved_views(tmp_path: Path) -> None:
    config = _config(tmp_path, MOVING, FELT)
    journal = run_simulation(config, run_id="run")
    events = _lines(journal)
    ticks = sorted({e["tick"] for e in events})
    for tick in ticks:
        types = [e["event_type"] for e in events if e["tick"] == tick]
        assert types.count("emotions_updated") == 1 and types[-1] == "opinion_dynamics_step"
        assert "pressure_action" not in types[:types.index("emotions_updated")]
    assert len(ticks) == config.run.duration_years * config.run.ticks_per_year + 1

    snapshots = _lines(journal.parent / "snapshots.jsonl")
    assert not any("latent_factors" in row or "anger" in row for row in snapshots if row["year"] == 0)
    assert all({"latent_factors", "anger", "anxiety", "enthusiasm"} <= set(row) for row in snapshots if row["year"] > 0)

    citizens = load_checkpoint(journal.parent / "checkpoint.json").state.citizens
    structure = latent_structure(config.citizens, config.run.population_size, config.run.seed)
    factors = np.array([c.latent_factors for c in citizens])
    assert [c.issue_positions for c in citizens] == [tuple(float(x) for x in row) for row in structure.positions(factors)]


def test_dynamics_and_emotions_at_their_neutral_settings_change_nothing_else_the_run_does(tmp_path: Path) -> None:
    static = run_simulation(golden_config(tmp_path / "static", llm=False), run_id="run")
    neutral = run_simulation(_config(tmp_path / "neutral", NEUTRAL, QUIET), run_id="run")
    added = {"opinion_dynamics_step", "emotions_updated"}

    def without_ids(events: list[dict[str, Any]]) -> list[dict[str, Any]]:  # the added events shift every later id
        return [{k: v for k, v in e.items() if k != "event_id"} for e in events if e["event_type"] not in added]

    assert without_ids(_lines(neutral)) == without_ids(_lines(static))

    static_checkpoint = json.loads((static.parent / "checkpoint.json").read_text())
    assert "dynamics_rng_state" not in static_checkpoint
    assert not any({"latent_factors", "anger"} & set(c) for c in static_checkpoint["citizens"])


def test_a_dynamic_run_resumed_after_a_crash_matches_an_uninterrupted_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uninterrupted = run_simulation(_config(tmp_path / "a", MOVING, FELT), run_id="run")
    real_phase = engine._run_accountability_phase

    def _crash_at_tick_5(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 5:
            raise _SimulatedCrash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", _crash_at_tick_5)
    with pytest.raises(_SimulatedCrash):
        run_simulation(_config(tmp_path / "b", MOVING, FELT), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_config(tmp_path / "b", MOVING, FELT), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()
    assert (resumed.parent / "snapshots.jsonl").read_bytes() == (uninterrupted.parent / "snapshots.jsonl").read_bytes()
