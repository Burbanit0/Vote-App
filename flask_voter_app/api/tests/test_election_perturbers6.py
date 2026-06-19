"""Tests for Phase 3 batch 8:
/api/v2/election/{adaptive, historical-replay, gerrymander, multiwinner_compare}."""
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


# ── /adaptive ───────────────────────────────────────────────────────────────

class TestAdaptive:
    payload = {
        "candidates": CANDS, "num_voters": 100, "seed": 42,
        "num_rounds": 3, "method": "plurality",
        "strategic_threshold": 0.15,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/adaptive", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("rounds", "converged", "final_winner", "sincere_winner",
                  "strategic_drift", "candidates"):
            assert k in body
        assert len(body["rounds"]) == 3

    def test_rejects_too_many_rounds(self, client):
        bad = {**self.payload, "num_rounds": 99}
        assert client.post("/api/v2/election/adaptive",
                           json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/adaptive",
                           json=bad).status_code == 422


# ── /historical-replay ─────────────────────────────────────────────────────

class TestHistoricalReplay:
    payload = {
        "scenario_id": "france2002",
        "num_days": 10, "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/historical-replay", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("scenario", "candidates", "days", "final"):
            assert k in body
        assert len(body["days"]) == 11   # day 0 + 10 days

    def test_accepts_overrides(self, client):
        ok = {
            **self.payload,
            "overrides": [
                {"name": "Chirac", "x": 0.1, "y": 0.0},
            ],
        }
        r = client.post("/api/v2/election/historical-replay", json=ok)
        assert r.status_code == 200, r.text

    def test_rejects_unknown_scenario(self, client):
        bad = {**self.payload, "scenario_id": "nope"}
        r = client.post("/api/v2/election/historical-replay", json=bad)
        assert r.status_code == 400, r.text


# ── /gerrymander ────────────────────────────────────────────────────────────

class TestGerrymander:
    payload = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
        ],
        "districts": [
            {"id": 0, "bounds": {"x_min": -1.0, "x_max": 0.0,
                                 "y_min": -1.0, "y_max": 1.0}},
            {"id": 1, "bounds": {"x_min":  0.0, "x_max": 1.0,
                                 "y_min": -1.0, "y_max": 1.0}},
        ],
        "num_voters": 100, "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/gerrymander", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("districts", "voters", "parliament_gerrymander",
                  "parliament_proportional", "national_vote_share",
                  "distortion", "gerrymander_index", "winner",
                  "candidates", "num_seats"):
            assert k in body
        assert len(body["districts"]) == 2

    def test_rejects_no_districts(self, client):
        bad = {**self.payload, "districts": []}
        assert client.post("/api/v2/election/gerrymander",
                           json=bad).status_code == 422


# ── /multiwinner_compare ───────────────────────────────────────────────────

class TestMultiwinnerCompare:
    payload = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.1},
            {"name": "Dave",  "x": -0.2, "y":  0.4},
        ],
        "num_voters": 100, "seed": 42, "num_seats": 3,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/multiwinner_compare", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("methods", "vote_shares", "proportional_reference",
                  "num_seats", "candidates", "best_method", "worst_method"):
            assert k in body
        for m in ("stv", "dhondt", "spav", "phragmen", "equal_shares", "fptp"):
            assert m in body["methods"]
        # Each method's committee carries its justified-representation verdict.
        jr = body["methods"]["equal_shares"]["justified_representation"]
        assert set(jr) == {"jr", "pjr", "ejr"}
        assert all(isinstance(v, bool) for v in jr.values())

    def test_rejects_seats_geq_candidates(self, client):
        bad = {**self.payload, "num_seats": 4}
        r = client.post("/api/v2/election/multiwinner_compare", json=bad)
        assert r.status_code == 400, r.text

    def test_rejects_too_many_seats(self, client):
        bad = {**self.payload, "num_seats": 99}
        assert client.post("/api/v2/election/multiwinner_compare",
                           json=bad).status_code == 422
