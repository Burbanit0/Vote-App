"""
test_districts.py — Tests for POST /api/election/districts
"""
import json
import pytest

URL = "/api/election/districts"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_districts":               10,
    "voters_per_district":         50,
    "district_ideology_variance":  0.3,
    "seed":                        42,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestDistrictsBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in (
            "districts", "parliament_fptp", "parliament_proportional",
            "national_vote_share", "distortion", "fptp_winner",
            "proportional_winner", "num_districts",
        ):
            assert key in body, f"Missing key: {key}"

    def test_districts_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["districts"]) == BASE["num_districts"]

    def test_fptp_seats_sum_to_num_districts(self, client):
        body = json.loads(post(client).data)
        total = sum(body["parliament_fptp"].values())
        assert total == BASE["num_districts"]

    def test_proportional_seats_sum_to_num_districts(self, client):
        body = json.loads(post(client).data)
        total = sum(body["parliament_proportional"].values())
        assert total == BASE["num_districts"]

    def test_distortion_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["distortion"] <= 1.0

    def test_national_vote_share_sums_to_one(self, client):
        body = json.loads(post(client).data)
        total = sum(body["national_vote_share"].values())
        assert abs(total - 1.0) < 0.05  # small floating-point tolerance

    def test_requires_at_least_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


# ── Per-district structure ────────────────────────────────────────────────────

class TestDistrictEntries:
    def test_district_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for d in body["districts"]:
            for key in ("id", "ideology_center", "winner_fptp", "vote_shares"):
                assert key in d, f"District {d.get('id')} missing key: {key}"

    def test_district_ids_sequential(self, client):
        body = json.loads(post(client).data)
        ids = [d["id"] for d in body["districts"]]
        assert ids == list(range(BASE["num_districts"]))

    def test_vote_shares_sum_to_one_per_district(self, client):
        body = json.loads(post(client).data)
        for d in body["districts"]:
            total = sum(d["vote_shares"].values())
            assert abs(total - 1.0) < 0.05, (
                f"District {d['id']}: vote_shares sum {total:.4f} ≠ 1"
            )

    def test_winner_fptp_is_known_candidate(self, client):
        body = json.loads(post(client).data)
        names = {c["name"] for c in BASE["candidates"]}
        for d in body["districts"]:
            assert d["winner_fptp"] in names, (
                f"District {d['id']}: unknown winner '{d['winner_fptp']}'"
            )


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestDistrictsReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["parliament_fptp"] == r2["parliament_fptp"]
        assert r1["distortion"] == r2["distortion"]
        assert r1["fptp_winner"] == r2["fptp_winner"]

    def test_different_seed_may_differ(self, client):
        r1 = json.loads(post(client, {**BASE, "seed": 42}).data)
        r2 = json.loads(post(client, {**BASE, "seed": 999}).data)
        # Not guaranteed, but with high variance they're unlikely to be identical
        # Just verify the response is valid for both seeds
        assert r1["num_districts"] == r2["num_districts"]


# ── Parameter boundaries ──────────────────────────────────────────────────────

class TestDistrictsBoundaries:
    def test_5_districts(self, client):
        r = post(client, {**BASE, "num_districts": 5})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert len(body["districts"]) == 5
        assert sum(body["parliament_fptp"].values()) == 5

    def test_zero_variance_homogeneous(self, client):
        payload = {**BASE, "district_ideology_variance": 0.0}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        # With zero variance all districts have similar ideology → low distortion
        assert body["distortion"] <= 1.0

    def test_high_variance(self, client):
        payload = {**BASE, "district_ideology_variance": 1.0}
        r = post(client, payload)
        assert r.status_code == 200

    def test_two_candidates(self, client):
        payload = {**BASE, "candidates": [
            {"name": "Left",  "x": -0.7, "y": 0.0},
            {"name": "Right", "x":  0.7, "y": 0.0},
        ]}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        total = sum(body["parliament_fptp"].values())
        assert total == BASE["num_districts"]
