"""
test_polarization.py — Tests for POST /api/election/polarization
"""
import json
import pytest

URL = "/api/election/polarization"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":      80,
    "ideology_range":  ["centrist", "polarized"],
    "seed":            42,
    "num_simulations": 5,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestPolarizationBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        assert "results" in body
        assert "key_findings" in body

    def test_results_count_equals_ideologies(self, client):
        body = json.loads(post(client).data)
        assert len(body["results"]) == len(BASE["ideology_range"])

    def test_result_keys(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            for k in ("ideology", "polarization_index", "condorcet_rate",
                      "agreement_rate", "winner_stability", "best_method",
                      "worst_method"):
                assert k in r, f"Missing key: {k}"

    def test_key_findings_not_empty(self, client):
        body = json.loads(post(client).data)
        assert len(body["key_findings"]) > 0

    def test_requires_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert post(client, payload).status_code == 400


# ── Esteban-Ray index ordering ────────────────────────────────────────────────

class TestPolarizationIndex:
    def test_centrist_lower_than_polarized(self, client):
        """Centrist electorate should have lower polarization than polarized."""
        body = json.loads(post(client).data)
        results = {r["ideology"]: r for r in body["results"]}
        centrist  = results.get("centrist",  {}).get("polarization_index", 0)
        polarized = results.get("polarized", {}).get("polarization_index", 0)
        assert centrist <= polarized, (
            f"centrist P={centrist:.3f} should be ≤ polarized P={polarized:.3f}"
        )

    def test_polarization_index_non_negative(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert r["polarization_index"] >= 0.0

    def test_rates_in_valid_range(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert 0.0 <= r["condorcet_rate"]  <= 1.0
            assert 0.0 <= r["agreement_rate"]  <= 1.0
            assert 0.0 <= r["winner_stability"] <= 1.0

    def test_all_ideologies_returned(self, client):
        payload = {**BASE, "ideology_range": ["centrist", "random", "polarized"]}
        body = json.loads(post(client, payload).data)
        ideologies = {r["ideology"] for r in body["results"]}
        assert ideologies == {"centrist", "random", "polarized"}


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestPolarizationReproducibility:
    def test_same_seed_same_indices(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        for res1, res2 in zip(r1["results"], r2["results"]):
            assert res1["ideology"] == res2["ideology"]
            assert abs(res1["polarization_index"] - res2["polarization_index"]) < 0.001


# ── Method regrets ────────────────────────────────────────────────────────────

class TestMethodRegrets:
    def test_method_regrets_present(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert isinstance(r["method_regrets"], dict)
            assert len(r["method_regrets"]) > 0

    def test_best_method_is_in_regrets(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            if r["best_method"]:
                assert r["best_method"] in r["method_regrets"]

    def test_best_has_lower_regret_than_worst(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            best  = r["best_method"]
            worst = r["worst_method"]
            if best and worst and best != worst:
                assert r["method_regrets"].get(best, 0) <= r["method_regrets"].get(worst, 1)
