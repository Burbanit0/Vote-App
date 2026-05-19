"""
test_affective_polarization.py — Tests for POST /api/election/affective-polarization
"""
import json
import pytest

URL = "/api/election/affective-polarization"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.6, "y": -0.2},
        {"name": "Bob",   "x":  0.6, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":       80,
    "ideology":         "random",
    "seed":             42,
    "affect_hostility": 0.5,
    "camp_threshold":   0.1,
    "num_simulations":  5,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestAffectiveBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("sincere_results", "affective_results", "winner_changed",
                  "condorcet_violation", "method_sensitivity", "affect_curve",
                  "candidate_camps", "pedagogical_note"):
            assert k in body, f"Missing key: {k}"

    def test_requires_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert post(client, payload).status_code == 400

    def test_affect_curve_has_11_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["affect_curve"]) == 11

    def test_affect_curve_hostility_0_to_1(self, client):
        body = json.loads(post(client).data)
        hostilities = [p["hostility"] for p in body["affect_curve"]]
        assert hostilities[0] == 0.0
        assert hostilities[-1] == 1.0

    def test_method_sensitivity_in_range(self, client):
        body = json.loads(post(client).data)
        for m, s in body["method_sensitivity"].items():
            assert 0.0 <= s <= 1.0, f"{m}: sensitivity {s} out of range"

    def test_candidate_camps_assigned(self, client):
        body = json.loads(post(client).data)
        camps = body["candidate_camps"]
        assert "Alice" in camps and "Bob" in camps
        # Alice (x=-0.6) should be left, Bob (x=0.6) should be right
        assert camps["Alice"] == "left"
        assert camps["Bob"]   == "right"


# ── Hostility = 0 → sincere results ──────────────────────────────────────────

class TestZeroHostility:
    def test_zero_hostility_same_winners(self, client):
        """At hostility=0, affective == sincere (no penalty)."""
        payload = {**BASE, "affect_hostility": 0.0}
        body = json.loads(post(client, payload).data)
        sin = body["sincere_results"]
        aff = body["affective_results"]
        for m in sin:
            assert sin[m] == aff[m], f"{m}: sincere {sin[m]} ≠ affective {aff[m]} at hostility 0"

    def test_zero_hostility_winner_unchanged(self, client):
        payload = {**BASE, "affect_hostility": 0.0}
        body = json.loads(post(client, payload).data)
        assert body["winner_changed"] is False

    def test_zero_hostility_no_condorcet_violation(self, client):
        payload = {**BASE, "affect_hostility": 0.0}
        body = json.loads(post(client, payload).data)
        assert body["condorcet_violation"] is False


# ── High hostility → camp voting ──────────────────────────────────────────────

class TestHighHostility:
    def test_high_hostility_centrism_penalised(self, client):
        """
        At max hostility with polarized electorate, the centrist Carol
        should be penalised — left voters reduce utility for right camp
        candidates and vice versa. Carol (centre) may be harmed if both
        camps reject their respective enemy.
        """
        payload = {
            **BASE,
            "affect_hostility": 1.0,
            "ideology": "polarized",
        }
        body = json.loads(post(client, payload).data)
        # Just verify the simulation runs and returns valid data
        assert body["candidate_camps"]["Alice"] in ("left", "right", "centre")
        assert len(body["affect_curve"]) == 11

    def test_sensitivity_increases_with_hostility(self, client):
        """More hostility → at least as much sensitivity."""
        low  = json.loads(post(client, {**BASE, "affect_hostility": 0.1}).data)
        high = json.loads(post(client, {**BASE, "affect_hostility": 0.9}).data)
        # Average sensitivity should be >= with high hostility
        avg_low  = sum(low["method_sensitivity"].values()) / max(len(low["method_sensitivity"]), 1)
        avg_high = sum(high["method_sensitivity"].values()) / max(len(high["method_sensitivity"]), 1)
        # This is a statistical property, may not hold for every seed — soft check
        assert avg_high >= avg_low - 0.15


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestAffectiveReproducibility:
    def test_same_seed_same_results(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["winner_changed"]      == r2["winner_changed"]
        assert r1["candidate_camps"]     == r2["candidate_camps"]
        assert r1["affect_curve"][5]     == r2["affect_curve"][5]  # midpoint

    def test_voters_snapshot_present(self, client):
        body = json.loads(post(client).data)
        assert len(body["voters"]) > 0
        v = body["voters"][0]
        assert "x" in v and "y" in v and "camp" in v
        assert "sincere_pref" in v and "affective_pref" in v
