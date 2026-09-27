from __future__ import annotations

import sqlite3

import pytest

from llm_test_harness import storage


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_harness.db"


def _experiment_row(experiment_id="exp-1", **overrides):
    row = {
        "experiment_id": experiment_id,
        "hypothesis": "h",
        "decision_criterion": "c",
        "threshold": None,
        "comparison": None,
        "metric": None,
        "planned_n": 10,
        "budget_description": "b",
        "registered_at": "2026-08-19T00:00:00+00:00",
        "git_commit": "abc",
    }
    row.update(overrides)
    return row


def _trial_row(experiment_id="exp-1", trial_number=1, **overrides):
    row = {
        "experiment_id": experiment_id,
        "trial_number": trial_number,
        "started_at": "2026-08-19T00:00:00+00:00",
        "finished_at": "2026-08-19T00:00:01+00:00",
        "environment_before": "{}",
        "environment_after": "{}",
        "ok": 1,
        "finish_reason": "stop",
        "truncated": 0,
        "latency_seconds": 1.0,
        "decoded_tokens": 50,
        "detail": "",
    }
    row.update(overrides)
    return row


def test_connect_creates_the_schema(db_path):
    conn = storage.connect(db_path)
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"experiments", "trials"} <= tables
    conn.close()


def test_insert_and_get_experiment_round_trips(db_path):
    conn = storage.connect(db_path)
    storage.insert_experiment(conn, _experiment_row())
    row = storage.get_experiment(conn, "exp-1")
    assert row is not None
    assert row["hypothesis"] == "h"
    conn.close()


def test_get_experiment_returns_none_for_unknown_id(db_path):
    conn = storage.connect(db_path)
    assert storage.get_experiment(conn, "does-not-exist") is None
    conn.close()


def test_duplicate_experiment_id_raises_integrity_error(db_path):
    conn = storage.connect(db_path)
    storage.insert_experiment(conn, _experiment_row())
    with pytest.raises(sqlite3.IntegrityError):
        storage.insert_experiment(conn, _experiment_row())
    conn.close()


def test_insert_and_get_trials_round_trips_in_trial_number_order(db_path):
    conn = storage.connect(db_path)
    storage.insert_experiment(conn, _experiment_row())
    storage.insert_trial(conn, _trial_row(trial_number=2))
    storage.insert_trial(conn, _trial_row(trial_number=1))
    trials = storage.get_trials(conn, "exp-1")
    assert [t["trial_number"] for t in trials] == [1, 2]
    conn.close()


def test_get_trials_scoped_to_its_own_experiment_id(db_path):
    conn = storage.connect(db_path)
    storage.insert_experiment(conn, _experiment_row(experiment_id="exp-1"))
    storage.insert_experiment(conn, _experiment_row(experiment_id="exp-2"))
    storage.insert_trial(conn, _trial_row(experiment_id="exp-1"))
    storage.insert_trial(conn, _trial_row(experiment_id="exp-2"))
    assert len(storage.get_trials(conn, "exp-1")) == 1
    conn.close()


def test_connect_creates_parent_directory_if_missing(tmp_path):
    nested = tmp_path / "a" / "b" / "harness.db"
    conn = storage.connect(nested)
    assert nested.is_file()
    conn.close()


def test_trial_insert_rejects_an_unknown_experiment_id(db_path):
    # foreign_keys pragma is on -- a trial naming a never-registered
    # experiment_id must fail loudly, not insert an orphaned row.
    conn = storage.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        storage.insert_trial(conn, _trial_row(experiment_id="never-registered"))
    conn.close()


def test_no_update_experiment_function_exists():
    # structural pin for the immutability contract this module's own
    # docstring commits to -- fails loudly if someone ever adds one.
    assert not hasattr(storage, "update_experiment")
