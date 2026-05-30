"""Tests for Phase 4 batch 2:
/api/v2/theory/{agenda-manipulation, apportionment, sen-paradox, manipulation-analysis}."""
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


# ── /agenda-manipulation ────────────────────────────────────────────────────

class TestAgendaManipulation:
    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/agenda-manipulation", json={
            "alternatives": ["A", "B", "C"], "num_voters": 11, "seed": 42,
            "target_outcome": "A",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("pairwise_matrix", "all_outcomes", "achievable_outcomes",
                  "optimal_agenda", "manipulation_power", "pedagogical_note"):
            assert k in body
        for k in ("for_target", "neutral", "worst_case"):
            assert k in body["optimal_agenda"]

    def test_rejects_single_alternative(self, client):
        assert client.post("/api/v2/theory/agenda-manipulation", json={
            "alternatives": ["only"],
        }).status_code == 422

    def test_rejects_too_many_voters(self, client):
        assert client.post("/api/v2/theory/agenda-manipulation", json={
            "alternatives": ["A", "B", "C"], "num_voters": 999,
        }).status_code == 422


# ── /apportionment ──────────────────────────────────────────────────────────

class TestApportionment:
    payload = {
        "parties": [
            {"name": "A", "votes": 9000},
            {"name": "B", "votes": 7000},
            {"name": "C", "votes": 5000},
        ],
        "num_seats": 10,
        "find_paradoxes": True,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/apportionment", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("results", "balinski_young_summary", "impossible_to_avoid",
                  "pedagogical_note"):
            assert k in body
        for method in ("hamilton", "jefferson", "webster", "adams",
                       "huntington_hill"):
            assert method in body["results"]
            assert sum(body["results"][method]["seats"].values()) == 10

    def test_rejects_no_parties(self, client):
        bad = {**self.payload, "parties": []}
        assert client.post("/api/v2/theory/apportionment",
                           json=bad).status_code == 422

    def test_rejects_too_many_seats(self, client):
        bad = {**self.payload, "num_seats": 99999}
        assert client.post("/api/v2/theory/apportionment",
                           json=bad).status_code == 422


# ── /sen-paradox ────────────────────────────────────────────────────────────

class TestSenParadox:
    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/sen-paradox",
                        json={"num_voters": 2, "seed": 42})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("paradox_exists", "paradox_examples", "paradox_frequency",
                  "alternative_names", "resolution_options",
                  "real_world_analogy", "pedagogical_note"):
            assert k in body
        assert len(body["resolution_options"]) == 4
        # Canonical Sen 1970 example always creates the paradox
        assert body["paradox_exists"] is True

    def test_rejects_wrong_num_voters(self, client):
        assert client.post("/api/v2/theory/sen-paradox",
                           json={"num_voters": 5}).status_code == 422


# ── /manipulation-analysis ────────────────────────────────────────────────

class TestManipulationAnalysis:
    payload = {
        "candidates": CANDS, "num_voters": 30, "seed": 42,
        "method": "plurality",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/manipulation-analysis",
                        json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("sincere_winner", "manipulable", "manipulation_count",
                  "manipulators", "strategy_breakdown", "pedagogical_note"):
            assert k in body
        assert body["manipulation_count"] == len(body["manipulators"])

    def test_two_candidates_never_manipulable(self, client):
        ok = {**self.payload, "candidates": [CANDS[0], CANDS[1]]}
        r = client.post("/api/v2/theory/manipulation-analysis", json=ok)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["manipulable"] is False
        assert body["manipulation_count"] == 0

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/theory/manipulation-analysis",
                           json=bad).status_code == 422

    def test_rejects_too_many_voters(self, client):
        bad = {**self.payload, "num_voters": 999}
        assert client.post("/api/v2/theory/manipulation-analysis",
                           json=bad).status_code == 422
