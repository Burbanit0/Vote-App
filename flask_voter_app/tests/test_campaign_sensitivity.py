"""
test_campaign_sensitivity.py — Tests for POST /api/election/campaign-sensitivity
"""
import json
import pytest

URL = "/api/election/campaign-sensitivity"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":  40,
    "ideology":    "random",
    "seed":        42,
    "campaign": {
        "enabled":        True,
        "num_days":       14,
        "polling_effect": 0.4,
    },
    "blank_vote": {
        "enabled":   False,
        "rule":      "symbolic",
        "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"},
    },
    "snapshot_days": [0, 7, 14],
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestCampaignSensitivityBasic:
    def test_returns_200(self, client):
        r = post(client)
        assert r.status_code == 200, r.data

    def test_response_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("snapshots", "method_stability", "most_stable_method", "least_stable_method"):
            assert key in body, f"Missing: {key}"

    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


# ── Snapshots ─────────────────────────────────────────────────────────────────

class TestSnapshots:
    def test_contains_at_least_j0_and_jfinal(self, client):
        body = json.loads(post(client).data)
        days = [s["day"] for s in body["snapshots"]]
        assert 0 in days, "Day 0 missing"
        assert BASE["campaign"]["num_days"] in days or max(days) >= 14, "Final day missing"

    def test_snapshot_count_matches_request(self, client):
        body = json.loads(post(client).data)
        assert len(body["snapshots"]) == len(set(BASE["snapshot_days"]))

    def test_each_snapshot_has_methods_and_agreement(self, client):
        for snap in json.loads(post(client).data)["snapshots"]:
            assert "day"                   in snap
            assert "methods"               in snap
            assert "inter_method_agreement" in snap

    def test_each_method_has_winner_and_vote_share(self, client):
        for snap in json.loads(post(client).data)["snapshots"]:
            for name, md in snap["methods"].items():
                assert "winner"     in md, f"{name} missing winner"
                assert "vote_share" in md, f"{name} missing vote_share"

    def test_agreement_values_in_range(self, client):
        for snap in json.loads(post(client).data)["snapshots"]:
            a = snap["inter_method_agreement"]
            assert 0.0 <= a <= 1.0, f"agreement {a} out of range"

    def test_vote_share_in_range(self, client):
        for snap in json.loads(post(client).data)["snapshots"]:
            for md in snap["methods"].values():
                assert 0.0 <= md["vote_share"] <= 1.0

    def test_final_keyword_resolves(self, client):
        payload = {**BASE, "snapshot_days": [0, "final"]}
        body = json.loads(post(client, payload).data)
        days = [s["day"] for s in body["snapshots"]]
        assert len(days) == 2
        assert 0 in days

    def test_days_are_sorted_ascending(self, client):
        body = json.loads(post(client).data)
        days = [s["day"] for s in body["snapshots"]]
        assert days == sorted(days)


# ── Method stability ──────────────────────────────────────────────────────────

class TestMethodStability:
    def test_method_stability_contains_all_methods(self, client):
        body = json.loads(post(client).data)
        snap_methods = set(body["snapshots"][0]["methods"].keys())
        stab_methods = set(body["method_stability"].keys())
        assert snap_methods == stab_methods

    def test_stability_score_in_range(self, client):
        for method, data in json.loads(post(client).data)["method_stability"].items():
            score = data["stability_score"]
            assert 0.0 <= score <= 1.0, f"{method}: score {score} out of range"

    def test_winner_changes_non_negative(self, client):
        for method, data in json.loads(post(client).data)["method_stability"].items():
            assert data["winner_changes"] >= 0

    def test_most_and_least_stable_are_known_methods(self, client):
        body = json.loads(post(client).data)
        methods = set(body["method_stability"].keys())
        assert body["most_stable_method"]  in methods
        assert body["least_stable_method"] in methods

    def test_most_stable_has_highest_score(self, client):
        body = json.loads(post(client).data)
        stab = body["method_stability"]
        most = body["most_stable_method"]
        max_score = max(d["stability_score"] for d in stab.values())
        assert stab[most]["stability_score"] == max_score


# ── Polling effect ────────────────────────────────────────────────────────────

class TestPollingEffect:
    def test_zero_polling_effect_returns_200(self, client):
        payload = {**BASE, "campaign": {**BASE["campaign"], "polling_effect": 0.0}}
        assert post(client, payload).status_code == 200

    def test_single_snapshot_stability_score_is_one(self, client):
        payload = {**BASE, "snapshot_days": [0]}
        body = json.loads(post(client, payload).data)
        for method, data in body["method_stability"].items():
            assert data["stability_score"] == 1.0, f"{method}: score should be 1.0 with 1 snap"

    def test_with_contagion_still_returns_200(self, client):
        payload = {
            **BASE,
            "blank_vote": {
                "enabled":   True,
                "rule":      "competitive",
                "contagion": {"enabled": True, "beta": 0.3, "gamma": 0.1, "network": "random"},
            },
        }
        assert post(client, payload).status_code == 200


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_results(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["method_stability"] == r2["method_stability"]
        assert r1["most_stable_method"] == r2["most_stable_method"]
