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


def test_validate_multiwinner_candidates_rejects_fewer_than_two():
    # Both HTTP callers (/stv, /multiwinner_compare) already enforce
    # min_length=2 candidates at the Pydantic schema layer, so this branch
    # is unreachable through the API today — but the helper is written to
    # be a standalone safety net for any future caller, so it gets its own
    # direct unit test rather than an HTTP-level one.
    error = workers_mechanisms._validate_multiwinner_candidates(
        [{"name": "Solo", "x": 0.0, "y": 0.0}], num_seats=2
    )
    assert error == ({"error": "At least 2 candidates required"}, 400)


def test_validate_multiwinner_candidates_accepts_valid_input():
    cand_specs = [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
    ]
    assert workers_mechanisms._validate_multiwinner_candidates(cand_specs, num_seats=1) is None
