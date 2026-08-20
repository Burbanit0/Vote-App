from __future__ import annotations

import pytest

from llm_test_harness import registration, report, trial


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_harness.db"


def _fake_env_runner(command):
    return ""


def test_generate_report_raises_for_unknown_experiment(db_path):
    with pytest.raises(ValueError, match="no experiment registered"):
        report.generate_report("does-not-exist", db_path=db_path)


def test_generate_report_with_no_trials_yet(db_path):
    experiment = registration.register("h", "c", 5, "b", db_path=db_path)
    text = report.generate_report(experiment.experiment_id, db_path=db_path)
    assert "No trials recorded yet" in text
    assert experiment.experiment_id in text


def test_generate_report_mechanically_evaluates_a_structured_criterion_fail_when_below_threshold(db_path):
    experiment = registration.register(
        "h", "c", 3, "b", db_path=db_path,
        threshold=0.5, comparison="gt", metric="failure_rate",
    )
    for i in range(1, 4):
        trial.record_trial(
            experiment.experiment_id, i, container_name="x",
            run_call=lambda: trial.TrialResult(ok=True),
            env_runner=_fake_env_runner, db_path=db_path,
        )
    text = report.generate_report(experiment.experiment_id, db_path=db_path)
    assert "FAIL" in text  # failure_rate=0.0, not > 0.5
    assert "0.000" in text


def test_generate_report_mechanically_evaluates_a_structured_criterion_pass_when_above_threshold(db_path):
    experiment = registration.register(
        "h", "c", 2, "b", db_path=db_path,
        threshold=0.5, comparison="gt", metric="failure_rate",
    )
    for i in (1, 2):
        trial.record_trial(
            experiment.experiment_id, i, container_name="x",
            run_call=lambda: trial.TrialResult(ok=False),
            env_runner=_fake_env_runner, db_path=db_path,
        )
    text = report.generate_report(experiment.experiment_id, db_path=db_path)
    assert "PASS" in text  # failure_rate=1.0 > 0.5


def test_generate_report_without_structured_criterion_shows_free_text_only(db_path):
    experiment = registration.register("h", "the model itself should judge this", 1, "b", db_path=db_path)
    trial.record_trial(
        experiment.experiment_id, 1, container_name="x",
        run_call=lambda: trial.TrialResult(ok=True),
        env_runner=_fake_env_runner, db_path=db_path,
    )
    text = report.generate_report(experiment.experiment_id, db_path=db_path)
    assert "evaluate the criterion above" in text
    assert "the model itself should judge this" in text


def test_generate_report_includes_planned_vs_actual_n(db_path):
    experiment = registration.register("h", "c", 10, "b", db_path=db_path)
    trial.record_trial(
        experiment.experiment_id, 1, container_name="x",
        run_call=lambda: trial.TrialResult(ok=True),
        env_runner=_fake_env_runner, db_path=db_path,
    )
    text = report.generate_report(experiment.experiment_id, db_path=db_path)
    assert "Planned n**: 10" in text
    assert "actual n**: 1" in text
