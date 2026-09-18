"""Tests for Phase 4.5.a.8 — simulation_advanced on FastAPI (/api/v2/simulations)."""

import api.domain.simulations.advanced as advanced_module

CANDS = ["Alice", "Bob", "Charlie"]


class TestMonteCarlo:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/monte-carlo",
                        json={"num_runs": 5, "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["num_runs"] == 5 and "methods" in body

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/monte-carlo",
                        json={"num_runs": 5, "candidates": ["Solo"]})
        assert r.status_code == 400, r.text

    def test_500_and_logs_on_compute_failure(self, client, monkeypatch, caplog):
        def _boom(*a, **kw):
            raise RuntimeError("engine exploded")
        monkeypatch.setattr(advanced_module, "compare_all_methods_mc", _boom)
        with caplog.at_level("WARNING"):
            r = client.post("/api/v2/simulations/monte-carlo",
                            json={"num_runs": 5, "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 500
        assert "engine exploded" in r.json()["detail"]
        assert "simulation.monte_carlo.failed" in caplog.text


