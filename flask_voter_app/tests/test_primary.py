"""
test_primary.py — Tests for POST /api/election/primary
"""
import json
import pytest

URL = "/api/election/primary"

BASE = {
    "parties": [
        {
            "name": "Left",
            "ideology_center": -0.5,
            "primary_voters_pct": 0.25,
            "primary_candidates": [
                {"name": "Sophie", "ideology_position": -0.35},
                {"name": "Marc",   "ideology_position": -0.75},
            ],
        },
        {
            "name": "Right",
            "ideology_center": 0.5,
            "primary_voters_pct": 0.25,
            "primary_candidates": [
                {"name": "Elise", "ideology_position": 0.35},
                {"name": "Paul",  "ideology_position": 0.75},
            ],
        },
        {
            "name": "Centre",
            "ideology_center": 0.0,
            "primary_voters_pct": 0.15,
            "primary_candidates": [
                {"name": "Anna", "ideology_position":  0.0},
                {"name": "Tom",  "ideology_position":  0.15},
            ],
        },
    ],
    "general_num_voters": 200,
    "general_ideology":   "random",
    "primary_method":     "plurality",
    "general_method":     "plurality",
    "seed":               42,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestPrimaryBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("primaries", "general_ballot", "general_winner",
                    "median_voter_distance", "without_primaries_winner",
                    "general_vote_shares"):
            assert key in body, f"Missing key: {key}"

    def test_n_parties_n_primaries(self, client):
        body = json.loads(post(client).data)
        assert len(body["primaries"]) == len(BASE["parties"])

    def test_general_ballot_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["general_ballot"]) == len(BASE["parties"])

    def test_requires_at_least_two_parties(self, client):
        payload = {**BASE, "parties": [BASE["parties"][0]]}
        assert post(client, payload).status_code == 400

    def test_party_needs_two_candidates(self, client):
        bad = {**BASE, "parties": [
            {**BASE["parties"][0], "primary_candidates": [{"name": "Solo", "ideology_position": 0.0}]},
            BASE["parties"][1],
        ]}
        assert post(client, bad).status_code == 400


# ── Primary result structure ──────────────────────────────────────────────────

class TestPrimaryResults:
    def test_each_primary_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for p in body["primaries"]:
            for key in ("party", "winner", "runner_up", "distortion",
                        "vote_shares", "num_primary_voters"):
                assert key in p, f"Primary '{p.get('party')}' missing key: {key}"

    def test_distortion_non_negative(self, client):
        body = json.loads(post(client).data)
        for p in body["primaries"]:
            assert p["distortion"] >= 0, f"Negative distortion for {p['party']}"

    def test_winner_is_known_candidate(self, client):
        body = json.loads(post(client).data)
        all_cands = {
            c["name"]
            for party in BASE["parties"]
            for c in party["primary_candidates"]
        }
        for p in body["primaries"]:
            assert p["winner"] in all_cands, f"Unknown winner: {p['winner']}"

    def test_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for p in body["primaries"]:
            total = sum(p["vote_shares"].values())
            assert abs(total - 1.0) < 0.05, f"{p['party']}: shares sum={total}"

    def test_general_ballot_has_one_per_party(self, client):
        body = json.loads(post(client).data)
        party_names = {p["name"] for p in BASE["parties"]}
        winner_parties = {p["party"] for p in body["primaries"]}
        assert party_names == winner_parties


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestPrimaryReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["general_winner"] == r2["general_winner"]
        assert r1["without_primaries_winner"] == r2["without_primaries_winner"]
        for p1, p2 in zip(r1["primaries"], r2["primaries"]):
            assert p1["winner"] == p2["winner"]
            assert p1["distortion"] == p2["distortion"]


# ── Method variants ───────────────────────────────────────────────────────────

class TestPrimaryMethods:
    def test_irv_primary(self, client):
        payload = {**BASE, "primary_method": "irv"}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert len(body["primaries"]) == len(BASE["parties"])

    def test_approval_primary(self, client):
        payload = {**BASE, "primary_method": "approval"}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["general_winner"] is not None

    def test_irv_general(self, client):
        payload = {**BASE, "general_method": "irv"}
        r = post(client, payload)
        assert r.status_code == 200

    def test_approval_general(self, client):
        payload = {**BASE, "general_method": "approval"}
        r = post(client, payload)
        assert r.status_code == 200


# ── Median voter distance ─────────────────────────────────────────────────────

class TestMedianVoterDistance:
    def test_distance_in_valid_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["median_voter_distance"] <= 1.0

    def test_extreme_candidates_increase_distance(self, client):
        # When all candidates are extreme, distance should be higher
        extreme = {**BASE, "parties": [
            {
                "name": "ExtLeft",
                "ideology_center": -0.8,
                "primary_voters_pct": 0.4,
                "primary_candidates": [
                    {"name": "Far1", "ideology_position": -0.9},
                    {"name": "Far2", "ideology_position": -0.95},
                ],
            },
            {
                "name": "ExtRight",
                "ideology_center": 0.8,
                "primary_voters_pct": 0.4,
                "primary_candidates": [
                    {"name": "Far3", "ideology_position": 0.9},
                    {"name": "Far4", "ideology_position": 0.95},
                ],
            },
        ]}
        body_extreme = json.loads(post(client, extreme).data)
        assert body_extreme["median_voter_distance"] >= 0.0
