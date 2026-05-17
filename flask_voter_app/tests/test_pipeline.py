"""
test_pipeline.py — Tests for POST /api/election/simulate-pipeline
"""
import json
import pytest

URL = "/api/election/simulate-pipeline"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
    ],
    "num_voters":  30,
    "ideology":    "random",
    "seed":        42,
    "blank_vote":  {"enabled": False, "rule": "symbolic",
                    "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"}},
    "information_model": {"enabled": False, "media_bias": {},
                          "voter_segments": {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2}},
    "campaign":    {"enabled": False, "num_days": 14, "polling_effect": 0.3},
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


class TestPipelineBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_has_steps_and_candidates(self, client):
        body = json.loads(post(client).data)
        assert "steps"      in body
        assert "candidates" in body
        assert "num_steps"  in body

    def test_minimum_two_steps_base_and_results(self, client):
        body = json.loads(post(client).data)
        ids  = [s["id"] for s in body["steps"]]
        assert ids[0] == "base"
        assert ids[-1] == "results"

    def test_voters_count_matches_num_voters(self, client):
        body     = json.loads(post(client).data)
        n_voters = len(body["steps"][0]["voters"])
        assert n_voters == BASE["num_voters"]

    def test_voter_has_required_fields(self, client):
        body  = json.loads(post(client).data)
        voter = body["steps"][0]["voters"][0]
        assert "id"         in voter
        assert "x"          in voter
        assert "y"          in voter
        assert "preference" in voter
        assert "is_blank"   in voter

    def test_voter_coords_in_domain_range(self, client):
        body = json.loads(post(client).data)
        for step in body["steps"]:
            for v in step["voters"]:
                assert -1.0 <= v["x"] <= 1.0
                assert -1.0 <= v["y"] <= 1.0

    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


class TestPipelineWithModels:
    def test_campaign_enabled_adds_step(self, client):
        payload = {**BASE, "campaign": {"enabled": True, "num_days": 14, "polling_effect": 0.3}}
        body    = json.loads(post(client, payload).data)
        ids     = [s["id"] for s in body["steps"]]
        assert "campaign" in ids

    def test_contagion_enabled_adds_step(self, client):
        payload = {
            **BASE,
            "blank_vote": {
                "enabled": True, "rule": "symbolic",
                "contagion": {"enabled": True, "beta": 0.3, "gamma": 0.1, "network": "random"},
            },
        }
        body = json.loads(post(client, payload).data)
        ids  = [s["id"] for s in body["steps"]]
        assert "contagion" in ids

    def test_info_model_enabled_adds_step(self, client):
        payload = {
            **BASE,
            "information_model": {
                "enabled": True,
                "media_bias": {"Alice": 0.5},
                "voter_segments": {"low_info": 0.4, "medium_info": 0.4, "high_info": 0.2},
            },
        }
        body = json.loads(post(client, payload).data)
        ids  = [s["id"] for s in body["steps"]]
        assert "information" in ids

    def test_all_models_gives_5_steps(self, client):
        payload = {
            **BASE,
            "campaign": {"enabled": True, "num_days": 14, "polling_effect": 0.3},
            "blank_vote": {
                "enabled": True, "rule": "symbolic",
                "contagion": {"enabled": True, "beta": 0.2, "gamma": 0.1, "network": "random"},
            },
            "information_model": {
                "enabled": True, "media_bias": {},
                "voter_segments": {"low_info": 0.3, "medium_info": 0.5, "high_info": 0.2},
            },
        }
        body = json.loads(post(client, payload).data)
        assert len(body["steps"]) == 5


class TestResultsStep:
    def test_results_step_has_winner_groups(self, client):
        body    = json.loads(post(client).data)
        results = next(s for s in body["steps"] if s["id"] == "results")
        assert "winner_groups" in results
        assert isinstance(results["winner_groups"], list)

    def test_results_step_has_agreement_metric(self, client):
        body    = json.loads(post(client).data)
        results = next(s for s in body["steps"] if s["id"] == "results")
        assert "inter_method_agreement" in results["metrics"]

    def test_results_winner_groups_cover_methods(self, client):
        body    = json.loads(post(client).data)
        results = next(s for s in body["steps"] if s["id"] == "results")
        # Sum of methods in groups should be > 0
        total = sum(len(g["methods"]) for g in results["winner_groups"])
        assert total > 0


class TestReproducibility:
    def test_same_seed_same_results(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["steps"][0]["voters"] == r2["steps"][0]["voters"]
