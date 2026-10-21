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
from api.domain.polity.citizen import Citizen, Office, generate_population, latent_structure
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
from api.domain.polity.opinion_dynamics import Mood, NeighbourEdges, apply_dynamics, current_factors, update_latent_factors
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


@pytest.mark.behavior("CIT-02")
@settings(max_examples=300, deadline=None)
@given(_worlds())
def test_at_the_neutral_settings_nobody_moves_at_all(world: tuple) -> None:
    factors, anchors, edges, _, _, bound = world
    step = update_latent_factors(factors, anchors, edges, dataclasses.replace(NEUTRAL, confidence_bound=bound), np.random.default_rng(0))
    assert np.array_equal(step.factors, factors)
    assert step.mean_shift == 0.0 and step.max_shift == 0.0


@pytest.mark.behavior("CIT-02")
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


# ── radicalisation (ADR-033) ──────────────────────────────────────────────

RADICAL = dataclasses.replace(NEUTRAL, radical_step=0.1)
"""One-step settings with nothing but the push: no neighbours' pull, no noise, no pull back to an anchor."""


def _mood(anger: list[float], salience: list[float], president: tuple[float, float] | None = (0.0, 0.0)) -> Mood:
    return Mood(anger=np.array(anger), salience=np.array(salience), president=None if president is None else np.array(president))


def test_the_radicalisation_settings_ship_at_zero_and_need_emotions() -> None:
    config = load_config()
    assert config.dynamics.radical_step == 0.0 and config.dynamics.anger_narrows_bound == 0.0
    dynamic = dataclasses.replace(config, dynamics=RADICAL)
    with pytest.raises(PolityConfigError, match="emotions.enabled"):
        validate_config(dynamic)
    with pytest.raises(PolityConfigError, match="emotions.enabled"):
        validate_config(dataclasses.replace(config, dynamics=dataclasses.replace(NEUTRAL, anger_narrows_bound=0.5)))
    awake = dataclasses.replace(dynamic, awakening=dataclasses.replace(config.awakening, enabled=True), emotions=QUIET)
    validate_config(awake)


@settings(max_examples=200, deadline=None)
@given(_worlds(), st.lists(st.floats(0.0, 1.0), min_size=8, max_size=8), st.lists(st.floats(0.0, 1.0), min_size=8, max_size=8))
def test_a_mood_changes_nothing_while_the_two_couplings_are_at_zero(world: tuple, anger: list[float], salience: list[float]) -> None:
    factors, anchors, edges, susceptibility, step_size, bound = world
    config = DynamicsConfig(enabled=True, susceptibility=susceptibility, influence_step=step_size, confidence_bound=bound, drift_std=0.1)
    n = len(factors)
    mood = _mood(anger[:n], salience[:n], president=(float(factors[0][0]), float(factors[0][1])))
    with_mood = update_latent_factors(factors, anchors, edges, config, np.random.default_rng(3), mood=mood)
    without = update_latent_factors(factors, anchors, edges, config, np.random.default_rng(3))
    assert np.array_equal(with_mood.factors, without.factors) and with_mood.radicalised == 0


def test_an_angry_citizen_the_shock_reached_steps_away_from_the_president_and_nobody_else_moves() -> None:
    factors = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 2.0], [-3.0, 0.0], [5.0, 5.0]])
    edges = NeighbourEdges.from_graph(_graph([], 5))
    mood = _mood(anger=[0.0, 1.0, 0.5, 0.0, 1.0], salience=[1.0, 1.0, 1.0, 1.0, 0.0], president=(0.0, 0.0))
    step = update_latent_factors(factors, factors.copy(), edges, RADICAL, np.random.default_rng(0), mood=mood)
    assert step.factors[0].tolist() == [0.0, 0.0]  # the president themself: no direction, no push
    assert step.factors[1].tolist() == pytest.approx([1.1, 0.0])  # anger 1, salience 1: radical_step along the direction away
    assert step.factors[2].tolist() == pytest.approx([0.0, 2.05])  # anger 0.5: half the step
    assert step.factors[3].tolist() == [-3.0, 0.0]  # calm: untouched
    assert step.factors[4].tolist() == [5.0, 5.0]  # angry but the shock never reached them (salience 0)
    assert step.radicalised == 2
    vacant = update_latent_factors(factors, factors.copy(), edges, RADICAL, np.random.default_rng(0), mood=_mood([1.0] * 5, [1.0] * 5, None))
    assert np.array_equal(vacant.factors, factors) and vacant.radicalised == 0


