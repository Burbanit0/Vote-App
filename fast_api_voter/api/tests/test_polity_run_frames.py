"""Run frames and the run map (run explorer B1): api/domain/polity/run_frames.py and
run_projection.py. The oracle replays live runs whole, without the yearly reset, and
requires every census and the final checkpoint to come out."""
from __future__ import annotations

import dataclasses
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.citizen import Role, generate_population, latent_structure
from api.domain.polity.run_digest import read_journal_tolerant
from api.domain.polity.run_frames import (
    ACT_NONE,
    CANDIDACY_DECLARED,
    CANDIDACY_DECLINED,
    CANDIDACY_ELECTED,
    CANDIDACY_NONE,
    CANDIDACY_NOMINATION_LOST,
    CANDIDACY_STANDING,
    STATUS_CODES,
    VOTE_BLANK,
    VOTE_NONE,
    VOTE_OTHER,
    VOTE_WINNER,
    NotExplorable,
    RunFrames,
    TickMarks,
    load_run_frames,
    read_census,
)
from api.domain.polity.run_projection import TOP_ISSUES, build_projection
from api.domain.polity.run_provenance import typed_config_mapping
from api.domain.polity.snapshots import write_snapshot
from api.tests.polity_explorer_fixtures import YEARS, explorer_runs, replay_mismatches
from api.tests.polity_golden import golden_config

@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return explorer_runs(tmp_path_factory.mktemp("frames"))


def _events(run_dir: Path) -> list[dict[str, Any]]:
    return read_journal_tolerant(run_dir / "events.jsonl")[0]


