"""checkpoint.py — per-tick state snapshot for a resumable run (Phase 3,
plan-flagship-30y-run.md).

Round-trip correctness is the whole contract here: every field a checkpoint
claims to capture must come back byte-for-byte the same live value it was
given, since `run_simulation`'s own resume path splices these straight back
into its tick loop with no further validation.
"""
import dataclasses

import numpy as np
import pytest

from api.domain.polity.checkpoint import (
    config_hash,
    load_checkpoint,
    restore_rng,
    save_checkpoint,
)
from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.config import load_config
from api.domain.polity.parties import Party


def _citizen(cid, **overrides):
    fields = {
        "citizen_id": cid,
        "issue_positions": (0.1, 0.2, 0.3),
        "issue_priorities": (1.0, 1.0, 1.0),
        "blank_threshold": 0.5,
        "ambition_score": 0.4,
    }
    fields.update(overrides)
    return Citizen(**fields)


def _rng(seed, draws=0):
    rng = np.random.default_rng(seed)
    if draws:
        rng.random(draws)
    return rng


def _save(path, config, **overrides):
    kwargs = dict(
        run_id="r1",
        config=config,
        tick=3,
        next_event_id=42,
        citizens=[_citizen(0)],
        parties=[Party(party_id=0, platform=(0.5, 0.5))],
        pending_rerun=None,
        economy_x=0.0,
        mobilized_last_tick={},
        rupture_rng=_rng(1),
        events_rng=_rng(2),
        sortition_rng=_rng(3),
    )
    kwargs.update(overrides)
    save_checkpoint(path, **kwargs)


def test_round_trip_preserves_scalar_fields(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, tick=7, next_event_id=99, economy_x=0.25)

    cp = load_checkpoint(path)

    assert cp.run_id == "r1"
    assert cp.tick == 7
    assert cp.next_event_id == 99
    assert cp.economy_x == 0.25
    assert cp.config_hash == config_hash(config)


def test_round_trip_preserves_every_citizen_field(tmp_path):
    config = load_config()
    citizen = _citizen(
        5,
        role=Role.CANDIDATE,
        office=Office.PRESIDENT,
        term_end_tick=12,
        party_affiliation=1,
        mandates_served=2,
        pledged_platform=(0.2, 0.3, 0.4),
        revealed_position=(0.25, 0.3, 0.4),
        base_threshold=0.1,
        legitimacy_capital=0.7,
        mandate_strength=0.6,
        street_pressure=1.5,
        petition_open_since_tick=4,
        petition_signers=frozenset({9, 3, 1}),
        petition_cooldown_until_tick=8,
        event_salience=0.3,
        sortition_seat_until_tick=20,
        sortition_terms_served=1,
        chamber_position=(0.5, 0.5, 0.5),
    )
    path = tmp_path / "checkpoint.json"
    _save(path, config, citizens=[citizen])

    restored = load_checkpoint(path).citizens[0]

    assert restored == citizen
    assert isinstance(restored.role, Role)
    assert isinstance(restored.office, Office)
    assert isinstance(restored.petition_signers, frozenset)
    assert isinstance(restored.issue_positions, tuple)
    assert isinstance(restored.pledged_platform, tuple)


def test_round_trip_preserves_citizens_with_none_optional_fields(tmp_path):
    # The shipped-default shape (a fresh, never-elected, never-seated
    # citizen) -- every Optional field at its None default, distinct from
    # the fully-populated citizen above.
    config = load_config()
    citizen = _citizen(0)
    path = tmp_path / "checkpoint.json"
    _save(path, config, citizens=[citizen])

    restored = load_checkpoint(path).citizens[0]

    assert restored == citizen
    assert restored.pledged_platform is None
    assert restored.revealed_position is None
    assert restored.chamber_position is None


def test_round_trip_preserves_citizen_order(tmp_path):
    config = load_config()
    citizens = [_citizen(i) for i in (5, 2, 8, 1)]
    path = tmp_path / "checkpoint.json"
    _save(path, config, citizens=citizens)

    restored = load_checkpoint(path).citizens

    assert [c.citizen_id for c in restored] == [5, 2, 8, 1]


def test_round_trip_preserves_parties(tmp_path):
    config = load_config()
    parties = [Party(party_id=0, platform=(0.1, 0.9)), Party(party_id=1, platform=(0.5, 0.5))]
    path = tmp_path / "checkpoint.json"
    _save(path, config, parties=parties)

    assert load_checkpoint(path).parties == parties


