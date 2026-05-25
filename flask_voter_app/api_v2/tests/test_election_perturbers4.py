"""Tests for Phase 3 batch 6:
/api/v2/election/{affective-polarization, demographic-turnout, compulsory-voting, party-dynamics}."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]


# ── /affective-polarization ─────────────────────────────────────────────────

class TestAffectivePolarization:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "affect_hostility": 0.5, "camp_threshold": 0.1,
        "num_simulations": 5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/affective-polarization", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("sincere_results", "affective_results", "winner_changed",
                  "affect_curve", "candidate_camps"):
            assert k in r.json()

    def test_rejects_hostility_above_1(self, client):
        bad = {**self.payload, "affect_hostility": 1.5}
        assert client.post("/api/v2/election/affective-polarization",
                           json=bad).status_code == 422

    def test_rejects_too_many_simulations(self, client):
        bad = {**self.payload, "num_simulations": 99}
        assert client.post("/api/v2/election/affective-polarization",
                           json=bad).status_code == 422


# ── /demographic-turnout ────────────────────────────────────────────────────

class TestDemographicTurnout:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "method": "plurality", "correct_for_turnout": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/demographic-turnout", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("biased_result", "corrected_result", "winner_changed",
                  "representation_gap", "demographic_breakdown"):
            assert k in r.json()

    def test_accepts_explicit_demographic_profile(self, client):
        ok = {**self.payload, "demographic_profile": {
            "age_distribution": [0.3, 0.4, 0.3],
            "turnout_by_age":   [0.5, 0.7, 0.9],
            "ideology_by_age":  [-0.1, 0.0, 0.2],
        }}
        r = client.post("/api/v2/election/demographic-turnout", json=ok)
        assert r.status_code == 200

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/demographic-turnout",
                           json=bad).status_code == 422


# ── /compulsory-voting ──────────────────────────────────────────────────────

class TestCompulsoryVoting:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "voluntary_turnout":   0.65,
        "compulsory_turnout":  0.92,
        "reluctant_null_rate": 0.04,
        "reluctant_random_pct": 0.08,
        "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/compulsory-voting", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("voluntary", "compulsory", "winner_changed",
                  "representation_improvement", "quality_degradation"):
            assert k in r.json()

    def test_rejects_voluntary_turnout_above_0_9(self, client):
        bad = {**self.payload, "voluntary_turnout": 0.95}
        assert client.post("/api/v2/election/compulsory-voting",
                           json=bad).status_code == 422

    def test_rejects_compulsory_turnout_below_0_7(self, client):
        bad = {**self.payload, "compulsory_turnout": 0.5}
        assert client.post("/api/v2/election/compulsory-voting",
                           json=bad).status_code == 422


# ── /party-dynamics ─────────────────────────────────────────────────────────

class TestPartyDynamics:
    payload = {
        "num_voters": 200, "seed": 42, "num_elections": 5,
        "method": "plurality", "survival_threshold": 0.05,
        "emergence_probability": 0.10, "hotelling_adaptation": 0.10,
        "tactical_voting": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/party-dynamics", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("elections", "final_system", "effective_parties_curve",
                  "duverger_confirmed"):
            assert k in r.json()

    def test_accepts_explicit_initial_parties(self, client):
        ok = {**self.payload, "initial_parties": [
            {"name": "P1", "x": -0.6, "y": 0.0, "support_pct": 0.4},
            {"name": "P2", "x":  0.6, "y": 0.0, "support_pct": 0.6},
        ]}
        r = client.post("/api/v2/election/party-dynamics", json=ok)
        assert r.status_code == 200

    def test_rejects_survival_threshold_above_0_2(self, client):
        bad = {**self.payload, "survival_threshold": 0.5}
        assert client.post("/api/v2/election/party-dynamics",
                           json=bad).status_code == 422

    def test_rejects_too_many_elections(self, client):
        bad = {**self.payload, "num_elections": 99}
        assert client.post("/api/v2/election/party-dynamics",
                           json=bad).status_code == 422
