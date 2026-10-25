"""ADR-040: party leaders who move their platform (Laver and Sergenti's sticker, aggregator, hunter, explorer)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from api.domain.polity.checkpoint import _party_from_dict, _party_to_dict
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import PolityConfig, PolityConfigError, load_config, validate_config
from api.domain.polity.config import LEADER_RULES
from api.domain.polity.leaders import EXPLORER_PROBES, nearest, reposition, shares
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_run_simulation import _SimulatedCrash


def _citizen(i: int, position: tuple[float, float]) -> Citizen:
    return Citizen(citizen_id=i, issue_positions=position, issue_priorities=(0.5, 0.5), blank_threshold=0.3, ambition_score=0.1)


def _line() -> list[Citizen]:
    """Ten citizens spread along the first issue, all at 0.5 on the second."""
    return [_citizen(i, (i / 9, 0.5)) for i in range(10)]


def _two(left: float = 0.2, right: float = 0.8) -> list[Party]:
    return [Party(party_id=0, platform=(left, 0.5)), Party(party_id=1, platform=(right, 0.5))]


# ── config ────────────────────────────────────────────────────────────────

def test_leaders_ship_as_stickers_and_a_moving_rule_needs_a_step() -> None:
    config = load_config()
    assert config.parties.leader_rule == "sticker" and config.parties.leader_step == 0.0 and LEADER_RULES[0] == "sticker"
    with pytest.raises(PolityConfigError, match="leader_step"):
        validate_config(dataclasses.replace(config, parties=dataclasses.replace(config.parties, leader_rule="hunter")))
    validate_config(dataclasses.replace(config, parties=dataclasses.replace(config.parties, leader_rule="hunter", leader_step=0.05)))


def test_the_step_is_read_from_the_yaml_and_bounded_by_one(tmp_path: Path) -> None:
    from api.tests.test_polity_config import _write

    with pytest.raises(PolityConfigError, match="leader_step"):
        load_config(_write(tmp_path, lambda d: d["parties"].update(leader_rule="hunter", leader_step=1.5)))
    with pytest.raises(PolityConfigError, match="leader_rule"):
        load_config(_write(tmp_path, lambda d: d["parties"].update(leader_rule="predator", leader_step=0.1)))
    parsed = load_config(_write(tmp_path, lambda d: d["parties"].update(leader_rule="explorer", leader_step=0.1)))
    assert parsed.parties.leader_rule == "explorer" and parsed.parties.leader_step == 0.1


# ── the poll ──────────────────────────────────────────────────────────────

def test_a_citizen_supports_the_nearest_platform_by_the_ballots_weighted_distance() -> None:
    positions = np.array([[0.1, 0.9], [0.9, 0.1]])
    priorities = np.array([[1.0, 0.0], [0.0, 1.0]])  # the first cares only about issue 0, the second only about issue 1
    platforms = np.array([[0.1, 0.1], [0.9, 0.9]])
    assert nearest(positions, priorities, platforms).tolist() == [0, 0]  # issue 0 puts the first at party 0; issue 1 the second
    assert shares(positions, priorities, platforms).tolist() == [1.0, 0.0]
    assert nearest(np.array([[0.5, 0.5]]), np.array([[0.5, 0.5]]), platforms).tolist() == [0]  # a tie goes to the lower row


# ── the rules ─────────────────────────────────────────────────────────────

def test_a_sticker_never_moves() -> None:
    parties, moves = reposition(_two(), _line(), "sticker", 0.1, np.random.default_rng(1))
    assert parties == _two() and all(m.shift == 0 for m in moves) and [m.share for m in moves] == [0.5, 0.5]


def test_an_aggregator_steps_toward_its_supporters_and_stops_on_them() -> None:
    moved, moves = reposition(_two(left=0.0), _line(), "aggregator", 0.05, np.random.default_rng(1))
    left_supporters = [i / 9 for i in range(10) if i / 9 < 0.4]  # the citizens nearer 0.0 than 0.8
    assert moved[0].platform[0] == pytest.approx(0.05) and moves[0].shift == pytest.approx(0.05)  # a step, not all the way
    far, _ = reposition(_two(left=0.0), _line(), "aggregator", 5.0, np.random.default_rng(1))
    assert far[0].platform[0] == pytest.approx(float(np.mean(left_supporters)))  # a long step lands on the centroid


def test_a_hunter_keeps_its_heading_while_its_share_grows_and_turns_back_when_it_falls() -> None:
    first, _ = reposition(_two(), _line(), "hunter", 0.05, np.random.default_rng(3))
    hunter = first[0]
    assert hunter.heading is not None and hunter.last_share == 0.5 and np.linalg.norm(hunter.heading) == pytest.approx(1.0)
    rising = dataclasses.replace(hunter, last_share=0.1)  # the next poll (0.5 again) is higher than this
    kept, _ = reposition([rising, first[1]], _line(), "hunter", 0.05, np.random.default_rng(9))
    assert kept[0].heading == hunter.heading
    falling = dataclasses.replace(hunter, last_share=0.9)
    for seed in range(20):
        turned, _ = reposition([falling, first[1]], _line(), "hunter", 0.05, np.random.default_rng(seed))
        assert np.dot(turned[0].heading, hunter.heading) <= 0  # always into the half-space it came from


def test_an_explorer_moves_only_to_a_probe_that_polls_better() -> None:
    citizens = [_citizen(i, (0.1, 0.5)) for i in range(5)] + [_citizen(5 + i, (0.9, 0.5)) for i in range(5)]
    stuck, moves = reposition(_two(left=0.1, right=0.9), citizens, "explorer", 0.05, np.random.default_rng(2))
    assert stuck[0].platform == (0.1, 0.5) and moves[0].shift == 0  # every probe away from its five loses them
    left, right = [_citizen(i, (0.2, 0.5)) for i in range(5)], [_citizen(5 + i, (0.8, 0.5)) for i in range(5)]
    lonely = [Party(party_id=0, platform=(0.3, 0.9)), Party(party_id=1, platform=(0.25, 0.5))]  # party 1 is nearer everyone
    went = 0
    for seed in range(10):
        moved, moves = reposition(lonely, left + right, "explorer", 0.4, np.random.default_rng(seed))
        assert moves[0].share == 0.0
        if moves[0].shift > 0:  # it moved only to a probe that polls better than where it stood
            went += 1
            platforms = np.array([p.platform for p in moved])
            people = np.array([c.issue_positions for c in left + right])
            assert shares(people, np.full_like(people, 0.5), platforms)[0] > 0.0
    assert went > 0  # and some probe does: one toward the five on the right takes them
    assert EXPLORER_PROBES == 5


def test_a_hunter_against_a_wall_keeps_the_direction_it_actually_moved_or_none() -> None:
    cornered = Party(party_id=0, platform=(1.0, 0.5), heading=(1.0, 0.0), last_share=0.0)  # its share (0.5) rose: keeps going
    moved, moves = reposition([cornered, Party(party_id=1, platform=(0.0, 0.5))], _line(), "hunter", 0.1, np.random.default_rng(1))
    assert moves[0].shift == 0 and moved[0].platform == (1.0, 0.5) and moved[0].heading is None  # blocked: no heading kept
    sliding = dataclasses.replace(cornered, heading=(0.6, 0.8))
    moved, _ = reposition([sliding, Party(party_id=1, platform=(0.0, 0.5))], _line(), "hunter", 0.1, np.random.default_rng(1))
    assert moved[0].heading == pytest.approx((0.0, 1.0))  # it slid along the wall, and that is its heading now


def test_a_platform_stays_inside_the_unit_box_and_an_unknown_rule_is_refused() -> None:
    edge = [Party(party_id=0, platform=(1.0, 1.0)), Party(party_id=1, platform=(0.0, 0.0))]
    moved, _ = reposition(edge, _line(), "hunter", 0.5, np.random.default_rng(4))
    assert all(0.0 <= x <= 1.0 for p in moved for x in p.platform)
    with pytest.raises(ValueError, match="unknown leader rule"):
        reposition(edge, _line(), "predator", 0.1, np.random.default_rng(4))


def test_a_hunters_state_survives_the_checkpoint_and_other_parties_write_none() -> None:
    hunter = Party(party_id=0, platform=(0.2, 0.5), heading=(0.6, 0.8), last_share=0.4)
    assert _party_from_dict(json.loads(json.dumps(_party_to_dict(hunter)))) == hunter
    assert set(_party_to_dict(Party(party_id=1, platform=(0.5, 0.5)))) == {"party_id", "platform"}


# ── in a run ──────────────────────────────────────────────────────────────

def _twin(flagship: Any, output_dir: Path, rule: str, years: int = 3) -> PolityConfig:
    config = flagship._flagship_config(
        engine="deterministic", years=years, population=60, seats=9, seed=2, output_dir=output_dir,
        max_batch_replays=0, provider=None, workers=1, profile="scenario",
    )
    return dataclasses.replace(config, parties=dataclasses.replace(config.parties, leader_rule=rule, leader_step=0.0 if rule == "sticker" else 0.05))


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_run_moves_every_party_once_a_year_and_checkpoints_the_hunters(flagship: Any, tmp_path: Path) -> None:
    config = _twin(flagship, tmp_path, "hunter")
    journal = run_simulation(config, run_id="run")
    moves = [e for e in _lines(journal) if e["event_type"] == "party_repositioned"]
    parties = config.parties.initial_count
    assert len(moves) == 3 * parties and {m["tick"] for m in moves} == {3, 7, 11}  # the last tick of each year
    assert all(m["payload"]["rule"] == "hunter" for m in moves) and any(m["payload"]["shift"] > 0 for m in moves)
    stored = json.loads((journal.parent / "checkpoint.json").read_text())
    last = {m["payload"]["party_id"]: m["payload"]["platform"] for m in moves}  # the journal says where each party now stands
    assert last == {p["party_id"]: p["platform"] for p in stored["parties"]}
    assert stored["leaders_rng_state"] and all("heading" in p for p in stored["parties"])


def test_a_run_of_stickers_writes_none_of_it(flagship: Any, tmp_path: Path) -> None:
    journal = run_simulation(_twin(flagship, tmp_path, "sticker"), run_id="run")
    assert not [e for e in _lines(journal) if e["event_type"] == "party_repositioned"]
    stored = json.loads((journal.parent / "checkpoint.json").read_text())
    assert "leaders_rng_state" not in stored and not any("heading" in p for p in stored["parties"])


@pytest.mark.parametrize("rule", ["hunter", "explorer"])
def test_a_run_whose_leaders_move_resumed_after_a_crash_matches_an_uninterrupted_one(
    flagship: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str,
) -> None:
    import api.domain.polity.run_polity_simulation as engine

    uninterrupted = run_simulation(_twin(flagship, tmp_path / "a", rule), run_id="run")
    real_phase = engine._run_accountability_phase

    def crash_at_tick_6(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 6:
            raise _SimulatedCrash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash_at_tick_6)
    with pytest.raises(_SimulatedCrash):
        run_simulation(_twin(flagship, tmp_path / "b", rule), run_id="run")
    monkeypatch.undo()
    resumed = run_simulation(_twin(flagship, tmp_path / "b", rule), run_id="run", resume=True)
    assert resumed.read_bytes() == uninterrupted.read_bytes()
    assert (resumed.parent / "checkpoint.json").read_bytes() == (uninterrupted.parent / "checkpoint.json").read_bytes()
