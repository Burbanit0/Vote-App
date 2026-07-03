"""Tests for Phase 3 batch 9 (final):
/api/v2/election/{divergence, interpret, quadratic-funding, liquid-democracy,
                  conviction-voting, power-indices}."""
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


# ── /divergence ─────────────────────────────────────────────────────────────

class TestDivergence:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "blank_vote": {"enabled": True, "rule": "symbolic"},
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/divergence", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("without_blank", "with_blank", "delta_agreement",
                  "methods_changed", "pct_methods_changed", "blank_rule"):
            assert k in body

    def test_rejects_too_many_voters(self, client):
        bad = {**self.payload, "num_voters": 999}
        assert client.post("/api/v2/election/divergence",
                           json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/divergence",
                           json=bad).status_code == 422


# ── /interpret ──────────────────────────────────────────────────────────────

class TestInterpret:
    """Provides a synthetic /simulate-like payload."""
    payload = {
        "lang": "fr",
        "methods": {
            "plurality": {"winner": "Alice"},
            "borda":     {"winner": "Bob"},
            "irv":       {"winner": "Alice"},
        },
        "condorcet_winner": "Alice",
        "condorcet_exists": True,
        "inter_method_agreement": 0.67,
        "blank_rate": 0.0,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/interpret", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("headline", "condorcet_analysis", "divergence_reason",
                  "method_groups", "pedagogical_note", "key_facts"):
            assert k in body

    def test_rejects_empty_methods(self, client):
        bad = {**self.payload, "methods": {}}
        r = client.post("/api/v2/election/interpret", json=bad)
        assert r.status_code == 400, r.text


# ── /quadratic-funding ──────────────────────────────────────────────────────

class TestQuadraticFunding:
    payload = {
        "projects": [
            {"name": "Education", "x": -0.4},
            {"name": "Health",    "x":  0.0},
            {"name": "Infra",     "x":  0.5},
        ],
        "num_voters": 80, "seed": 42,
        "budget_per_voter": 100.0, "matching_pool": 5000.0,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/quadratic-funding", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("projects", "winner", "mechanism_comparison",
                  "gini_coefficients", "vote_shares", "matching_pool",
                  "budget_per_voter", "pedagogical_note"):
            assert k in body

    def test_rejects_single_project(self, client):
        bad = {**self.payload, "projects": [self.payload["projects"][0]]}
        assert client.post("/api/v2/election/quadratic-funding",
                           json=bad).status_code == 422


# ── /liquid-democracy ──────────────────────────────────────────────────────

class TestLiquidDemocracy:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
        "delegation_probability": 0.5,
        "delegation_strategy": "nearest",
        "max_chain_length": 5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/liquid-democracy", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("weighted_results", "direct_voters", "delegators",
                  "super_voters", "delegation_graph", "comparison",
                  "gini_voting_weight", "pedagogical_note"):
            assert k in body

    def test_rejects_chain_too_long(self, client):
        bad = {**self.payload, "max_chain_length": 99}
        assert client.post("/api/v2/election/liquid-democracy",
                           json=bad).status_code == 422


# ── /conviction-voting ─────────────────────────────────────────────────────

class TestConvictionVoting:
    payload = {
        "proposals": [
            {"name": "Prop A", "x": -0.5},
            {"name": "Prop B", "x":  0.5},
            {"name": "Prop C", "x":  0.0},
        ],
        "num_voters": 80, "seed": 42,
        "conviction_distribution": "uniform",
        "whale_pct": 0.10,
        "small_lock_days": 224,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/conviction-voting", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("conviction_winner", "token_winner", "winner_changed",
                  "proposals", "voter_scatter", "voter_stats",
                  "pedagogical_note", "lock_options", "multipliers"):
            assert k in body

    def test_rejects_single_proposal(self, client):
        bad = {**self.payload, "proposals": [self.payload["proposals"][0]]}
        assert client.post("/api/v2/election/conviction-voting",
                           json=bad).status_code == 422


# ── /power-indices ─────────────────────────────────────────────────────────

class TestPowerIndices:
    payload = {
        "parties": [
            {"name": "A", "seats": 40, "pariah": False},
            {"name": "B", "seats": 35, "pariah": False},
            {"name": "C", "seats": 15, "pariah": False},
            {"name": "D", "seats": 10, "pariah": True},
        ],
        "majority_threshold": 51,
        "calculate_shapley": True,
        "calculate_banzhaf": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/power-indices", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("total_seats", "majority_threshold", "parties",
                  "viable_coalitions", "power_surprises", "pedagogical_note"):
            assert k in body
        assert body["total_seats"] == 100
        # Pariah party D must have shapley == 0
        d = next(p for p in body["parties"] if p["name"] == "D")
        assert d["shapley_index"] == 0.0

    def test_rejects_no_parties(self, client):
        bad = {**self.payload, "parties": []}
        assert client.post("/api/v2/election/power-indices",
                           json=bad).status_code == 422