def test_the_push_survives_the_pull_back_to_the_anchor_only_in_proportion_to_susceptibility() -> None:
    factors = np.array([[0.0, 0.0], [1.0, 0.0]])
    mood = _mood([0.0, 1.0], [1.0, 1.0])
    edges = NeighbourEdges.from_graph(_graph([], 2))
    held = update_latent_factors(factors, factors.copy(), edges, dataclasses.replace(RADICAL, susceptibility=0.5), np.random.default_rng(0), mood=mood)
    assert held.factors[1].tolist() == pytest.approx([0.5 * 1.0 + 0.5 * 1.1, 0.0])  # (1 - s) anchor + s (f + push)


def test_anger_narrows_the_confidence_bound_so_an_angry_citizen_listens_only_to_the_like_minded() -> None:
    factors = np.array([[0.0, 0.0], [0.8, 0.0]])
    edges = NeighbourEdges.from_graph(_graph([(0, 1)], 2))
    listening = DynamicsConfig(enabled=True, susceptibility=1.0, influence_step=1.0, confidence_bound=1.0, drift_std=0.0, anger_narrows_bound=0.5)
    calm = update_latent_factors(factors, factors.copy(), edges, listening, np.random.default_rng(0), mood=_mood([0.0, 0.0], [0.0, 0.0], None))
    assert calm.factors[0].tolist() == pytest.approx([0.8, 0.0]) and calm.influenced == 2  # 0.8 is inside the bound of 1.0
    angry = update_latent_factors(factors, factors.copy(), edges, listening, np.random.default_rng(0), mood=_mood([1.0, 0.0], [0.0, 0.0], None))
    assert angry.factors[0].tolist() == [0.0, 0.0]  # citizen 0's bound is 0.5 at anger 1: citizen 1 is out of earshot
    assert angry.factors[1].tolist() == pytest.approx([0.0, 0.0])  # citizen 1 is calm: their bound is 1.0 and they still hear citizen 0
    assert angry.influenced == 1


def test_apply_dynamics_reads_anger_salience_and_the_sitting_president_off_the_citizens() -> None:
    citizens_config = load_config().citizens
    population = generate_population(citizens_config, 6, seed=2)
    structure = latent_structure(citizens_config, 6, seed=2)
    edges = NeighbourEdges.from_graph(_graph([], 6))
    for citizen in population:
        citizen.anger, citizen.event_salience = 1.0, 1.0
    population[0].office = Office.PRESIDENT
    start = current_factors(population, structure)
    step = apply_dynamics(population, structure, edges, RADICAL, np.random.default_rng(1))
    moved = np.array([c.latent_factors for c in population])
    assert step.radicalised == 5 and np.array_equal(moved[0], start[0])  # everyone but the president steps
    assert (np.linalg.norm(moved[1:] - start[0], axis=1) > np.linalg.norm(start[1:] - start[0], axis=1)).all()  # all farther from them
    population[0].office = Office.NONE
    assert apply_dynamics(population, structure, edges, RADICAL, np.random.default_rng(1)).radicalised == 0  # no president, no push


def test_a_run_with_the_push_on_journals_how_many_it_moved_and_one_without_does_not(tmp_path: Path) -> None:
    pushing = dataclasses.replace(MOVING, radical_step=0.05, anger_narrows_bound=0.3)
    with_push = [e for e in _lines(run_simulation(_config(tmp_path / "on", pushing, FELT), run_id="run")) if e["event_type"] == "opinion_dynamics_step"]
    assert with_push and all("radicalised" in e["payload"] and e["payload"]["radicalised"] >= 0 for e in with_push)
    without = [e for e in _lines(run_simulation(_config(tmp_path / "off", MOVING, FELT), run_id="run")) if e["event_type"] == "opinion_dynamics_step"]
    assert without and not any("radicalised" in e["payload"] for e in without)
