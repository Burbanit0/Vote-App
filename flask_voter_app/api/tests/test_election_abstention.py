"""Tests for POST /api/v2/election/abstention — Phase 3 batch 2."""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _payload(**overrides) -> dict:
    base = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.3},
        ],
        "num_voters":            60,
        "ideology":              "random",
        "seed":                  42,
        "demobilization_factor": 0.5,
        "poll_influence":        0.8,
        "num_rounds":            3,
    }
    base.update(overrides)
    return base


class TestAbstention:
    def test_returns_200_with_expected_keys(self, client):
        r = client.post("/api/v2/election/abstention", json=_payload())
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("rounds", "sincere_winner", "final_winner",
                    "winner_changed", "turnout_by_camp", "candidates"):
            assert key in body, f"missing key: {key}"

    def test_round_0_is_sincere_full_turnout(self, client):
        body = client.post("/api/v2/election/abstention", json=_payload()).json()
        round_0 = body["rounds"][0]
        assert round_0["round"] == 0
        assert round_0["turnout"] == 1.0, (
            "round 0 must be sincere — no polls yet → 100 % turnout"
        )

    def test_num_rounds_plus_initial_sincere(self, client):
        """Worker returns 1 sincere round (0) + num_rounds polling rounds."""
        body = client.post("/api/v2/election/abstention",
                           json=_payload(num_rounds=4)).json()
        assert len(body["rounds"]) == 5  # 0 + 4

    def test_winners_by_method_present(self, client):
        body = client.post("/api/v2/election/abstention", json=_payload()).json()
        assert "winners_by_method" in body
        assert isinstance(body["winners_by_method"], dict)
        # Should contain at least the major method names
        keys = body["winners_by_method"].keys()
        assert "plurality" in keys or "irv" in keys

    def test_rejects_single_candidate(self, client):
        r = client.post("/api/v2/election/abstention", json=_payload(
            candidates=[{"name": "Solo", "x": 0.0, "y": 0.0}]
        ))
        assert r.status_code == 422

    def test_rejects_demobilization_factor_above_1(self, client):
        r = client.post("/api/v2/election/abstention",
                        json=_payload(demobilization_factor=1.5))
        assert r.status_code == 422

    def test_rejects_poll_influence_above_1(self, client):
        r = client.post("/api/v2/election/abstention",
                        json=_payload(poll_influence=1.5))
        assert r.status_code == 422
