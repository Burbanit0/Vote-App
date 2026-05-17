"""
test_gerrymander.py — Tests for POST /api/election/gerrymander
"""
import json
import pytest

URL = "/api/election/gerrymander"

# Full coverage of [-1,1]×[-1,1]
FULL_DISTRICT = [{"id": 0, "bounds": {"x_min": -1.0, "x_max": 1.0, "y_min": -1.0, "y_max": 1.0}}]

# Two equal horizontal halves
TWO_DISTRICTS = [
    {"id": 0, "bounds": {"x_min": -1.0, "x_max": 1.0, "y_min":  0.0, "y_max": 1.0}},
    {"id": 1, "bounds": {"x_min": -1.0, "x_max": 1.0, "y_min": -1.0, "y_max": 0.0}},
]

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
    ],
    "num_voters": 100,
    "ideology":   "random",
    "seed":       42,
    "districts":  TWO_DISTRICTS,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestGerrymanderBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("districts", "voters", "parliament_gerrymander",
                  "parliament_proportional", "national_vote_share",
                  "distortion", "gerrymander_index", "winner", "candidates"):
            assert k in body, f"Missing key: {k}"

    def test_requires_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert post(client, payload).status_code == 400

    def test_requires_districts(self, client):
        payload = {**BASE, "districts": []}
        assert post(client, payload).status_code == 400

    def test_district_count_in_response(self, client):
        body = json.loads(post(client).data)
        assert len(body["districts"]) == len(BASE["districts"])

    def test_gerrymander_index_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["gerrymander_index"] <= 1.0

    def test_distortion_non_negative(self, client):
        body = json.loads(post(client).data)
        assert body["distortion"] >= 0.0


# ── Single district → all voters in one place ─────────────────────────────────

class TestSingleDistrict:
    def test_all_voters_assigned_to_single_district(self, client):
        payload = {**BASE, "districts": FULL_DISTRICT}
        body = json.loads(post(client, payload).data)
        assert body["districts"][0]["num_voters"] == BASE["num_voters"]

    def test_parliament_has_one_seat(self, client):
        payload = {**BASE, "districts": FULL_DISTRICT}
        body = json.loads(post(client, payload).data)
        total = sum(body["parliament_gerrymander"].values())
        assert total == 1

    def test_proportional_also_one_seat(self, client):
        payload = {**BASE, "districts": FULL_DISTRICT}
        body = json.loads(post(client, payload).data)
        total = sum(body["parliament_proportional"].values())
        assert total == 1

    def test_single_district_winner_is_national_leader(self, client):
        payload = {**BASE, "districts": FULL_DISTRICT}
        body = json.loads(post(client, payload).data)
        gerry_winner = max(
            body["parliament_gerrymander"],
            key=lambda k: body["parliament_gerrymander"][k],
        )
        assert gerry_winner == body["winner"]


# ── Seats sum to district count ───────────────────────────────────────────────

class TestSeatSums:
    def test_gerry_seats_sum_to_num_districts(self, client):
        body = json.loads(post(client).data)
        total = sum(body["parliament_gerrymander"].values())
        assert total == len(BASE["districts"])

    def test_proportional_seats_sum_to_num_districts(self, client):
        body = json.loads(post(client).data)
        total = sum(body["parliament_proportional"].values())
        assert total == len(BASE["districts"])

    def test_national_vote_share_sums_to_one(self, client):
        body = json.loads(post(client).data)
        total = sum(body["national_vote_share"].values())
        assert abs(total - 1.0) < 0.05


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["winner"]                 == r2["winner"]
        assert r1["distortion"]             == r2["distortion"]
        assert r1["gerrymander_index"]      == r2["gerrymander_index"]
        assert r1["parliament_gerrymander"] == r2["parliament_gerrymander"]

    def test_different_seed_may_differ(self, client):
        r1 = json.loads(post(client, {**BASE, "seed": 42}).data)
        r2 = json.loads(post(client, {**BASE, "seed": 999}).data)
        # Both valid — just verify they complete
        assert "winner" in r1
        assert "winner" in r2


# ── Equitable split → low distortion ─────────────────────────────────────────

class TestEquitableDistricts:
    def test_voters_snapshot_present(self, client):
        body = json.loads(post(client).data)
        assert len(body["voters"]) > 0
        voter = body["voters"][0]
        assert "x" in voter and "y" in voter and "preferred" in voter

    def test_per_district_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for d in body["districts"]:
            if d["num_voters"] > 0:
                total = sum(d["vote_shares"].values())
                assert abs(total - 1.0) < 0.05, f"District {d['id']}: sum={total}"
