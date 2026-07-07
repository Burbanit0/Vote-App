"""Tests for the 4 Perturber endpoints migrated in Phase 3 batch 3:
/api/v2/election/{nota, ballot-complexity, shy-voter, electoral-fatigue}.

Bundled in a single file because each endpoint is small and tested
for the same 3 properties: happy-path response, response shape, and
422 on invalid input.
"""
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


# ── /nota ────────────────────────────────────────────────────────────────────

class TestNota:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "nota_threshold": 0.3, "nota_rule": "invalidate", "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/nota", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("nota_pct", "election_valid", "winner", "nota_curve",
                  "method_comparison", "pedagogical_note", "nota_rule"):
            assert k in r.json()

    def test_curve_has_20_points(self, client):
        body = client.post("/api/v2/election/nota", json=self.payload).json()
        assert len(body["nota_curve"]) == 20

    def test_rejects_invalid_threshold(self, client):
        bad = {**self.payload, "nota_threshold": 1.5}
        assert client.post("/api/v2/election/nota", json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/nota", json=bad).status_code == 422


# ── /ballot-complexity ──────────────────────────────────────────────────────

class TestBallotComplexity:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "education_level": 0.7, "first_time_voter_pct": 0.1,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/ballot-complexity", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("results", "candidate_count_curve",
                  "most_inclusive_method", "least_inclusive_method"):
            assert k in r.json()

    def test_rejects_education_above_1(self, client):
        bad = {**self.payload, "education_level": 1.5}
        assert client.post("/api/v2/election/ballot-complexity", json=bad).status_code == 422

    def test_rejects_negative_ftv_pct(self, client):
        bad = {**self.payload, "first_time_voter_pct": -0.1}
        assert client.post("/api/v2/election/ballot-complexity", json=bad).status_code == 422


# ── /shy-voter ──────────────────────────────────────────────────────────────

class TestShyVoter:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "shy_candidate_idx": 0, "social_desirability_factor": 0.4,
        "num_polls": 5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/shy-voter", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("real_winner", "poll_winner", "polls_wrong",
                  "shy_candidate", "social_desirability_curve"):
            assert k in r.json()

    def test_rejects_factor_above_1(self, client):
        bad = {**self.payload, "social_desirability_factor": 1.5}
        assert client.post("/api/v2/election/shy-voter", json=bad).status_code == 422

    def test_rejects_num_polls_above_30(self, client):
        bad = {**self.payload, "num_polls": 99}
        assert client.post("/api/v2/election/shy-voter", json=bad).status_code == 422


# ── /electoral-fatigue ──────────────────────────────────────────────────────

class TestElectoralFatigue:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "num_elections": 4, "fatigue_rate": 0.07,
        "engaged_voter_pct": 0.2, "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/electoral-fatigue", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("elections", "winner_drift", "ideology_drift",
                  "representation_gap"):
            assert k in r.json()

    def test_returns_one_entry_per_election(self, client):
        body = client.post("/api/v2/election/electoral-fatigue", json={
            **self.payload, "num_elections": 6,
        }).json()
        assert len(body["elections"]) == 6

    def test_rejects_fatigue_rate_above_max(self, client):
        bad = {**self.payload, "fatigue_rate": 0.5}
        assert client.post("/api/v2/election/electoral-fatigue", json=bad).status_code == 422