def test_round_trip_preserves_pending_rerun(tmp_path):
    config = load_config()
    pending = {"attempt": 2, "next_tick": 9, "barred_candidate_ids": [3, 1, 7]}
    path = tmp_path / "checkpoint.json"
    _save(path, config, pending_rerun=pending)

    assert load_checkpoint(path).pending_rerun == pending


def test_round_trip_preserves_pending_rerun_none(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, pending_rerun=None)

    assert load_checkpoint(path).pending_rerun is None


def test_round_trip_preserves_staggered_declared_cids(tmp_path):
    # Track E, 2026-09-11: the cross-tick gap between a staggered
    # declaration and its own nomination tick, one tick later.
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, staggered_declared_cids=[7, 3, 1])

    assert load_checkpoint(path).staggered_declared_cids == [7, 3, 1]


def test_round_trip_preserves_staggered_declared_cids_none(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, staggered_declared_cids=None)

    assert load_checkpoint(path).staggered_declared_cids is None


def test_a_checkpoint_written_before_track_e_shipped_loads_as_none(tmp_path):
    # A checkpoint from a crashed run predating this field has no such key
    # at all -- .get() must read that the same as an explicit null, not
    # raise KeyError.
    import json

    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config)
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["staggered_declared_cids"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_checkpoint(path).staggered_declared_cids is None


def test_round_trip_preserves_mobilized_last_tick_with_int_keys(tmp_path):
    # JSON object keys are always strings on the wire -- this is the one
    # field genuinely at risk of coming back with str keys instead of int.
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, mobilized_last_tick={5: 12, 30: 7})

    restored = load_checkpoint(path).mobilized_last_tick

    assert restored == {5: 12, 30: 7}
    assert all(isinstance(k, int) for k in restored)


def test_rng_state_round_trips_and_continues_the_same_stream(tmp_path):
    config = load_config()
    rupture_rng = _rng(42, draws=5)  # advance past the start, like a real mid-run stream
    expected_next = rupture_rng.random(10)  # what the ORIGINAL stream produces next
    rupture_rng = _rng(42, draws=5)  # rewind to the same position for the checkpoint

    path = tmp_path / "checkpoint.json"
    _save(path, config, rupture_rng=rupture_rng)

    restored = restore_rng(load_checkpoint(path).rupture_rng_state)
    actual_next = restored.random(10)

    assert (actual_next == expected_next).all()


def test_the_three_rng_streams_restore_independently(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(
        path, config,
        rupture_rng=_rng(1, draws=3), events_rng=_rng(2, draws=6), sortition_rng=_rng(3, draws=9),
    )
    cp = load_checkpoint(path)

    expected_rupture = _rng(1, draws=3).random(4)
    expected_events = _rng(2, draws=6).random(4)
    expected_sortition = _rng(3, draws=9).random(4)

    assert (restore_rng(cp.rupture_rng_state).random(4) == expected_rupture).all()
    assert (restore_rng(cp.events_rng_state).random(4) == expected_events).all()
    assert (restore_rng(cp.sortition_rng_state).random(4) == expected_sortition).all()


def test_save_is_atomic_no_tmp_file_left_behind(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config)

    assert path.exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_save_overwrites_a_previous_checkpoint_at_the_same_path(tmp_path):
    config = load_config()
    path = tmp_path / "checkpoint.json"
    _save(path, config, tick=3)
    _save(path, config, tick=8)

    assert load_checkpoint(path).tick == 8


def test_load_checkpoint_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_checkpoint(tmp_path / "does_not_exist.json")


# ── config_hash ──────────────────────────────────────────────────────────

def test_config_hash_is_stable_for_the_same_config():
    config = load_config()
    assert config_hash(config) == config_hash(config)


def test_config_hash_changes_when_a_simulation_parameter_changes():
    config = load_config()
    changed = dataclasses.replace(config, run=dataclasses.replace(config.run, seed=config.run.seed + 1))
    assert config_hash(config) != config_hash(changed)


def test_config_hash_changes_for_a_nested_section_field():
    config = load_config()
    changed = dataclasses.replace(
        config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.99)
    )
    assert config_hash(config) != config_hash(changed)


def test_config_hash_ignores_journal_output_dir():
    # A resumed run relocating its own output directory is legitimate --
    # the path is not a simulation parameter.
    config = load_config()
    relocated = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir="/elsewhere"))
    assert config_hash(config) == config_hash(relocated)
