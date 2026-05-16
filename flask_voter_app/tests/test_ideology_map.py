"""
test_ideology_map.py — Tests for POST /simulations/ideology-map
"""
import json
import pytest

URL = "/simulations/ideology-map"

BASE_PAYLOAD = {
    "num_voters":  60,
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.3},
        {"name": "Bob",   "x":  0.5, "y":  0.3},
        {"name": "Carol", "x":  0.0, "y":  0.0},
    ],
    "ideology":  "random",
    "seed":       42,
    "method_a":  "plurality",
    "method_b":  "schulze",
}


def post(client, payload):
    return client.post(URL, json=payload)


class TestIdeologyMapBasic:
    def test_returns_200(self, client):
        r = post(client, BASE_PAYLOAD)
        assert r.status_code == 200, r.data

    def test_response_has_required_keys(self, client):
        body = json.loads(post(client, BASE_PAYLOAD).data)
        for key in ("voters", "candidates", "winner_a", "winner_b",
                    "method_a", "method_b", "condorcet_winner",
                    "pct_better_off_with_a", "pct_better_off_with_b"):
            assert key in body, f"Missing key: {key}"

    def test_voter_count_matches_request(self, client):
        body = json.loads(post(client, BASE_PAYLOAD).data)
        assert len(body["voters"]) == BASE_PAYLOAD["num_voters"]

    def test_candidate_count_matches_request(self, client):
        body = json.loads(post(client, BASE_PAYLOAD).data)
        assert len(body["candidates"]) == len(BASE_PAYLOAD["candidates"])


class TestIdeologyMapCoordinates:
    def test_voter_x_in_range(self, client):
        voters = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        for v in voters:
            assert -1.0 <= v["x"] <= 1.0, f"voter x={v['x']} out of range"

    def test_voter_y_in_range(self, client):
        voters = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        for v in voters:
            assert -1.0 <= v["y"] <= 1.0, f"voter y={v['y']} out of range"

    def test_voter_has_utility_fields(self, client):
        voters = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        assert voters, "No voters returned"
        v = voters[0]
        assert "utility_winner_a" in v
        assert "utility_winner_b" in v
        assert "prefers_a"        in v
        assert isinstance(v["prefers_a"], bool)

    def test_utilities_are_floats_in_range(self, client):
        voters = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        for v in voters:
            assert 0.0 <= v["utility_winner_a"] <= 1.0
            assert 0.0 <= v["utility_winner_b"] <= 1.0


class TestIdeologyMapPercentages:
    def test_pct_sums_to_one(self, client):
        body = json.loads(post(client, BASE_PAYLOAD).data)
        total = body["pct_better_off_with_a"] + body["pct_better_off_with_b"]
        assert abs(total - 1.0) < 0.01, f"pct_a + pct_b = {total}, expected ≈ 1.0"

    def test_pct_consistent_with_voters(self, client):
        body    = json.loads(post(client, BASE_PAYLOAD).data)
        voters  = body["voters"]
        n       = len(voters)
        pct_a   = sum(1 for v in voters if v["prefers_a"]) / n
        assert abs(pct_a - body["pct_better_off_with_a"]) < 0.01


class TestIdeologyMapReproducibility:
    def test_same_seed_same_voters(self, client):
        r1 = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        r2 = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        assert r1 == r2, "Same seed should produce identical voter positions"

    def test_different_seed_different_voters(self, client):
        payload2 = {**BASE_PAYLOAD, "seed": 99}
        v1 = json.loads(post(client, BASE_PAYLOAD).data)["voters"]
        v2 = json.loads(post(client, payload2).data)["voters"]
        # At least one voter should differ
        assert any(a["x"] != b["x"] or a["y"] != b["y"] for a, b in zip(v1, v2))


class TestIdeologyMapCandidateDrag:
    def test_moving_candidate_can_change_winners(self, client):
        """Shifting one candidate far to an extreme should affect election results."""
        left_payload = {**BASE_PAYLOAD, "candidates": [
            {"name": "Alice", "x": -0.9, "y": 0.0},
            {"name": "Bob",   "x": -0.8, "y": 0.0},
            {"name": "Carol", "x": -0.7, "y": 0.0},
        ]}
        right_payload = {**BASE_PAYLOAD, "candidates": [
            {"name": "Alice", "x":  0.7, "y": 0.0},
            {"name": "Bob",   "x":  0.8, "y": 0.0},
            {"name": "Carol", "x":  0.9, "y": 0.0},
        ]}
        b_left  = json.loads(post(client, left_payload).data)
        b_right = json.loads(post(client, right_payload).data)
        # With different positions the pct distributions should differ
        assert (
            b_left["pct_better_off_with_a"] != b_right["pct_better_off_with_a"]
            or b_left["winner_a"] != b_right["winner_a"]
        )


class TestIdeologyMapValidation:
    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE_PAYLOAD, "candidates": [{"name": "Alice", "x": 0.0, "y": 0.0}]}
        r = post(client, payload)
        assert r.status_code == 400
        assert "error" in json.loads(r.data)

    def test_num_voters_clamped(self, client):
        payload = {**BASE_PAYLOAD, "num_voters": 9999}
        body    = json.loads(post(client, payload).data)
        # Should be clamped to 500
        assert len(body["voters"]) == 500

    def test_method_a_in_response(self, client):
        body = json.loads(post(client, BASE_PAYLOAD).data)
        assert body["method_a"] == BASE_PAYLOAD["method_a"]
        assert body["method_b"] == BASE_PAYLOAD["method_b"]
