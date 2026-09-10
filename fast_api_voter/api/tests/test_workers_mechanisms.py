"""Tests for api.domain.election.workers_mechanisms — abstention winners-by-method fallback."""
import api.domain.election.workers_mechanisms as workers_mechanisms


def test_abstention_worker_falls_back_and_logs_on_compare_failure(monkeypatch, caplog):
    def _boom(*a, **kw):
        raise RuntimeError("compare exploded")

    monkeypatch.setattr(workers_mechanisms, "compare_all_methods", _boom)

    with caplog.at_level("WARNING"):
        body, status = workers_mechanisms._abstention_worker({"num_voters": 50, "seed": 1})

    assert status == 200
    assert body["sincere_winners_by_method"] == {}
    assert body["winners_by_method"] == {}
    assert "workers_mechanisms.abstention_winners_by_method_failed" in caplog.text
