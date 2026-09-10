"""Tests for api.domain.election.workers_advanced — compare_all_methods fallbacks."""
import api.domain.election.workers_advanced as workers_advanced


def test_dt_winners_by_method_falls_back_and_logs_on_failure(monkeypatch, caplog):
    def _boom(*a, **kw):
        raise RuntimeError("compare exploded")

    monkeypatch.setattr(workers_advanced, "compare_all_methods", _boom)

    with caplog.at_level("WARNING"):
        result = workers_advanced._dt_winners_by_method(
            [[{"id": 1}], [{"id": 2}]], candidates=[], issues={},
        )

    assert result == [{}, {}]
    assert "workers_advanced.dt_winners_by_method_failed" in caplog.text


def test_compulsory_voting_worker_falls_back_and_logs_on_compare_failure(monkeypatch, caplog):
    def _boom(*a, **kw):
        raise RuntimeError("compare exploded")

    monkeypatch.setattr(workers_advanced, "compare_all_methods", _boom)

    with caplog.at_level("WARNING"):
        body, status = workers_advanced._compulsory_voting_worker({"num_voters": 50, "seed": 1})

    assert status == 200
    assert body["voluntary"]["winners_by_method"] == {}
    assert body["compulsory"]["winners_by_method"] == {}
    assert "workers_advanced.compulsory_voting_winners_by_method_failed" in caplog.text
