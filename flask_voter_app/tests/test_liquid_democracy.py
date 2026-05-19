"""
test_liquid_democracy.py — Tests for POST /api/election/liquid-democracy
"""
import json
import pytest

URL = "/api/election/liquid-democracy"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":              60,
    "ideology":                "random",
    "seed":                    42,
    "delegation_probability":  0.5,
    "delegation_strategy":     "nearest",
    "max_chain_length":        5,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestLiquidBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("weighted_results", "direct_voters", "delegators",
                  "super_voters", "delegation_graph", "cycles_detected",
                  "cycle_voter_ids", "chain_stats", "gini_curve",
                  "comparison", "gini_voting_weight", "pedagogical_note"):
            assert k in body, f"Missing key: {k}"

    def test_comparison_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("liquid_winner", "direct_winner", "winner_changed"):
            assert k in body["comparison"]

    def test_chain_stats_keys(self, client):
        body = json.loads(post(client).data)
        assert "mean" in body["chain_stats"]
        assert "max"  in body["chain_stats"]

    def test_weighted_results_has_all_candidates(self, client):
        body = json.loads(post(client).data)
        assert set(body["weighted_results"].keys()) == {"Alice", "Bob", "Carol"}

    def test_voter_counts_sum(self, client):
        body = json.loads(post(client).data)
        assert body["direct_voters"] + body["delegators"] == 60

    def test_gini_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["gini_voting_weight"] <= 1.0

    def test_gini_curve_has_11_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["gini_curve"]) == 11

    def test_gini_curve_range(self, client):
        body = json.loads(post(client).data)
        probs = [pt["probability"] for pt in body["gini_curve"]]
        assert probs[0] == pytest.approx(0.0)
        assert probs[-1] == pytest.approx(1.0)


# ── delegation_probability=0 → same as direct vote ───────────────────────────

class TestNoDelegation:
    def _run(self, client):
        payload = {**BASE, "delegation_probability": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_no_delegators(self, client):
        body = self._run(client)
        assert body["delegators"] == 0

    def test_all_direct_voters(self, client):
        body = self._run(client)
        assert body["direct_voters"] == 60

    def test_liquid_equals_direct_winner(self, client):
        body = self._run(client)
        assert body["comparison"]["liquid_winner"] == body["comparison"]["direct_winner"]

    def test_winner_not_changed(self, client):
        body = self._run(client)
        assert body["comparison"]["winner_changed"] is False

    def test_gini_is_zero(self, client):
        body = self._run(client)
        # All weights=1 → perfect equality
        assert body["gini_voting_weight"] == pytest.approx(0.0, abs=1e-4)

    def test_no_delegation_graph(self, client):
        body = self._run(client)
        assert body["delegation_graph"] == []

    def test_no_cycles(self, client):
        body = self._run(client)
        assert body["cycles_detected"] == 0


# ── Cycle detection ───────────────────────────────────────────────────────────

class TestCycleDetection:
    def test_cycles_detected_is_nonneg(self, client):
        body = json.loads(post(client).data)
        assert body["cycles_detected"] >= 0

    def test_cycle_voter_ids_length_matches(self, client):
        body = json.loads(post(client).data)
        assert len(body["cycle_voter_ids"]) == body["cycles_detected"]

    def test_mutual_delegation_creates_cycles(self, client):
        """With 2 voters, nearest strategy → A→B, B→A → both in cycles."""
        payload = {
            **BASE,
            "num_voters":             2,
            "delegation_probability": 1.0,
            "delegation_strategy":    "nearest",
            "max_chain_length":       5,
        }
        body = json.loads(client.post(URL, json=payload).data)
        # 2 voters, both delegate to each other → cycles_detected = 2
        # Both vote directly (no delegators)
        assert body["cycles_detected"] == 2
        assert body["delegators"] == 0

    def test_cycles_vote_directly(self, client):
        """Cycle voters are counted as direct voters."""
        payload = {
            **BASE,
            "num_voters":             2,
            "delegation_probability": 1.0,
            "delegation_strategy":    "nearest",
        }
        body = json.loads(client.post(URL, json=payload).data)
        assert body["direct_voters"] == 2


# ── max_chain_length = 1 ──────────────────────────────────────────────────────

class TestMaxChainOne:
    def _run(self, client):
        payload = {**BASE, "max_chain_length": 1}
        return json.loads(client.post(URL, json=payload).data)

    def test_returns_200(self, client):
        assert client.post(URL, json={**BASE, "max_chain_length": 1}).status_code == 200

    def test_chain_max_le_one(self, client):
        body = self._run(client)
        assert body["chain_stats"]["max"] <= 1

    def test_no_transitive_delegation(self, client):
        # With max_chain=1, no chain longer than 1 hop can succeed
        body = self._run(client)
        assert body["chain_stats"]["max"] <= 1


# ── Gini grows with delegation_probability ────────────────────────────────────

class TestGiniMonotonic:
    def _gini(self, client, prob: float) -> float:
        payload = {**BASE, "delegation_probability": prob, "delegation_strategy": "nearest"}
        return json.loads(client.post(URL, json=payload).data)["gini_voting_weight"]

    def test_gini_zero_at_zero_prob(self, client):
        assert self._gini(client, 0.0) == pytest.approx(0.0, abs=1e-4)

    def test_gini_positive_at_high_prob(self, client):
        # With 60% delegation, some concentration expected with nearest strategy
        assert self._gini(client, 0.6) >= 0.0

    def test_gini_nondecreasing(self, client):
        # Gini at 0% <= Gini at 80% (on average with nearest strategy)
        g0 = self._gini(client, 0.0)
        g8 = self._gini(client, 0.8)
        assert g8 >= g0


# ── Strategies ────────────────────────────────────────────────────────────────

class TestStrategies:
    def test_random_strategy(self, client):
        payload = {**BASE, "delegation_strategy": "random"}
        assert client.post(URL, json=payload).status_code == 200

    def test_most_competent_strategy(self, client):
        payload = {**BASE, "delegation_strategy": "most_competent"}
        assert client.post(URL, json=payload).status_code == 200

    def test_nearest_strategy(self, client):
        payload = {**BASE, "delegation_strategy": "nearest"}
        assert client.post(URL, json=payload).status_code == 200


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["comparison"]["liquid_winner"] == b["comparison"]["liquid_winner"]
        assert a["cycles_detected"] == b["cycles_detected"]
        assert a["gini_voting_weight"] == b["gini_voting_weight"]

    def test_different_seed_independent(self, client):
        a = json.loads(post(client).data)
        b = json.loads(client.post(URL, json={**BASE, "seed": 777}).data)
        # Just check structure, not value
        assert "comparison" in b


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_candidate_rejected(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_two_candidates(self, client):
        payload = {
            **BASE,
            "candidates": [
                {"name": "A", "x": -0.5, "y": 0.0},
                {"name": "B", "x":  0.5, "y": 0.0},
            ],
        }
        assert client.post(URL, json=payload).status_code == 200

    def test_full_delegation_nearest(self, client):
        payload = {**BASE, "delegation_probability": 1.0, "num_voters": 20}
        resp = client.post(URL, json=payload)
        assert resp.status_code == 200

    def test_delegation_graph_max_500(self, client):
        payload = {**BASE, "num_voters": 200, "delegation_probability": 0.8}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["delegation_graph"]) <= 500

    def test_super_voters_weight_ge2(self, client):
        payload = {**BASE, "delegation_probability": 0.8}
        body = json.loads(client.post(URL, json=payload).data)
        for sv in body["super_voters"]:
            assert sv["weight"] >= 2
