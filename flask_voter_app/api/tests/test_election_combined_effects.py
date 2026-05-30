"""Tests for POST /api/v2/election/combined-effects — Phase 3 batch 1.

The heavy 2³-factorial endpoint: same electorate run 8 times with all
combinations of blank/campaign/info ON-OFF. Pins behavioural parity with
the Flask /api/election/combined-effects.
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
    }
    base.update(overrides)
    return base


class TestCombinedEffects:
    def test_returns_200_with_expected_keys(self, client):
        r = client.post("/api/v2/election/combined-effects", json=_payload())
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "base_winner", "combinations", "factor_deltas",
            "most_disruptive_factor", "least_disruptive_factor",
            "max_disruption_combination",
        ):
            assert key in body, f"missing key: {key}"

    def test_exactly_8_combinations(self, client):
        body = client.post("/api/v2/election/combined-effects", json=_payload()).json()
        assert len(body["combinations"]) == 8, "expected 2^3 = 8 combinations"

    def test_each_combination_has_required_fields(self, client):
        body = client.post("/api/v2/election/combined-effects", json=_payload()).json()
        for combo in body["combinations"]:
            for k in ("id", "blank", "campaign", "information_model",
                      "plurality_winner", "condorcet_winner",
                      "inter_method_agreement", "winner_differs_from_base"):
                assert k in combo

    def test_factor_deltas_are_floats(self, client):
        body = client.post("/api/v2/election/combined-effects", json=_payload()).json()
        for k in ("blank", "campaign", "information_model"):
            assert k in body["factor_deltas"]
            assert isinstance(body["factor_deltas"][k], (int, float))

    def test_most_and_least_disruptive_are_among_factors(self, client):
        body = client.post("/api/v2/election/combined-effects", json=_payload()).json()
        valid = {"blank", "campaign", "information_model"}
        assert body["most_disruptive_factor"]  in valid
        assert body["least_disruptive_factor"] in valid

    def test_rejects_single_candidate_via_422(self, client):
        r = client.post("/api/v2/election/combined-effects", json=_payload(candidates=[
            {"name": "Solo", "x": 0.0, "y": 0.0},
        ]))
        assert r.status_code == 422

    def test_rejects_too_many_candidates_via_422(self, client):
        many = [{"name": f"C{i}", "x": 0.0, "y": 0.0} for i in range(7)]
        r = client.post("/api/v2/election/combined-effects", json=_payload(candidates=many))
        assert r.status_code == 422

    def test_caps_num_voters_at_200(self, client):
        r = client.post("/api/v2/election/combined-effects", json=_payload(num_voters=201))
        assert r.status_code == 422
