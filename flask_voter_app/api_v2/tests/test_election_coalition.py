"""Tests for POST /api/v2/election/coalition — Phase 3 batch 2."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


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
        "num_voters":           50,
        "ideology":             "random",
        "seed":                 42,
        "total_seats":          100,
        "government_threshold": 0.5,
    }
    base.update(overrides)
    return base


class TestCoalition:
    def test_returns_200_with_expected_keys(self, client):
        r = client.post("/api/v2/election/coalition", json=_payload())
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "methods", "candidates", "total_seats", "seat_threshold",
            "most_centrist_method", "most_divergent_method",
            "inter_method_agreement",
        ):
            assert key in body, f"missing key: {key}"

    def test_each_method_result_has_required_fields(self, client):
        body = client.post("/api/v2/election/coalition", json=_payload()).json()
        assert len(body["methods"]) >= 5, "expected ≥5 voting methods"
        for m in body["methods"]:
            for k in ("method", "winner", "seats", "vote_shares",
                      "coalition_parties", "coalition_seats",
                      "coalition_spread", "government_possible"):
                assert k in m, f"method {m.get('method')} missing {k}"

    def test_seat_threshold_matches_government_threshold(self, client):
        body = client.post(
            "/api/v2/election/coalition",
            json=_payload(total_seats=200, government_threshold=0.6),
        ).json()
        assert body["seat_threshold"] == 120
        assert body["total_seats"] == 200

    def test_total_seats_allocated_per_method(self, client):
        body = client.post("/api/v2/election/coalition", json=_payload()).json()
        for m in body["methods"]:
            assert sum(m["seats"].values()) == body["total_seats"], (
                f"method {m['method']} doesn't allocate all seats"
            )

    def test_rejects_single_candidate(self, client):
        r = client.post("/api/v2/election/coalition", json=_payload(
            candidates=[{"name": "Solo", "x": 0.0, "y": 0.0}]
        ))
        assert r.status_code == 422

    def test_rejects_government_threshold_above_1(self, client):
        r = client.post("/api/v2/election/coalition",
                        json=_payload(government_threshold=1.5))
        assert r.status_code == 422

    def test_rejects_total_seats_above_cap(self, client):
        r = client.post("/api/v2/election/coalition",
                        json=_payload(total_seats=99_999))
        assert r.status_code == 422
