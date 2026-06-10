"""Tests for Phase 3 batch 5: /api/v2/election/{jury, hotelling, polarization, sortition}."""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]


# ── /jury ───────────────────────────────────────────────────────────────────

class TestJury:
    payload = {
        "num_voters": 50, "num_options": 2,
        "correct_option_index": 0, "voter_competence": 0.7,
        "num_simulations": 50, "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/jury", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("theoretical_accuracy", "methods", "best_method",
                  "voter_competence", "competence_curve"):
            assert k in r.json()

    def test_rejects_competence_below_0_5(self, client):
        bad = {**self.payload, "voter_competence": 0.4}
        assert client.post("/api/v2/election/jury", json=bad).status_code == 422

    def test_rejects_num_options_above_5(self, client):
        bad = {**self.payload, "num_options": 99}
        assert client.post("/api/v2/election/jury", json=bad).status_code == 422


# ── /hotelling ──────────────────────────────────────────────────────────────

class TestHotelling:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "method": "plurality", "num_iterations": 3, "step_size": 0.05,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/hotelling", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("iterations", "converged", "final_positions",
                  "equilibrium_type", "method"):
            assert k in r.json()

    def test_rejects_step_size_above_0_15(self, client):
        bad = {**self.payload, "step_size": 0.5}
        assert client.post("/api/v2/election/hotelling", json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/hotelling", json=bad).status_code == 422


# ── /polarization ───────────────────────────────────────────────────────────

class TestPolarization:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "num_simulations": 5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/polarization", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("results", "key_findings"):
            assert k in r.json()

    def test_rejects_too_many_simulations(self, client):
        bad = {**self.payload, "num_simulations": 99}
        assert client.post("/api/v2/election/polarization", json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/polarization", json=bad).status_code == 422

    def test_rejects_too_many_candidates(self, client):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(9)]
        assert client.post("/api/v2/election/polarization",
                           json={**self.payload, "candidates": many}).status_code == 422


# ── /sortition ──────────────────────────────────────────────────────────────

class TestSortition:
    payload = {
        "candidates": CANDS, "num_voters": 100, "assembly_size": 20,
        "seed": 42, "method": "plurality",
        "num_simulations": 5, "realistic_candidates": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/sortition", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("population", "assemblies", "variance",
                  "winner_by_method", "consensus_possible"):
            assert k in r.json()

    def test_rejects_assembly_size_too_large(self, client):
        bad = {**self.payload, "assembly_size": 99_999}
        assert client.post("/api/v2/election/sortition", json=bad).status_code == 422

    def test_accepts_explicit_stratification(self, client):
        ok = {**self.payload, "stratification": {
            "age_groups": [0.3, 0.4, 0.3],
            "gender_parity": True,
            "education_quota": False,
        }}
        r = client.post("/api/v2/election/sortition", json=ok)
        assert r.status_code == 200
