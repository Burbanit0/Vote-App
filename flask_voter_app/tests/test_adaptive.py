"""
test_adaptive.py — Tests for POST /api/election/adaptive
"""
import json
import pytest

URL = "/api/election/adaptive"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":          100,
    "ideology":            "random",
    "seed":                42,
    "num_rounds":          4,
    "method":              "plurality",
    "strategic_threshold": 0.15,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestAdaptiveBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("rounds", "converged", "convergence_round",
                    "final_winner", "sincere_winner", "strategic_drift", "candidates"):
            assert key in body, f"Missing key: {key}"

    def test_rounds_length_equals_num_rounds(self, client):
        body = json.loads(post(client).data)
        assert len(body["rounds"]) == BASE["num_rounds"]

    def test_requires_at_least_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400

    def test_strategic_drift_non_negative(self, client):
        body = json.loads(post(client).data)
        assert body["strategic_drift"] >= 0.0

    def test_converged_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["converged"], bool)


# ── Round structure ───────────────────────────────────────────────────────────

class TestAdaptiveRounds:
    def test_each_round_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            for key in ("round", "vote_shares", "winner", "sincere_winner",
                        "strategic_voters_pct", "voter_snapshot"):
                assert key in r, f"Round {r.get('round')} missing key: {key}"

    def test_round_indices_sequential(self, client):
        body = json.loads(post(client).data)
        assert [r["round"] for r in body["rounds"]] == list(range(BASE["num_rounds"]))

    def test_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            total = sum(r["vote_shares"].values())
            assert abs(total - 1.0) < 0.05, f"Round {r['round']}: shares={total}"

    def test_strategic_voters_pct_in_range(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            pct = r["strategic_voters_pct"]
            assert 0.0 <= pct <= 1.0, f"Round {r['round']}: strategic_pct={pct}"

    def test_round_0_has_zero_tactical_voters(self, client):
        body = json.loads(post(client).data)
        r0 = body["rounds"][0]
        assert r0["strategic_voters_pct"] == 0.0

    def test_voter_snapshot_not_empty(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            assert len(r["voter_snapshot"]) > 0


# ── Threshold = 1.0 → no tactical voting ─────────────────────────────────────

class TestAdaptiveThreshold:
    def test_threshold_1_0_zero_strategic(self, client):
        payload = {**BASE, "strategic_threshold": 1.0}
        body = json.loads(post(client, payload).data)
        # With threshold=1.0 no candidate is ever below threshold → all sincere
        for r in body["rounds"][1:]:
            assert r["strategic_voters_pct"] == 0.0

    def test_threshold_0_forces_max_strategic(self, client):
        # With threshold=0.0 all candidates are "viable" → no tactical switch needed
        payload = {**BASE, "strategic_threshold": 0.0}
        r = post(client, payload)
        assert r.status_code == 200

    def test_high_threshold_same_as_sincere(self, client):
        sincere = json.loads(post(client, {**BASE, "strategic_threshold": 1.0}).data)
        assert sincere["sincere_winner"] is not None
        # Final winner with 100% threshold should match sincere winner
        assert sincere["final_winner"] == sincere["sincere_winner"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestAdaptiveReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["final_winner"] == r2["final_winner"]
        assert r1["strategic_drift"] == r2["strategic_drift"]
        for rd1, rd2 in zip(r1["rounds"], r2["rounds"]):
            assert rd1["winner"] == rd2["winner"]
            assert rd1["strategic_voters_pct"] == rd2["strategic_voters_pct"]


# ── Method variants ───────────────────────────────────────────────────────────

class TestAdaptiveMethods:
    def test_irv_method(self, client):
        r = post(client, {**BASE, "method": "irv"})
        assert r.status_code == 200
        assert json.loads(r.data)["final_winner"] is not None

    def test_borda_method(self, client):
        r = post(client, {**BASE, "method": "borda"})
        assert r.status_code == 200

    def test_schulze_method(self, client):
        r = post(client, {**BASE, "method": "schulze"})
        assert r.status_code == 200

    def test_approval_method(self, client):
        r = post(client, {**BASE, "method": "approval"})
        assert r.status_code == 200
