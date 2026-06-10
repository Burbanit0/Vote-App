"""Tests for Phase 3 batch 4: /api/v2/election/{cascade,behavioral-biases,
choice-overload,deliberation}. Same pattern as test_election_perturbers.py
from batch 3 — 3-4 tests per endpoint covering happy path + validation."""
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


# ── /cascade ────────────────────────────────────────────────────────────────

class TestCascade:
    payload = {
        "candidates": CANDS, "num_voters": 50, "seed": 42,
        "cascade_strength": 0.5, "observation_window": 10,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/cascade", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("sincere_winner", "cascade_winner", "cascade_occurred",
                  "vote_sequence", "cascade_strength_curve"):
            assert k in r.json()

    def test_rejects_cascade_strength_above_1(self, client):
        bad = {**self.payload, "cascade_strength": 1.5}
        assert client.post("/api/v2/election/cascade", json=bad).status_code == 422

    def test_rejects_observation_window_above_50(self, client):
        bad = {**self.payload, "observation_window": 99}
        assert client.post("/api/v2/election/cascade", json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/cascade", json=bad).status_code == 422


# ── /behavioral-biases ──────────────────────────────────────────────────────

class TestBehavioralBiases:
    payload = {
        "candidates": CANDS, "num_voters": 80, "seed": 42,
        "expressive_pct": 0.2, "bullet_voting_pct": 0.2,
        "primacy_bonus": 0.02, "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/behavioral-biases", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("sincere_winner", "biased_winner", "winner_changed",
                  "vote_breakdown", "method_sensitivity"):
            assert k in r.json()

    def test_rejects_primacy_bonus_above_0_2(self, client):
        bad = {**self.payload, "primacy_bonus": 0.5}
        assert client.post("/api/v2/election/behavioral-biases", json=bad).status_code == 422

    def test_accepts_explicit_candidate_order(self, client):
        ok = {**self.payload, "candidate_order": ["Carol", "Bob", "Alice"]}
        r = client.post("/api/v2/election/behavioral-biases", json=ok)
        assert r.status_code == 200


# ── /choice-overload ────────────────────────────────────────────────────────

class TestChoiceOverload:
    payload = {
        "num_voters": 100, "seed": 42,
        "candidate_counts": [3, 5, 7],
        "overload_threshold": 5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/choice-overload", json=self.payload)
        assert r.status_code == 200, r.text
        for k in ("results_by_n", "regret_curve",
                  "most_robust_method", "least_robust_method",
                  "overload_threshold"):
            assert k in r.json()

    def test_rejects_empty_candidate_counts(self, client):
        bad = {**self.payload, "candidate_counts": []}
        assert client.post("/api/v2/election/choice-overload", json=bad).status_code == 422

    def test_rejects_overload_threshold_above_12(self, client):
        bad = {**self.payload, "overload_threshold": 99}
        assert client.post("/api/v2/election/choice-overload", json=bad).status_code == 422

    def test_accepts_explicit_heuristic_weights(self, client):
        ok = {**self.payload, "heuristic_weights": {"notoriety": 0.3, "primacy": 0.1, "partisan": 0.15}}
        r = client.post("/api/v2/election/choice-overload", json=ok)
        assert r.status_code == 200


# ── /deliberation ───────────────────────────────────────────────────────────

class TestDeliberation:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "deliberation_rounds": 3, "influence_weight": 0.3,
        "network_type": "random", "group_size": 5,
        "argument_quality": 0.5, "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/deliberation", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("pre_deliberation", "post_deliberation", "winner_changed",
                  "deliberation_effect", "per_round", "network_effect"):
            assert k in body
        # Pre and post both contain the winner — they're separate sub-objects.
        assert "winner" in body["pre_deliberation"]
        assert "winner" in body["post_deliberation"]

    def test_rejects_invalid_influence_weight(self, client):
        bad = {**self.payload, "influence_weight": 1.5}
        assert client.post("/api/v2/election/deliberation", json=bad).status_code == 422

    def test_rejects_group_size_below_3(self, client):
        bad = {**self.payload, "group_size": 1}
        assert client.post("/api/v2/election/deliberation", json=bad).status_code == 422

    def test_rejects_too_many_rounds(self, client):
        bad = {**self.payload, "deliberation_rounds": 99}
        assert client.post("/api/v2/election/deliberation", json=bad).status_code == 422
