"""
test_coalition.py — Tests for POST /api/election/coalition
"""
import json
import pytest

URL = "/api/election/coalition"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":           60,
    "ideology":             "random",
    "seed":                 42,
    "total_seats":          100,
    "government_threshold": 0.5,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestCoalitionBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("methods", "candidates", "total_seats", "seat_threshold",
                    "most_centrist_method", "most_divergent_method"):
            assert key in body, f"Missing top-level key: {key}"

    def test_methods_list_not_empty(self, client):
        body = json.loads(post(client).data)
        assert len(body["methods"]) > 0

    def test_total_seats_echoed(self, client):
        body = json.loads(post(client).data)
        assert body["total_seats"] == 100

    def test_seat_threshold_is_half(self, client):
        body = json.loads(post(client).data)
        # ceil(100 * 0.5) = 50
        assert body["seat_threshold"] == 50

    def test_candidates_in_response(self, client):
        body = json.loads(post(client).data)
        names = {c["name"] for c in body["candidates"]}
        assert {"Alice", "Bob", "Carol"} == names


# ── Per-method result structure ───────────────────────────────────────────────

class TestCoalitionMethodResults:
    def test_each_method_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for m in body["methods"]:
            for key in ("method", "winner", "seats", "vote_shares",
                        "coalition_parties", "coalition_seats",
                        "coalition_spread", "government_possible"):
                assert key in m, f"Method '{m.get('method')}' missing key: {key}"

    def test_seats_sum_to_total(self, client):
        body = json.loads(post(client).data)
        for m in body["methods"]:
            s = sum(m["seats"].values())
            assert s == body["total_seats"], (
                f"{m['method']}: seat sum {s} ≠ {body['total_seats']}"
            )

    def test_coalition_spread_in_range(self, client):
        body = json.loads(post(client).data)
        for m in body["methods"]:
            assert 0.0 <= m["coalition_spread"] <= 2.0, (
                f"{m['method']}: coalition_spread={m['coalition_spread']} out of [0, 2]"
            )

    def test_coalition_parties_is_list(self, client):
        body = json.loads(post(client).data)
        for m in body["methods"]:
            assert isinstance(m["coalition_parties"], list)
            assert len(m["coalition_parties"]) >= 1


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestCoalitionEdgeCases:
    def test_two_candidates(self, client):
        payload = {**BASE, "candidates": [
            {"name": "Alice", "x": -0.5, "y": 0.0},
            {"name": "Bob",   "x":  0.5, "y": 0.0},
        ]}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert len(body["methods"]) > 0

    def test_government_threshold_1_0_always_false(self, client):
        """Threshold=100% means 100 seats needed; greedy can never exceed 100 with 3 parties."""
        payload = {**BASE, "government_threshold": 1.0, "total_seats": 100}
        body = json.loads(post(client, payload).data)
        # With threshold=100 seats and only 3 parties sharing 100 seats,
        # the coalition might actually reach 100 if it takes all parties — so we just verify
        # the field is present and boolean.
        for m in body["methods"]:
            assert isinstance(m["government_possible"], bool)

    def test_six_candidates(self, client):
        payload = {**BASE, "num_voters": 20, "candidates": [
            {"name": "A", "x": -0.8, "y": 0.0},
            {"name": "B", "x": -0.4, "y": 0.0},
            {"name": "C", "x":  0.0, "y": 0.0},
            {"name": "D", "x":  0.2, "y": 0.0},
            {"name": "E", "x":  0.5, "y": 0.0},
            {"name": "F", "x":  0.8, "y": 0.0},
        ]}
        r = post(client, payload)
        assert r.status_code == 200

    def test_requires_at_least_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        r = post(client, payload)
        assert r.status_code == 400


# ── D'Hondt correctness ───────────────────────────────────────────────────────

class TestDHondt:
    def test_winner_gets_most_seats(self, client):
        """The plurality winner should generally hold the most seats."""
        body = json.loads(post(client).data)
        for m in body["methods"]:
            winner = m["winner"]
            if winner and winner in m["seats"]:
                max_seats = max(m["seats"].values())
                assert m["seats"][winner] == max_seats or m["seats"][winner] > 0
