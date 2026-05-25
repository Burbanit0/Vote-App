"""Tests for Phase 4 batch 4 (final theory batch):
/api/v2/theory/{identity-voting, assumption-testing, collective-will}."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


CANDS = [
    {"name": "Alice", "x": -0.5, "y": 0.0},
    {"name": "Bob",   "x":  0.0, "y": 0.0},
    {"name": "Carol", "x":  0.5, "y": 0.0},
]


# ── /identity-voting ──────────────────────────────────────────────────────

class TestIdentityVoting:
    payload = {
        "candidates": CANDS, "num_voters": 100, "seed": 42,
        "identity_weight": 0.5, "cross_pressure": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/identity-voting", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("sincere_winner", "identity_winner", "mixed_winner",
                  "winner_changed", "group_results", "cross_pressured",
                  "identity_weight_curve", "pedagogical_note"):
            assert k in body
        # Curve sweeps weight 0.0..1.0 in 0.1 steps
        assert len(body["identity_weight_curve"]) == 11

    def test_accepts_custom_groups(self, client):
        ok = {
            **self.payload,
            "identity_groups": [
                {"name": "Left", "pct": 0.5, "ideology_center": -0.4,
                 "loyalty": 0.8, "candidate_affiliation": "Alice"},
                {"name": "Right", "pct": 0.5, "ideology_center": 0.4,
                 "loyalty": 0.7, "candidate_affiliation": "Carol"},
            ],
        }
        r = client.post("/api/v2/theory/identity-voting", json=ok)
        assert r.status_code == 200, r.text
        assert len(r.json()["group_results"]) == 2

    def test_rejects_identity_weight_above_1(self, client):
        bad = {**self.payload, "identity_weight": 1.5}
        assert client.post("/api/v2/theory/identity-voting",
                           json=bad).status_code == 422


# ── /assumption-testing ────────────────────────────────────────────────────

class TestAssumptionTesting:
    def test_happy_path_default(self, client):
        r = client.post("/api/v2/theory/assumption-testing", json={})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("baseline_result", "relaxed_results",
                  "most_fragile_assumption", "robust_result",
                  "pedagogical_note"):
            assert k in body
        # All 5 assumptions tested by default
        for a in ("single_peaked", "stable_preferences", "rational_voters",
                  "fixed_electorate", "measurable_utilities"):
            assert a in body["relaxed_results"]

    def test_accepts_subset(self, client):
        ok = {
            "base_simulation": {
                "candidates": CANDS, "num_voters": 80,
                "ideology": "random", "seed": 42,
            },
            "assumptions_to_relax": ["stable_preferences", "rational_voters"],
        }
        r = client.post("/api/v2/theory/assumption-testing", json=ok)
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body["relaxed_results"].keys()) == {
            "stable_preferences", "rational_voters",
        }

    def test_rejects_bad_base_simulation(self, client):
        bad = {"base_simulation": {"num_voters": 5}}   # < 20 voters
        assert client.post("/api/v2/theory/assumption-testing",
                           json=bad).status_code == 422


# ── /collective-will ──────────────────────────────────────────────────────

class TestCollectiveWill:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "num_methods": 4, "num_agendas": 3, "num_simulations": 1,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/collective-will", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("unique_winners", "unique_winner_count", "winner_by_method",
                  "winner_by_agenda", "rousseau_score", "most_frequent_winner",
                  "condorcet_exists", "philosophical_conclusion",
                  "pedagogical_note"):
            assert k in body
        assert len(body["winner_by_method"]) == 4
        assert len(body["winner_by_agenda"]) == 3

    def test_rejects_too_many_methods(self, client):
        bad = {**self.payload, "num_methods": 99}
        assert client.post("/api/v2/theory/collective-will",
                           json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/theory/collective-will",
                           json=bad).status_code == 422
