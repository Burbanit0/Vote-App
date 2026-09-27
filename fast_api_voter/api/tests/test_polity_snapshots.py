"""snapshots.py — per-simulated-year citizen state (Phase 6,
plan-flagship-30y-run.md, design doc §16.4).
"""
import json

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.snapshots import expected_snapshot_rows, is_snapshot_tick, write_snapshot


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


# ── is_snapshot_tick ─────────────────────────────────────────────────────

def test_is_snapshot_tick_true_at_year_boundaries():
    assert is_snapshot_tick(0, ticks_per_year=4) is True
    assert is_snapshot_tick(4, ticks_per_year=4) is True
    assert is_snapshot_tick(8, ticks_per_year=4) is True


def test_is_snapshot_tick_false_mid_year():
    assert is_snapshot_tick(1, ticks_per_year=4) is False
    assert is_snapshot_tick(2, ticks_per_year=4) is False
    assert is_snapshot_tick(3, ticks_per_year=4) is False
    assert is_snapshot_tick(7, ticks_per_year=4) is False


def test_is_snapshot_tick_with_ticks_per_year_one():
    # Every tick is a year boundary when ticks_per_year=1 -- not a config
    # this project ships, but the function should not special-case it.
    assert all(is_snapshot_tick(t, ticks_per_year=1) for t in range(5))


# ── expected_snapshot_rows ───────────────────────────────────────────────

def test_expected_snapshot_rows_at_tick_zero_is_one_years_worth():
    assert expected_snapshot_rows(0, ticks_per_year=4, population_size=500) == 500


def test_expected_snapshot_rows_scales_with_years_reached():
    # tick=8 -> years 0, 1, 2 reached (3 snapshot ticks: 0, 4, 8)
    assert expected_snapshot_rows(8, ticks_per_year=4, population_size=500) == 1500


def test_expected_snapshot_rows_mid_year_does_not_add_a_partial_row():
    # tick=6 has NOT reached year 2's own boundary (tick 8) -- still only
    # years 0 and 1 (ticks 0 and 4) have fired a snapshot.
    assert expected_snapshot_rows(6, ticks_per_year=4, population_size=500) == 1000
    assert expected_snapshot_rows(7, ticks_per_year=4, population_size=500) == 1000


# ── write_snapshot ───────────────────────────────────────────────────────

def test_write_snapshot_writes_one_row_per_citizen(tmp_path):
    path = tmp_path / "snapshots.jsonl"
    citizens = [_citizen(0), _citizen(1), _citizen(2)]
    write_snapshot(path, citizens, tick=0, ticks_per_year=4)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["citizen_id"] for line in lines] == [0, 1, 2]


def test_write_snapshot_computes_year_from_tick(tmp_path):
    path = tmp_path / "snapshots.jsonl"
    write_snapshot(path, [_citizen(0)], tick=12, ticks_per_year=4)

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["year"] == 3
    assert row["tick"] == 12


def test_write_snapshot_captures_every_documented_field(tmp_path):
    path = tmp_path / "snapshots.jsonl"
    citizen = _citizen(
        7,
        issue_positions=(0.2, 0.4, 0.6),
        party_affiliation=2,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        event_salience=0.35,
        pledged_platform=(0.25, 0.45, 0.6),
        revealed_position=(0.3, 0.5, 0.65),
    )
    write_snapshot(path, [citizen], tick=0, ticks_per_year=4)

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {
        "year": 0,
        "tick": 0,
        "citizen_id": 7,
        "issue_positions": [0.2, 0.4, 0.6],
        "party_affiliation": 2,
        "role": "elu",
        "office": "president",
        "event_salience": 0.35,
        "pledged_platform": [0.25, 0.45, 0.6],
        "revealed_position": [0.3, 0.5, 0.65],
    }


def test_write_snapshot_null_platform_for_a_plain_elector(tmp_path):
    path = tmp_path / "snapshots.jsonl"
    write_snapshot(path, [_citizen(0)], tick=0, ticks_per_year=4)

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["pledged_platform"] is None
    assert row["revealed_position"] is None
    assert row["role"] == "electeur"
    assert row["office"] == "aucun"


def test_write_snapshot_appends_across_calls(tmp_path):
    path = tmp_path / "snapshots.jsonl"
    write_snapshot(path, [_citizen(0)], tick=0, ticks_per_year=4)
    write_snapshot(path, [_citizen(0)], tick=4, ticks_per_year=4)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["year"] for line in lines] == [0, 1]


def test_write_snapshot_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "run" / "snapshots.jsonl"
    write_snapshot(path, [_citizen(0)], tick=0, ticks_per_year=4)
    assert path.exists()


def test_two_snapshot_writes_with_the_same_input_are_byte_identical(tmp_path):
    citizens = [_citizen(i) for i in range(5)]
    path_a, path_b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_snapshot(path_a, citizens, tick=4, ticks_per_year=4)
    write_snapshot(path_b, citizens, tick=4, ticks_per_year=4)
    assert path_a.read_bytes() == path_b.read_bytes()
