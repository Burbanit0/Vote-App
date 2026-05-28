"""Tests for Phase 4.5.a.3 — tech-democracy demos on FastAPI."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── /tech/e2e-demo ─────────────────────────────────────────────────────────

class TestE2EDemo:
    payload = {
        "candidates": ["Alice", "Bob", "Carol"],
        "num_demo_voters": 10,
        "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/tech/e2e-demo", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("voters", "public_bulletin_board", "aggregate_result",
                  "winner", "audit_proof"):
            assert k in body
        assert len(body["voters"]) == 10
        assert body["winner"] in self.payload["candidates"]

    def test_user_vote_sets_voter_one(self, client):
        ok = {**self.payload, "user_vote": "Carol"}
        r = client.post("/api/v2/tech/e2e-demo", json=ok)
        assert r.status_code == 200, r.text
        assert r.json()["voters"][0]["vote_HIDDEN"] == "Carol"

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": ["Alice"]}
        assert client.post("/api/v2/tech/e2e-demo", json=bad).status_code == 422

    def test_rejects_too_many_voters(self, client):
        bad = {**self.payload, "num_demo_voters": 99}
        assert client.post("/api/v2/tech/e2e-demo", json=bad).status_code == 422


# ── /tech/polis-simulation ─────────────────────────────────────────────────

class TestPolisSimulation:
    payload = {"num_participants": 60, "ideology": "polarized",
               "seed": 42, "num_clusters": 3}

    def test_happy_path_default_statements(self, client):
        r = client.post("/api/v2/tech/polis-simulation", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("clusters", "consensus_statements", "polarizing_statements",
                  "participant_positions", "num_clusters", "num_participants"):
            assert k in body
        assert body["num_participants"] == 60
        assert len(body["participant_positions"]) == 60

    def test_accepts_custom_statements(self, client):
        ok = {**self.payload,
              "statements": ["Statement A", "Statement B", "Statement C"]}
        r = client.post("/api/v2/tech/polis-simulation", json=ok)
        assert r.status_code == 200, r.text

    def test_rejects_too_many_clusters(self, client):
        bad = {**self.payload, "num_clusters": 99}
        assert client.post("/api/v2/tech/polis-simulation",
                           json=bad).status_code == 422

    def test_rejects_too_few_participants(self, client):
        bad = {**self.payload, "num_participants": 5}
        assert client.post("/api/v2/tech/polis-simulation",
                           json=bad).status_code == 422


# ── /tech/polis ────────────────────────────────────────────────────────────

class TestPolisWithCandidates:
    payload = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.1},
        ],
        "num_participants": 60,
        "ideology": "random",
        "seed": 42,
        "num_clusters": 3,
        "method_to_compare": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/tech/polis", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("clusters", "statements", "participant_positions",
                  "polis_winner", "election_winner", "winners_agree",
                  "candidate_scores", "pedagogical_note"):
            assert k in body

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [self.payload["candidates"][0]]}
        assert client.post("/api/v2/tech/polis", json=bad).status_code == 422

    def test_rejects_extra_field(self, client):
        bad = {**self.payload, "evil": 1}
        assert client.post("/api/v2/tech/polis", json=bad).status_code == 422
