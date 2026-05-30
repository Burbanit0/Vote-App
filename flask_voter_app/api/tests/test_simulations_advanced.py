"""Tests for Phase 4.5.a.8 — simulation_advanced on FastAPI (/api/v2/simulations)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

CANDS = ["Alice", "Bob", "Charlie"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestBandwagon:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/bandwagon",
                        json={"num_voters": 60, "candidates": CANDS, "num_rounds": 3, "seed": 1})
        assert r.status_code == 200, r.text

    def test_too_few_candidates_400(self, client):
        r = client.post("/api/v2/simulations/bandwagon",
                        json={"num_voters": 60, "candidates": ["Solo"]})
        assert r.status_code == 400, r.text


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


class TestMultiwinner:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/multiwinner",
                        json={"party_votes": {"A": 40, "B": 35, "C": 25}, "num_seats": 10})
        assert r.status_code == 200, r.text
        assert r.json()["num_seats"] == 10

    def test_empty_party_votes_400(self, client):
        r = client.post("/api/v2/simulations/multiwinner", json={"party_votes": {}, "num_seats": 10})
        assert r.status_code == 400, r.text


class TestRealElections:
    def test_list(self, client):
        r = client.get("/api/v2/simulations/real-elections")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list) and r.json()


class TestBlankHistory:
    def test_france(self, client):
        r = client.get("/api/v2/simulations/blank-history", params={"country": "france"})
        assert r.status_code == 200, r.text
        assert "series" in r.json()

    def test_missing_country_400(self, client):
        r = client.get("/api/v2/simulations/blank-history")
        assert r.status_code == 400, r.text

    def test_unknown_country_404(self, client):
        r = client.get("/api/v2/simulations/blank-history", params={"country": "atlantis"})
        assert r.status_code == 404, r.text


class TestRealElection:
    def test_happy_path(self, client):
        key = client.get("/api/v2/simulations/real-elections").json()[0]["key"]
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": key, "num_voters": 200})
        assert r.status_code == 200, r.text

    def test_missing_name_400(self, client):
        r = client.post("/api/v2/simulations/real-election", json={"num_voters": 200})
        assert r.status_code == 400, r.text

    def test_unknown_election_404(self, client):
        r = client.post("/api/v2/simulations/real-election",
                        json={"election_name": "no_such_election", "num_voters": 200})
        assert r.status_code == 404, r.text


class TestConstitutionalScenario:
    initial = {
        "candidates": [
            {"name": "A", "ideology": -0.5, "positions": {"economy": 0.3}},
            {"name": "B", "ideology": 0.5, "positions": {"economy": 0.7}},
        ],
        "electorate": {"num_voters": 60, "ideology_preset": "random"},
        "blank_rule": "competitive",
    }

    def test_new_election(self, client):
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": self.initial, "scenario_type": "new_election"})
        assert r.status_code == 200, r.text
        assert r.json()["scenario_type"] == "new_election"

    def test_unknown_scenario_type_400(self, client):
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": self.initial, "scenario_type": "bogus"})
        assert r.status_code == 400, r.text

    def test_too_few_candidates_400(self, client):
        bad = {**self.initial, "candidates": [self.initial["candidates"][0]]}
        r = client.post("/api/v2/simulations/constitutional-scenario",
                        json={"initial_election": bad, "scenario_type": "new_election"})
        assert r.status_code == 400, r.text


class TestBlankContagion:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/blank-contagion",
                        json={"num_voters": 60, "num_rounds": 5, "seed": 1})
        assert r.status_code == 200, r.text
