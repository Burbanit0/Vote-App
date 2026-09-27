from __future__ import annotations

import time

import pytest

from llm_test_harness import registration, storage, trial


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_harness.db"


def _fake_env_runner(command):
    return ""


def _register_dummy(db_path):
    return registration.register("h", "c", 1, "b", db_path=db_path)


def test_record_trial_stores_a_successful_result(db_path):
    experiment = _register_dummy(db_path)
    result = trial.record_trial(
        experiment.experiment_id, 1,
        container_name="x",
        run_call=lambda: trial.TrialResult(ok=True, finish_reason="stop", decoded_tokens=42),
        env_runner=_fake_env_runner,
        db_path=db_path,
    )
    assert result.ok is True

    conn = storage.connect(db_path)
    rows = storage.get_trials(conn, experiment.experiment_id)
    conn.close()
    assert len(rows) == 1
    assert rows[0]["ok"] == 1
    assert rows[0]["decoded_tokens"] == 42


def test_record_trial_stores_a_failed_result(db_path):
    experiment = _register_dummy(db_path)
    trial.record_trial(
        experiment.experiment_id, 1,
        container_name="x",
        run_call=lambda: trial.TrialResult(ok=False, finish_reason="length", truncated=True, detail="oops"),
        env_runner=_fake_env_runner,
        db_path=db_path,
    )
    conn = storage.connect(db_path)
    rows = storage.get_trials(conn, experiment.experiment_id)
    conn.close()
    assert rows[0]["ok"] == 0
    assert rows[0]["truncated"] == 1
    assert rows[0]["detail"] == "oops"


def test_record_trial_captures_environment_before_and_after(db_path):
    experiment = _register_dummy(db_path)
    trial.record_trial(
        experiment.experiment_id, 1,
        container_name="x",
        run_call=lambda: trial.TrialResult(ok=True),
        env_runner=_fake_env_runner,
        db_path=db_path,
    )
    conn = storage.connect(db_path)
    rows = storage.get_trials(conn, experiment.experiment_id)
    conn.close()
    assert rows[0]["environment_before"] != ""
    assert rows[0]["environment_after"] != ""


def test_record_trial_measures_nonzero_latency(db_path):
    experiment = _register_dummy(db_path)

    def slow_call():
        time.sleep(0.05)
        return trial.TrialResult(ok=True)

    trial.record_trial(
        experiment.experiment_id, 1,
        container_name="x", run_call=slow_call,
        env_runner=_fake_env_runner, db_path=db_path,
    )
    conn = storage.connect(db_path)
    rows = storage.get_trials(conn, experiment.experiment_id)
    conn.close()
    assert rows[0]["latency_seconds"] >= 0.05


def test_record_trial_propagates_run_call_exceptions(db_path):
    # a real LLM call can raise (transport error, etc.) -- record_trial
    # does not swallow it into a fake TrialResult; the caller's own
    # run_call is responsible for turning failures into
    # TrialResult(ok=False, ...) deliberately, so a genuinely unexpected
    # exception is never misrepresented as a measured trial outcome.
    def raising_call():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        trial.record_trial(
            "exp-x", 1, container_name="x", run_call=raising_call,
            env_runner=_fake_env_runner, db_path=db_path,
        )
