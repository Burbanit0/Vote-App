from __future__ import annotations

import pytest

from llm_test_harness import registration, storage


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_harness.db"


def test_register_writes_an_immutable_experiment(db_path):
    experiment = registration.register("h", "c", 10, "b", db_path=db_path)
    conn = storage.connect(db_path)
    row = storage.get_experiment(conn, experiment.experiment_id)
    conn.close()
    assert row is not None
    assert row["hypothesis"] == "h"
    assert row["planned_n"] == 10


def test_register_rejects_nonpositive_planned_n(db_path):
    with pytest.raises(ValueError, match="planned_n"):
        registration.register("h", "c", 0, "b", db_path=db_path)


def test_register_warns_when_planned_n_is_too_small(db_path, capsys):
    registration.register(
        "h", "c", 3, "b", db_path=db_path,
        expected_effect_rate=0.5, decision_threshold_for_sizing=0.1,
    )
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_register_does_not_warn_when_planned_n_is_sufficient(db_path, capsys):
    registration.register(
        "h", "c", 100, "b", db_path=db_path,
        expected_effect_rate=0.5, decision_threshold_for_sizing=0.1,
    )
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out


def test_register_never_blocks_even_with_an_insufficient_n(db_path):
    # the design brief's own explicit requirement: warning, not a hard block.
    experiment = registration.register(
        "h", "c", 1, "b", db_path=db_path,
        expected_effect_rate=0.5, decision_threshold_for_sizing=0.1,
    )
    assert experiment.planned_n == 1


def test_two_registrations_get_distinct_experiment_ids(db_path):
    e1 = registration.register("h", "c", 1, "b", db_path=db_path)
    e2 = registration.register("h", "c", 1, "b", db_path=db_path)
    assert e1.experiment_id != e2.experiment_id


def test_register_stores_structured_decision_fields(db_path):
    experiment = registration.register(
        "h", "c", 5, "b", db_path=db_path,
        threshold=0.2, comparison="gt", metric="failure_rate",
    )
    assert experiment.threshold == 0.2
    assert experiment.comparison == "gt"
    assert experiment.metric == "failure_rate"


def test_register_without_sizing_args_prints_no_warning(db_path, capsys):
    registration.register("h", "c", 1, "b", db_path=db_path)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