def _config(run_dir: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads((run_dir / "config.json").read_text())
    return config


def _census(run_dir: Path) -> dict[int, list[dict[str, Any]]]:
    return read_census(run_dir / "snapshots.jsonl", _config(run_dir)["run"]["population_size"])


# ── the oracle ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["invalidated", "staggered", "audited", "deterministic", "dynamic"])
def test_the_replay_reproduces_every_census_and_the_final_checkpoint(runs: dict[str, Path], name: str) -> None:
    assert replay_mismatches(runs[name]) == []


def test_the_oracle_catches_a_replay_that_goes_wrong(runs: dict[str, Path], tmp_path: Path) -> None:
    run_dir = Path(shutil.copytree(runs["staggered"], tmp_path / "run"))
    events = _lines(run_dir / "events.jsonl")
    (run_dir / "events.jsonl").write_text("".join(line for line in events if json.loads(line)["event_type"] != "elected"))
    assert any(m.startswith("census of year") for m in replay_mismatches(run_dir))
    (run_dir / "events.jsonl").write_text("".join(line for line in events if json.loads(line)["tick"] <= 2))
    assert "censuses compared [], recorded [0, 1, 2, 3]" in replay_mismatches(run_dir)  # a journal cut before a census


def test_the_oracle_runs_exercise_what_the_replay_handles(runs: dict[str, Path]) -> None:
    def count(name: str, event_type: str, **payload: Any) -> int:
        return sum(1 for e in _events(runs[name]) if e["event_type"] == event_type
                   and all(e["payload"].get(k) == v for k, v in payload.items()))

    assert count("invalidated", "election_invalidated") >= 2 and count("invalidated", "elected") == 0
    assert all(count(name, "candidacy_declared", path="rupture") >= 3 for name in ("invalidated", "staggered", "deterministic", "dynamic"))
    assert count("staggered", "elected") >= 3 and count("staggered", "recalled") >= 1
    assert count("staggered", "representative_response") >= 1 and count("staggered", "nomination_lost") >= 1
    staggered = _events(runs["staggered"])
    outcome_ticks = {e["tick"] for e in staggered if e["event_type"] == "elected"}
    assert {e["tick"] for e in staggered if e["event_type"] == "campaign_positioning"} - outcome_ticks  # campaigns ahead of the vote
    assert count("audited", "vote_cast", audit=1) >= 1


# ── frames ────────────────────────────────────────────────────────────────

def _by_tick(events: list[dict[str, Any]], event_type: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for e in events:
        if e["event_type"] == event_type:
            grouped.setdefault(e["tick"], []).append(e)
    return grouped


def test_each_frame_holds_the_state_after_its_tick_and_what_happened_in_it(runs: dict[str, Path]) -> None:
    run_dir = runs["staggered"]
    frames = load_run_frames(run_dir)
    events = _events(run_dir)
    assert (frames.run_id, frames.population, frames.ticks_per_year) == ("staggered", 40, 4)
    assert [f.tick for f in frames.frames] == list(range(YEARS * 4 + 1))
    assert frames.last_checkpoint_tick == YEARS * 4 and not any(f.partial for f in frames.frames)
    assert frames.vote_coverage == "all" and frames.unknown_event_types == ()

    for tick, [elected] in _by_tick(events, "elected").items():
        frame = frames.frames[tick]
        winner = elected["citizen_id"]
        assert frame.status[winner] == STATUS_CODES[Role.ELECTED.value] and frame.candidacy[winner] == CANDIDACY_ELECTED
        ballots = _by_tick(events, "vote_cast")[tick]
        expected = [VOTE_NONE] * frames.population
        for ballot in ballots:
            first = ballot["payload"]["ranking"][0] if ballot["payload"]["ranking"] else None
            expected[ballot["citizen_id"]] = VOTE_BLANK if ballot["payload"]["blank"] else VOTE_WINNER if first == winner else VOTE_OTHER
        assert list(frame.vote) == expected
        [pledge] = [e for e in _by_tick(events, "mandate_pledge_declared")[tick] if e["citizen_id"] == winner]
        assert frame.president is not None and frame.president.lame_duck == pledge["payload"]["lame_duck"]
    for tick, recalls in _by_tick(events, "recalled").items():
        assert frames.frames[tick].president is None
        assert all(frames.frames[tick].status[e["citizen_id"]] == STATUS_CODES[Role.ELECTOR.value] for e in recalls)

    for tick, acts in _by_tick(events, "pressure_action").items():
        by_citizen = {e["citizen_id"]: e["payload"]["act"] for e in acts}
        assert list(frames.frames[tick].act) == [by_citizen.get(cid, ACT_NONE) for cid in range(frames.population)]
    seated: set[int] = set()
    for frame in frames.frames:
        for rotation in _by_tick(events, "sortition_rotation").get(frame.tick, []):
            seated = set(rotation["payload"]["seated"])
        assert {cid for cid, flag in enumerate(frame.chamber) if flag} == seated

    readings = {e["tick"]: e for e in events if e["event_type"] == "legitimacy_updated"}
    for tick, reading in readings.items():
        president = frames.frames[tick].president
        if president is not None and president.citizen_id == reading["citizen_id"]:
            assert (president.legitimacy, president.ecart, president.mandate_strength) == (
                reading["payload"]["legitimacy"], reading["payload"]["ecart"], reading["payload"]["mandate_strength"])


def test_a_candidacy_code_is_the_furthest_stage_the_citizen_reached_in_the_tick(runs: dict[str, Path]) -> None:
    run_dir = runs["staggered"]
    frames = load_run_frames(run_dir)
    stages = {
        "candidacy_considered": lambda e: CANDIDACY_DECLARED if e["payload"]["outcome"] == 1 else CANDIDACY_DECLINED,
        "nomination_lost": lambda e: CANDIDACY_NOMINATION_LOST,
        "candidacy_declared": lambda e: CANDIDACY_STANDING,
        "elected": lambda e: CANDIDACY_ELECTED,
    }
    expected: dict[tuple[int, int], int] = {}
    for e in _events(run_dir):
        if e["event_type"] in stages:
            key = (e["tick"], e["citizen_id"])
            expected[key] = max(expected.get(key, CANDIDACY_NONE), stages[e["event_type"]](e))
    assert {CANDIDACY_DECLINED, CANDIDACY_DECLARED, CANDIDACY_NOMINATION_LOST, CANDIDACY_STANDING, CANDIDACY_ELECTED} <= set(expected.values())
    for frame in frames.frames:
        assert list(frame.candidacy) == [expected.get((frame.tick, cid), CANDIDACY_NONE) for cid in range(frames.population)]


def test_a_president_s_pledge_and_drift_sit_on_the_map(runs: dict[str, Path]) -> None:
    frames = load_run_frames(runs["staggered"])
    presidents = [f.president for f in frames.frames if f.president is not None]
    assert presidents and all(p.pledged_xy is not None for p in presidents)
    assert any(p.xy != p.pledged_xy for p in presidents)  # the fake's representative always concedes a step


def test_vote_coverage_names_what_the_journal_recorded(runs: dict[str, Path]) -> None:
    assert load_run_frames(runs["invalidated"]).vote_coverage == "all"
    assert load_run_frames(runs["audited"]).vote_coverage == "audit_sample"
    assert load_run_frames(runs["deterministic"]).vote_coverage == "none"
    marks = TickMarks.empty(3)
    marks.ballots = {0: (1, None), 1: (0, 7), 2: (0, None)}
    marks.winner = 7
    assert marks.votes(3) == [VOTE_BLANK, VOTE_WINNER, VOTE_OTHER]


# ── the map ───────────────────────────────────────────────────────────────

def test_the_latent_map_puts_citizens_at_their_redrawn_factors(runs: dict[str, Path]) -> None:
    run_dir = runs["deterministic"]
    config, census = _config(run_dir), _census(run_dir)
    projection = build_projection(config, census)
    structure = latent_structure(golden_config(run_dir, llm=False).citizens, 40, config["run"]["seed"])
    assert (projection.method, projection.positions) == ("latent", "static")
    np.testing.assert_array_equal(projection.citizens_at(2), structure.anchors)
    for axis, weights in zip(projection.axes, structure.loadings.T):
        assert [w.issue for w in axis] == list(np.argsort(-np.abs(weights), kind="stable")[:TOP_ISSUES])
        assert abs(axis[0].weight) >= abs(axis[-1].weight)

    own = census[0][5]["issue_positions"]
    np.testing.assert_allclose(projection.holder_xy(5, 2, own), structure.anchors[5], atol=1e-9)  # no drift: on their anchor
    moved = list(own)
    strongest = projection.axes[0][0].issue
    moved[strongest] = min(1.0, moved[strongest] + 0.2)
    assert projection.holder_xy(5, 2, moved) != pytest.approx(tuple(structure.anchors[5]))
    assert np.isfinite(projection.point_xy([0.0] * 20)).all() and np.isfinite(projection.point_xy([1.0] * 20)).all()  # at the bounds


def test_a_structure_that_does_not_reproduce_the_census_falls_back_to_principal_components(runs: dict[str, Path]) -> None:
    run_dir = runs["deterministic"]
    config, census = _config(run_dir), _census(run_dir)
    wrong_seed = {**config, "run": {**config["run"], "seed": config["run"]["seed"] + 1}}
    for mapping in (wrong_seed, {**config, "citizens": {**config["citizens"], "position_dist": "uniform"}}):
        projection = build_projection(mapping, census)
        assert (projection.method, projection.positions, projection.loadings) == ("pca", "static", None)
        assert all(axis[0].weight > 0 for axis in projection.axes)  # signed toward its strongest issue
        positions = np.array([row["issue_positions"] for row in census[0]])
        assert projection.point_xy(positions.mean(axis=0)) == pytest.approx((0.0, 0.0), abs=1e-9)
        assert projection.holder_xy(3, 0, positions[3]) == pytest.approx(tuple(projection.citizens_at(0)[3]))

    one_issue = {0: [{**row, "issue_positions": row["issue_positions"][:1]} for row in census[0]]}
    projection = build_projection(wrong_seed, one_issue)
    assert projection.axes[1][0].weight == 0.0 and projection.citizens_at(0).shape == (40, 2)


def test_a_dynamic_run_moves_citizens_once_a_year(runs: dict[str, Path]) -> None:
    run_dir = runs["dynamic"]
    config, census = _config(run_dir), _census(run_dir)
    projection = build_projection(config, census)
    structure = latent_structure(golden_config(run_dir, llm=False).citizens, 40, config["run"]["seed"])
    assert (projection.method, projection.positions) == ("latent", "yearly")
    np.testing.assert_array_equal(projection.citizens_at(0), structure.anchors)  # no factors recorded before they move
    np.testing.assert_array_equal(projection.citizens_at(1), [row["latent_factors"] for row in census[1]])
    assert projection.census_year(99) == max(census) and projection.census_year(1) == 1


# ── damaged, interrupted and older runs ───────────────────────────────────

def _copy(run_dir: Path, tmp_path: Path) -> Path:
    return Path(shutil.copytree(run_dir, tmp_path / run_dir.name))


def _lines(path: Path) -> list[str]:
    return path.read_text().splitlines(keepends=True)


def test_a_torn_journal_an_unknown_event_and_an_older_config_still_load(runs: dict[str, Path], tmp_path: Path) -> None:
    run_dir = _copy(runs["staggered"], tmp_path)
    whole = load_run_frames(runs["staggered"])
    with (run_dir / "events.jsonl").open("a") as handle:
        handle.write(json.dumps({"event_type": "future_event", "tick": 12, "citizen_id": None, "payload": {}}) + "\n")
        handle.write('{"event_type": "pressure_act')  # killed mid-write
    config = _config(run_dir)
    for section in ("vote", "dynamics", "emotions", "legislation"):  # absent from runs before S4
        config.pop(section)
    (run_dir / "config.json").write_text(json.dumps(config))
    loaded = load_run_frames(run_dir)
    assert loaded.unknown_event_types == ("future_event",)
    assert loaded.frames == whole.frames and loaded.projection.positions == "static"


def test_ticks_after_the_last_checkpoint_are_partial(runs: dict[str, Path], tmp_path: Path) -> None:
    run_dir = _copy(runs["deterministic"], tmp_path)
    progress = json.loads((run_dir / "progress.json").read_text())
    (run_dir / "progress.json").write_text(json.dumps({**progress, "last_checkpoint_tick": 5}))
    frames = load_run_frames(run_dir)
    assert frames.last_checkpoint_tick == 5 and [f.partial for f in frames.frames] == [f.tick > 5 for f in frames.frames]
    (run_dir / "progress.json").unlink()
    assert all(f.partial for f in load_run_frames(run_dir).frames)  # nothing confirmed


def test_a_census_year_cut_short_is_dropped_and_the_last_complete_one_stands_in(runs: dict[str, Path], tmp_path: Path) -> None:
    run_dir = _copy(runs["dynamic"], tmp_path)
    rows = _lines(run_dir / "snapshots.jsonl")
    (run_dir / "snapshots.jsonl").write_text("".join(rows[: 40 * 3 + 7]) + '{"year": 3, "torn')
    census = _census(run_dir)
    assert sorted(census) == [0, 1, 2]
    frames = load_run_frames(run_dir)
    assert len(frames.frames) == YEARS * 4 + 1 and frames.projection.census_year(3) == 2


@pytest.mark.parametrize("damage", ["config", "journal", "census"])
def test_a_run_missing_what_the_replay_needs_is_not_explorable(runs: dict[str, Path], tmp_path: Path, damage: str) -> None:
    run_dir = _copy(runs["deterministic"], tmp_path)
    if damage == "config":
        (run_dir / "config.json").write_text("[]")
    elif damage == "journal":
        (run_dir / "events.jsonl").write_text("")
    else:
        (run_dir / "snapshots.jsonl").unlink()
    with pytest.raises(NotExplorable):
        load_run_frames(run_dir)


# ── payload ───────────────────────────────────────────────────────────────

def _synthetic_p500_run(run_dir: Path) -> Path:
    """A population of 500 over 8 years, with the p500 batch's shape of journal: a
    pressure act from a fifth of the population every tick, every ballot recorded at four
    elections, a president with legitimacy readings."""
    config = golden_config(run_dir, llm=False)
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=500, duration_years=8))
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(json.dumps(typed_config_mapping(config), default=str))
    citizens = generate_population(config.citizens, 500, config.run.seed)
    for year in range(9):
        write_snapshot(run_dir / "snapshots.jsonl", citizens, tick=year * 4, ticks_per_year=4)
    rng = np.random.default_rng(0)
    events: list[Mapping[str, Any]] = []
    for tick in range(33):
        if tick % 8 == 0:
            events += [{"event_type": "vote_cast", "tick": tick, "citizen_id": cid,
                        "payload": {"blank": 0, "ranking": [7, 8]}} for cid in range(500)]
            events.append({"event_type": "elected", "tick": tick, "citizen_id": 7, "payload": {"office": "president"}})
        events += [{"event_type": "pressure_action", "tick": tick, "citizen_id": int(cid), "payload": {"act": int(rng.integers(0, 5)), "target": 7}}
                   for cid in rng.choice(500, size=100, replace=False)]
        events.append({"event_type": "legitimacy_updated", "tick": tick, "citizen_id": 7,
                       "payload": {"legitimacy": 0.5, "ecart": 0.01, "mandate_strength": 0.4}})
    (run_dir / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    (run_dir / "progress.json").write_text(json.dumps({"last_checkpoint_tick": 32}))
    return run_dir


def _payload_bytes(frames: RunFrames) -> int:
    return len(json.dumps([dataclasses.asdict(frame) for frame in frames.frames], separators=(",", ":")))


def test_a_p500_run_s_frames_fit_the_payload_budget(tmp_path: Path) -> None:
    frames = load_run_frames(_synthetic_p500_run(tmp_path / "p500"))
    assert len(frames.frames) == 33 and frames.frames[8].president is not None
    assert _payload_bytes(frames) <= 400_000

