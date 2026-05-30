"""Tests for POST /api/v2/election/simulate — the first endpoint migrated
from Flask to FastAPI in Phase 2 of the strategic refactor.

These tests pin behavioural parity with the Flask /api/election/simulate
endpoint, so the frontend can switch from v1 to v2 transparently.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Minimal valid payload reused across tests ───────────────────────────────

def _payload(**overrides) -> dict:
    base = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.3},
        ],
        "num_voters": 30,
        "ideology":   "random",
        "seed":       42,
    }
    base.update(overrides)
    return base


# ── Happy path ───────────────────────────────────────────────────────────────

class TestSimulateHappyPath:
    def test_returns_200_with_top_level_keys(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload())
        assert r.status_code == 200
        body = r.json()
        for key in (
            "config", "voters_snapshot", "candidates", "methods",
            "condorcet_winner", "blank_rate", "campaign_trajectory",
            "inter_method_agreement", "condorcet_exists",
        ):
            assert key in body, f"missing key: {key}"

    def test_runs_at_least_5_methods(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload()).json()
        assert len(body["methods"]) >= 5
        for md in body["methods"].values():
            assert "winner" in md

    def test_voter_snapshot_count_matches_num_voters(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(num_voters=80)).json()
        assert len(body["voters_snapshot"]) == 80

    def test_inter_method_agreement_in_range(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload()).json()
        assert 0.0 <= body["inter_method_agreement"] <= 1.0


# ── Determinism — same seed = same result ──────────────────────────────────

class TestDeterminism:
    def test_same_seed_yields_identical_methods(self, client):
        r1 = client.post("/api/v2/election/simulate", json=_payload(seed=7)).json()
        r2 = client.post("/api/v2/election/simulate", json=_payload(seed=7)).json()
        assert r1["methods"] == r2["methods"]
        assert r1["voters_snapshot"] == r2["voters_snapshot"]

    def test_different_seed_may_differ(self, client):
        r1 = client.post("/api/v2/election/simulate", json=_payload(seed=1)).json()
        r2 = client.post("/api/v2/election/simulate", json=_payload(seed=999)).json()
        # Voters always differ on a different seed, methods often do too.
        assert r1["voters_snapshot"] != r2["voters_snapshot"]


# ── Validation rejected at the FastAPI boundary ─────────────────────────────

class TestValidation:
    def test_rejects_single_candidate_with_422(self, client):
        """Pydantic min_length=2 → FastAPI returns 422 (unprocessable entity)
        BEFORE the worker runs. That's stricter than the Flask side (which
        returned 400 from inside the worker)."""
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=[
            {"name": "Solo", "x": 0.0, "y": 0.0},
        ]))
        assert r.status_code == 422
        assert "detail" in r.json()

    def test_rejects_x_out_of_range(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=[
            {"name": "A", "x":  2.0, "y": 0.0},
            {"name": "B", "x": -0.5, "y": 0.0},
        ]))
        assert r.status_code == 422

    def test_rejects_extra_fields(self, client):
        """extra='forbid' on the schema catches typos."""
        r = client.post("/api/v2/election/simulate", json={**_payload(), "Seed": 99})
        assert r.status_code == 422

    def test_rejects_too_many_candidates(self, client):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(9)]
        r = client.post("/api/v2/election/simulate", json=_payload(candidates=many))
        assert r.status_code == 422

    def test_rejects_num_voters_above_cap(self, client):
        r = client.post("/api/v2/election/simulate", json=_payload(num_voters=99_999))
        assert r.status_code == 422


# ── Blank vote / campaign / information_model ──────────────────────────────

class TestPipelineOptions:
    def test_blank_vote_enables_winner_with_blank(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(
            blank_vote={"enabled": True, "rule": "symbolic",
                        "contagion": {"enabled": False, "beta": 0.15,
                                      "gamma": 0.10, "network": "random"}}
        )).json()
        for md in body["methods"].values():
            assert "winner_with_blank" in md
            assert "blank_triggered" in md

    def test_campaign_enabled_returns_trajectory(self, client):
        body = client.post("/api/v2/election/simulate", json=_payload(
            campaign={"enabled": True, "num_days": 14, "polling_effect": 0.3}
        )).json()
        assert body["campaign_trajectory"] is not None
