"""Tests for Phase 4.5.a.7 — simulation_compare on FastAPI (/api/v2/simulations)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

CANDS = ["Alice", "Bob", "Charlie"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestCompare:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/compare",
                        json={"num_voters": 60, "candidates": CANDS})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "methods" in body and "plurality" in body["methods"]
        assert body["information_model"]["enabled"] is False

    def test_blank_vote(self, client):
        r = client.post("/api/v2/simulations/compare", json={
            "num_voters": 60, "candidates": CANDS,
            "blank_vote": True, "blank_rule": "threshold_30",
        })
        assert r.status_code == 200, r.text
        assert "blank_rule_applied" in next(iter(r.json()["methods"].values()))

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/compare",
                        json={"num_voters": 60, "candidates": ["Solo"]})
        assert r.status_code == 400, r.text

    def test_unknown_blank_rule_400(self, client):
        r = client.post("/api/v2/simulations/compare", json={
            "num_voters": 60, "candidates": CANDS, "blank_rule": "nonsense",
        })
        assert r.status_code == 400, r.text


class TestStrategicImpact:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/strategic-impact", json={
            "num_voters": 60, "candidates": CANDS, "strategic_percentages": [0, 50],
        })
        assert r.status_code == 200, r.text
        assert len(r.json()["results"]) == 2


class TestCondorcetMatrix:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/condorcet-matrix",
                        json={"num_voters": 60, "candidates": CANDS})
        assert r.status_code == 200, r.text


class TestSensitivity:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/sensitivity", json={
            "base_config": {"num_voters": 60, "candidates": CANDS},
            "variable": "num_voters", "values": [50, 80],
        })
        assert r.status_code == 200, r.text
        assert len(r.json()["results"]) == 2

    def test_no_values_400(self, client):
        r = client.post("/api/v2/simulations/sensitivity", json={
            "base_config": {"candidates": CANDS}, "variable": "num_voters", "values": [],
        })
        assert r.status_code == 400, r.text


class TestArrowCriteria:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/arrow-criteria",
                        json={"num_voters": 60, "candidates": CANDS})
        assert r.status_code == 200, r.text


class TestScenario:
    payload = {
        "candidates": [
            {"name": "A", "ideology": -0.5, "positions": {"economy": 0.3}},
            {"name": "B", "ideology": 0.5, "positions": {"economy": 0.7}},
        ],
        "electorate": {"num_voters": 60, "ideology_preset": "random"},
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/scenario", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "without_blank" in body and "with_blank" in body

    def test_too_few_real_candidates_400(self, client):
        bad = {**self.payload, "candidates": [self.payload["candidates"][0]]}
        r = client.post("/api/v2/simulations/scenario", json=bad)
        assert r.status_code == 400, r.text


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


class TestVoteSteps:
    def test_plurality(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "plurality", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        assert r.json()["method"] == "plurality"

    def test_irv(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "irv", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 200, r.text
        assert "rounds" in r.json()

    def test_invalid_method_400(self, client):
        r = client.post("/api/v2/simulations/vote-steps",
                        json={"method": "nonsense", "num_voters": 50, "candidates": CANDS})
        assert r.status_code == 400, r.text


class TestIdeologyMap:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/ideology-map", json={
            "num_voters": 50,
            "candidates": [{"name": "A", "x": -0.5, "y": 0.0}, {"name": "B", "x": 0.5, "y": 0.0}],
            "method_a": "plurality", "method_b": "schulze",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "voters" in body and len(body["voters"]) == 50

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/ideology-map",
                        json={"num_voters": 50, "candidates": [{"name": "A", "x": 0, "y": 0}]})
        assert r.status_code == 400, r.text
