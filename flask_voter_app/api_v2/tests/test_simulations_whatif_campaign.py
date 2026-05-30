"""Tests for Phase 4.5.a.6 — what-if + campaign on FastAPI (/api/v2/simulations)."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── /what-if ─────────────────────────────────────────────────────────────────

class TestWhatIf:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/what-if", json={
            "base": {"num_candidates": 3, "num_voters": 200},
            "variant_param": "num_voters",
            "variant_values": [100, 300],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["variant_param"] == "num_voters"
        assert len(body["results"]) == 2
        assert "methods" in body["results"][0]
        assert "condorcet_winner" in body["results"][0]

    def test_unknown_variant_param_400(self, client):
        r = client.post("/api/v2/simulations/what-if", json={
            "variant_param": "nonsense", "variant_values": [1, 2],
        })
        assert r.status_code == 400, r.text

    def test_empty_variant_values_400(self, client):
        r = client.post("/api/v2/simulations/what-if", json={
            "variant_param": "num_voters", "variant_values": [],
        })
        assert r.status_code == 400, r.text

    def test_caps_at_10_values(self, client):
        r = client.post("/api/v2/simulations/what-if", json={
            "base": {"num_candidates": 3, "num_voters": 120},
            "variant_param": "num_candidates",
            "variant_values": list(range(2, 20)),   # 18 values → capped to 10
        })
        assert r.status_code == 200, r.text
        assert len(r.json()["results"]) == 10


# ── /campaign ────────────────────────────────────────────────────────────────

class TestCampaign:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/campaign", json={
            "num_candidates": 3, "num_voters": 100, "num_days": 10,
            "method": "plurality", "seed": 42,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("days", "daily_leader", "daily_scores", "final_winner",
                  "lead_changes", "candidates"):
            assert k in body
        assert len(body["candidates"]) == 3

    def test_with_events(self, client):
        r = client.post("/api/v2/simulations/campaign", json={
            "num_candidates": 2, "num_voters": 80, "num_days": 8, "seed": 1,
            "events": [{"day": 3, "type": "scandal", "candidate": 0, "magnitude": 0.3}],
        })
        assert r.status_code == 200, r.text

    def test_defaults(self, client):
        r = client.post("/api/v2/simulations/campaign", json={"num_voters": 60, "num_days": 5})
        assert r.status_code == 200, r.text
        assert len(r.json()["candidates"]) == 4   # default num_candidates
