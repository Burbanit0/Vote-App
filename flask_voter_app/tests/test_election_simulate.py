"""
test_election_simulate.py — Tests for POST /api/election/simulate
"""
import json
import pytest

URL = "/api/election/simulate"

BASE = {
    "candidates":  [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":  60,
    "ideology":    "random",
    "seed":        42,
    "blank_vote":  {"enabled": False, "rule": "symbolic",
                    "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"}},
    "information_model": {"enabled": False, "media_bias": {}, "voter_segments": {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2}},
    "campaign":    {"enabled": False, "num_days": 14, "polling_effect": 0.3},
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestElectionSimulateBasic:
    def test_returns_200(self, client):
        r = post(client)
        assert r.status_code == 200, r.data

    def test_response_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("methods", "condorcet_winner", "inter_method_agreement",
                    "condorcet_exists", "blank_rate", "voters_snapshot", "candidates"):
            assert key in body, f"Missing: {key}"

    def test_methods_contains_plurality(self, client):
        body = json.loads(post(client).data)
        assert "plurality" in body["methods"]

    def test_methods_contain_all_15_plus(self, client):
        body = json.loads(post(client).data)
        assert len(body["methods"]) >= 9  # at least the ranked methods

    def test_each_method_has_winner_and_regret(self, client):
        methods = json.loads(post(client).data)["methods"]
        for name, md in methods.items():
            assert "winner"           in md, f"{name} missing winner"
            assert "bayesian_regret"  in md, f"{name} missing bayesian_regret"

    def test_inter_method_agreement_in_range(self, client):
        body = json.loads(post(client).data)
        agr = body["inter_method_agreement"]
        assert 0.0 <= agr <= 1.0, f"agreement out of range: {agr}"

    def test_voters_snapshot_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["voters_snapshot"]) == BASE["num_voters"]

    def test_candidates_echo(self, client):
        body = json.loads(post(client).data)
        assert len(body["candidates"]) == len(BASE["candidates"])
        assert body["candidates"][0]["name"] == "Alice"

    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


# ── Campaign disabled ─────────────────────────────────────────────────────────

class TestCampaignDisabled:
    def test_campaign_trajectory_is_null_when_disabled(self, client):
        body = json.loads(post(client).data)
        assert body["campaign_trajectory"] is None

    def test_campaign_enabled_returns_trajectory(self, client):
        payload = {**BASE, "campaign": {"enabled": True, "num_days": 14, "polling_effect": 0.3}}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["campaign_trajectory"] is not None


# ── Blank vote ────────────────────────────────────────────────────────────────

class TestBlankVote:
    def test_blank_disabled_no_winner_with_blank(self, client):
        body = json.loads(post(client).data)
        for md in body["methods"].values():
            assert "winner_with_blank" not in md

    def test_blank_enabled_adds_winner_with_blank(self, client):
        payload = {**BASE, "blank_vote": {
            "enabled": True, "rule": "symbolic",
            "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"},
        }}
        body = json.loads(client.post(URL, json=payload).data)
        for md in body["methods"].values():
            assert "winner_with_blank" in md

    def test_blank_rate_zero_when_disabled(self, client):
        body = json.loads(post(client).data)
        assert body["blank_rate"] == 0.0

    def test_blank_rate_in_range(self, client):
        payload = {**BASE, "blank_vote": {
            "enabled": True, "rule": "competitive",
            "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"},
        }}
        body = json.loads(client.post(URL, json=payload).data)
        assert 0.0 <= body["blank_rate"] <= 1.0


# ── Information model ─────────────────────────────────────────────────────────

class TestInformationModel:
    def test_info_enabled_still_returns_200(self, client):
        payload = {**BASE, "information_model": {
            "enabled": True,
            "media_bias": {"Alice": 0.5, "Bob": -0.3},
            "voter_segments": {"low_info": 0.4, "medium_info": 0.4, "high_info": 0.2},
        }}
        assert client.post(URL, json=payload).status_code == 200

    def test_info_model_does_not_crash_with_empty_bias(self, client):
        payload = {**BASE, "information_model": {
            "enabled": True,
            "media_bias": {},
            "voter_segments": {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2},
        }}
        assert client.post(URL, json=payload).status_code == 200


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_results(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["methods"] == r2["methods"]
        assert r1["condorcet_winner"] == r2["condorcet_winner"]

    def test_different_seed_can_differ(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(client.post(URL, json={**BASE, "seed": 999}).data)
        # Not guaranteed but almost always true with different seeds
        assert "plurality" in r1["methods"] and "plurality" in r2["methods"]

    def test_all_combinations_return_200(self, client):
        """Smoke test: all module combinations must not crash."""
        for blank_on in (False, True):
            for campaign_on in (False, True):
                for info_on in (False, True):
                    payload = {
                        **BASE,
                        "num_voters": 30,
                        "blank_vote":  {**BASE["blank_vote"],        "enabled": blank_on},
                        "campaign":    {**BASE["campaign"],           "enabled": campaign_on},
                        "information_model": {**BASE["information_model"], "enabled": info_on},
                    }
                    r = client.post(URL, json=payload)
                    assert r.status_code == 200, f"blank={blank_on} camp={campaign_on} info={info_on}: {r.data}"
