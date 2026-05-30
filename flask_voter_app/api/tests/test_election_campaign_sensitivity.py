"""Tests for POST /api/v2/election/campaign-sensitivity — Phase 3 batch 1.

Snapshot endpoint: runs the same electorate at N campaign days and
measures method-by-method winner stability over time.
"""
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
        "num_voters": 30,
        "ideology":   "random",
        "seed":       42,
        "snapshot_days": [0, 7, 14, "final"],
        "campaign": {"enabled": True, "num_days": 28, "polling_effect": 0.4},
    }
    base.update(overrides)
    return base


class TestCampaignSensitivity:
    def test_returns_200_with_expected_keys(self, client):
        r = client.post("/api/v2/election/campaign-sensitivity", json=_payload())
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("snapshots", "method_stability",
                    "most_stable_method", "least_stable_method"):
            assert key in body

    def test_one_snapshot_per_requested_day(self, client):
        body = client.post("/api/v2/election/campaign-sensitivity",
                           json=_payload(snapshot_days=[0, 7, 14])).json()
        assert len(body["snapshots"]) == 3

    def test_each_snapshot_has_methods_dict(self, client):
        body = client.post("/api/v2/election/campaign-sensitivity",
                           json=_payload()).json()
        for snap in body["snapshots"]:
            assert "methods" in snap
            assert isinstance(snap["methods"], dict)
            assert len(snap["methods"]) >= 5

    def test_method_stability_has_score_in_unit_interval(self, client):
        body = client.post("/api/v2/election/campaign-sensitivity",
                           json=_payload()).json()
        for method, stats in body["method_stability"].items():
            assert "winner_changes" in stats
            assert "stability_score" in stats
            assert 0.0 <= stats["stability_score"] <= 1.0

    def test_rejects_too_many_candidates(self, client):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(7)]
        r = client.post("/api/v2/election/campaign-sensitivity",
                        json=_payload(candidates=many))
        assert r.status_code == 422

    def test_accepts_mixed_int_and_string_snapshot_days(self, client):
        """Worker behaviour: 'final' may be deduplicated with the last int day
        if they collide (28 == 'final' in a 28-day campaign). We just check
        that the worker accepts the mixed input without crashing and returns
        at least the int days."""
        r = client.post("/api/v2/election/campaign-sensitivity",
                        json=_payload(snapshot_days=[0, 7, 14, 21, 28, "final"]))
        assert r.status_code == 200
        snaps = r.json()["snapshots"]
        assert 5 <= len(snaps) <= 6   # 5 if dedup'd, 6 otherwise
