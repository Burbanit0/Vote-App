"""Tests for Phase 4.5.a.7 — simulation_compare on FastAPI (/api/v2/simulations)."""

import api.domain.simulations.compare as compare_module

CANDS = ["Alice", "Bob", "Charlie"]


class TestManipulability:
    def test_happy_path(self, client):
        r = client.get("/api/v2/simulations/manipulability",
                       params={"num_candidates": 3, "num_voters": 60, "num_trials": 10})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["num_candidates"] == 3
        assert isinstance(body["results"], list) and body["results"]

    def test_specific_methods(self, client):
        r = client.get("/api/v2/simulations/manipulability",
                       params={"num_voters": 60, "num_trials": 10, "methods": "plurality,borda"})
        assert r.status_code == 200, r.text
        assert {m["method"] for m in r.json()["results"]} == {"plurality", "borda"}

    def test_500_and_logs_on_population_build_failure(self, client, monkeypatch, caplog):
        def _boom(*a, **kw):
            raise RuntimeError("engine exploded")
        monkeypatch.setattr(compare_module, "_build_population", _boom)
        with caplog.at_level("WARNING"):
            r = client.get("/api/v2/simulations/manipulability",
                           params={"num_candidates": 3, "num_voters": 60, "num_trials": 10})
        assert r.status_code == 500
        assert "engine exploded" in r.json()["detail"]
        assert "simulation.manipulability.population_build_failed" in caplog.text


class TestVoteSteps:
    def test_plurality(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "plurality", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        assert r.json()["method"] == "plurality"

    def test_approval_elects_the_most_approved(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "approval", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        scores = body["approval_scores"]
        assert body["winner"] == min(scores, key=lambda c: (-scores[c], c))

    def test_irv(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "irv", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        assert "rounds" in r.json()

    def test_borda(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "borda", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["method"] == "borda"
        # One step per rank, cumulative tally grows to cover every candidate.
        assert len(body["steps"]) == len(CANDS)
        assert set(body["steps"][-1]["tally"]) == set(CANDS)
        assert body["winner"] in CANDS

    def test_schulze(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "schulze", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["method"] == "schulze"
        assert set(body["duel_matrix"]) == set(CANDS)
        assert body["winner"] in CANDS

    def test_invalid_method_400(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "nonsense", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 400, r.text


