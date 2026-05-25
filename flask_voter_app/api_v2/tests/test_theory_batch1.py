"""Tests for Phase 4 batch 1:
/api/v2/theory/{arrow, iia-rate, plott-chaos, judgment-aggregation}."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── /arrow ──────────────────────────────────────────────────────────────────

class TestArrow:
    def test_happy_path_plurality(self, client):
        r = client.post("/api/v2/theory/arrow",
                        json={"method": "plurality", "seed": 42})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["method"] == "plurality"
        assert body["tradeoff_type"] == "majority_focus"
        for ax in ("iia", "pareto", "transitivity", "non_dictatorship"):
            assert ax in body["violations"]
            assert "violated" in body["violations"][ax]
        # Plurality violates IIA, satisfies the other three
        assert body["violations"]["iia"]["violated"] is True
        assert body["violations"]["pareto"]["violated"] is False
        assert body["violations"]["transitivity"]["violated"] is False
        assert body["violations"]["iia"]["counterexample"] is not None

    def test_condorcet_violates_transitivity(self, client):
        r = client.post("/api/v2/theory/arrow", json={"method": "condorcet"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["violations"]["transitivity"]["violated"] is True
        assert body["violations"]["transitivity"]["counterexample"] is not None
        assert body["tradeoff_type"] == "condorcet_focus"

    def test_rejects_extra_field(self, client):
        r = client.post("/api/v2/theory/arrow",
                        json={"method": "plurality", "bogus": 1})
        assert r.status_code == 422


# ── /iia-rate ───────────────────────────────────────────────────────────────

class TestIIARate:
    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/iia-rate",
                        json={"method": "plurality", "max_candidates": 5,
                              "num_trials": 50, "seed": 42})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["method"] == "plurality"
        assert len(body["curve"]) == 4   # n=2..5
        for pt in body["curve"]:
            assert "n_candidates" in pt
            assert 0.0 <= pt["violation_rate"] <= 1.0

    def test_rejects_too_many_candidates(self, client):
        r = client.post("/api/v2/theory/iia-rate",
                        json={"method": "plurality", "max_candidates": 99})
        assert r.status_code == 422

    def test_rejects_too_few_trials(self, client):
        r = client.post("/api/v2/theory/iia-rate",
                        json={"num_trials": 1})
        assert r.status_code == 422


# ── /plott-chaos ────────────────────────────────────────────────────────────

class TestPlottChaos:
    payload = {
        "num_voters": 5, "num_dimensions": 2, "seed": 42,
        "target_policy": [0.6, 0.6],
        "start_policy": [-0.6, -0.6],
        "max_steps": 10,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/plott-chaos", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("condorcet_winner_exists", "top_cycle", "chaos_path",
                  "alternative_path", "voter_ideal_points", "pedagogical_note"):
            assert k in body
        assert "size" in body["top_cycle"]
        assert "center" in body["top_cycle"]
        # chaos_path uses alias 'from' on input/output
        assert "from" in body["chaos_path"]
        assert len(body["voter_ideal_points"]) == 5

    def test_rejects_too_few_voters(self, client):
        bad = {**self.payload, "num_voters": 1}
        assert client.post("/api/v2/theory/plott-chaos",
                           json=bad).status_code == 422

    def test_rejects_too_many_dimensions(self, client):
        bad = {**self.payload, "num_dimensions": 5}
        assert client.post("/api/v2/theory/plott-chaos",
                           json=bad).status_code == 422


# ── /judgment-aggregation ──────────────────────────────────────────────────

class TestJudgmentAggregation:
    def test_happy_path_legal(self, client):
        r = client.post("/api/v2/theory/judgment-aggregation",
                        json={"num_voters": 20, "seed": 42,
                              "scenario": "legal"})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("scenario", "scenario_name", "propositions",
                  "collective_coherent", "incoherences",
                  "voter_coherence_rate", "paradox_severity",
                  "resolution_methods", "pedagogical_note"):
            assert k in body
        assert body["scenario"] == "legal"
        # All voter types are individually coherent in pre-defined scenarios
        assert body["voter_coherence_rate"] == 1.0
        assert len(body["propositions"]) == 3

    def test_accepts_climate_scenario(self, client):
        r = client.post("/api/v2/theory/judgment-aggregation",
                        json={"scenario": "climate", "num_voters": 15})
        assert r.status_code == 200, r.text
        assert r.json()["scenario"] == "climate"

    def test_unknown_scenario_falls_back_to_legal(self, client):
        # Worker silently falls back to 'legal' for unknown scenarios.
        r = client.post("/api/v2/theory/judgment-aggregation",
                        json={"scenario": "nope"})
        assert r.status_code == 200, r.text
        # Scenario echoed back is the user-supplied one, but scenario_name
        # is the legal one (since lookup fell back).
        assert r.json()["scenario_name"] == "Responsabilité contractuelle"

    def test_rejects_too_many_voters(self, client):
        r = client.post("/api/v2/theory/judgment-aggregation",
                        json={"num_voters": 999})
        assert r.status_code == 422
