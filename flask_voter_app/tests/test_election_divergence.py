"""
test_election_divergence.py — Tests for POST /api/election/divergence
"""
import json
import pytest

URL = "/api/election/divergence"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters": 60,
    "ideology":   "random",
    "seed":       42,
    "blank_vote": {
        "rule":      "symbolic",
        "contagion": {"enabled": False, "beta": 0.1, "gamma": 0.1, "network": "random"},
    },
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestDivergenceBasic:
    def test_returns_200(self, client):
        r = post(client)
        assert r.status_code == 200, r.data

    def test_response_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("without_blank", "with_blank", "delta_agreement",
                    "methods_changed", "pct_methods_changed", "blank_rule"):
            assert key in body, f"Missing: {key}"

    def test_without_blank_structure(self, client):
        body = json.loads(post(client).data)
        wb = body["without_blank"]
        assert "methods"               in wb
        assert "inter_method_agreement" in wb
        assert "condorcet_winner"      in wb

    def test_with_blank_structure(self, client):
        body = json.loads(post(client).data)
        wb = body["with_blank"]
        assert "methods"               in wb
        assert "inter_method_agreement" in wb
        assert "condorcet_winner"      in wb
        assert "blank_rate"            in wb

    def test_with_blank_methods_have_winner_after_rule(self, client):
        methods = json.loads(post(client).data)["with_blank"]["methods"]
        for name, md in methods.items():
            assert "winner_after_rule" in md, f"{name} missing winner_after_rule"

    def test_too_few_candidates_returns_400(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400


# ── Delta agreement ───────────────────────────────────────────────────────────

class TestDeltaAgreement:
    def test_delta_agreement_equals_with_minus_without(self, client):
        body = json.loads(post(client).data)
        delta_computed = (
            body["with_blank"]["inter_method_agreement"]
            - body["without_blank"]["inter_method_agreement"]
        )
        assert abs(body["delta_agreement"] - delta_computed) < 0.01

    def test_agreement_values_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["without_blank"]["inter_method_agreement"] <= 1.0
        assert 0.0 <= body["with_blank"]["inter_method_agreement"]    <= 1.0

    def test_pct_methods_changed_in_range(self, client):
        body = json.loads(post(client).data)
        pct = body["pct_methods_changed"]
        assert 0.0 <= pct <= 1.0

    def test_methods_changed_are_valid_methods(self, client):
        body = json.loads(post(client).data)
        all_methods = set(body["without_blank"]["methods"].keys())
        for m in body["methods_changed"]:
            assert m in all_methods, f"'{m}' not a known method"


# ── Blank-vote rules ──────────────────────────────────────────────────────────

class TestBlankRules:
    def test_symbolic_rule_echoed_in_response(self, client):
        body = json.loads(post(client, {**BASE, "blank_vote": {**BASE["blank_vote"], "rule": "symbolic"}}).data)
        assert body["blank_rule"] == "symbolic"

    def test_competitive_rule_echoed(self, client):
        payload = {**BASE, "blank_vote": {**BASE["blank_vote"], "rule": "competitive"}}
        body = json.loads(post(client, payload).data)
        assert body["blank_rule"] == "competitive"

    def test_blank_rate_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["with_blank"]["blank_rate"] <= 1.0

    def test_without_blank_methods_have_no_winner_after_rule(self, client):
        # Run without blank should NOT have winner_after_rule
        methods = json.loads(post(client).data)["without_blank"]["methods"]
        for name, md in methods.items():
            assert "winner_after_rule" not in md


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_results(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["without_blank"]["methods"] == r2["without_blank"]["methods"]
        assert r1["delta_agreement"]          == r2["delta_agreement"]
        assert r1["methods_changed"]          == r2["methods_changed"]

    def test_all_rules_return_200(self, client):
        for rule in ("symbolic", "competitive", "threshold_30"):
            payload = {**BASE, "blank_vote": {**BASE["blank_vote"], "rule": rule}}
            r = post(client, payload)
            assert r.status_code == 200, f"rule={rule}: {r.data}"

    def test_with_contagion_still_returns_200(self, client):
        payload = {
            **BASE,
            "blank_vote": {
                "rule": "competitive",
                "contagion": {"enabled": True, "beta": 0.3, "gamma": 0.1, "network": "random"},
            },
        }
        assert post(client, payload).status_code == 200
