"""
test_behavioral_biases.py — Tests for POST /api/election/behavioral-biases
"""
import json
import pytest

URL = "/api/election/behavioral-biases"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":         100,
    "ideology":           "random",
    "seed":               42,
    "expressive_pct":     0.0,
    "bullet_voting_pct":  0.0,
    "primacy_bonus":      0.0,
    "method":             "plurality",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestBiasBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("sincere_winner", "biased_winner", "winner_changed",
                  "vote_breakdown", "method_sensitivity", "pedagogical_note"):
            assert k in body, f"Missing key: {k}"

    def test_vote_breakdown_keys(self, client):
        body = json.loads(post(client).data)
        bd = body["vote_breakdown"]
        for k in ("expressive_voters", "bullet_voters", "primacy_affected",
                  "first_listed", "candidate_order"):
            assert k in bd

    def test_method_sensitivity_has_approval_and_plurality(self, client):
        body = json.loads(post(client).data)
        ms = body["method_sensitivity"]
        assert "plurality" in ms
        assert "approval"  in ms

    def test_candidate_order_has_all_candidates(self, client):
        body = json.loads(post(client).data)
        order = body["vote_breakdown"]["candidate_order"]
        assert set(order) == {"Alice", "Bob", "Carol"}


# ── No biases → sincere result ────────────────────────────────────────────────

class TestNoBiases:
    def test_winner_unchanged(self, client):
        body = json.loads(post(client).data)
        assert body["winner_changed"] is False
        assert body["sincere_winner"] == body["biased_winner"]

    def test_zero_expressive_voters(self, client):
        body = json.loads(post(client).data)
        assert body["vote_breakdown"]["expressive_voters"] == 0

    def test_zero_bullet_voters(self, client):
        body = json.loads(post(client).data)
        assert body["vote_breakdown"]["bullet_voters"] == 0

    def test_zero_primacy_affected(self, client):
        body = json.loads(post(client).data)
        assert body["vote_breakdown"]["primacy_affected"] == 0

    def test_all_methods_sincere_equals_biased(self, client):
        body = json.loads(post(client).data)
        for m, d in body["method_sensitivity"].items():
            assert d["sincere"] == d["biased"], f"{m}: sincere≠biased with no biases"


# ── Bullet voting pct = 1.0 → approval = plurality ───────────────────────────

class TestBulletVotingFull:
    def _run(self, client):
        payload = {**BASE, "bullet_voting_pct": 1.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_approval_equals_plurality(self, client):
        body = self._run(client)
        ms = body["method_sensitivity"]
        # With 100% bullet voters, approval winner must equal plurality winner
        assert ms["approval"]["biased"] == ms["plurality"]["biased"]

    def test_bullet_count_equals_num_voters(self, client):
        body = self._run(client)
        assert body["vote_breakdown"]["bullet_voters"] == 100

    def test_non_approval_methods_unchanged(self, client):
        body = self._run(client)
        ms = body["method_sensitivity"]
        # Bullet voting should NOT change winners for ranked/score methods
        for m in ("borda", "irv", "schulze", "majority_judgment"):
            if m in ms:
                assert ms[m]["sincere"] == ms[m]["biased"], \
                    f"{m} should be bullet-immune"


# ── Bullet voting = 0 → approval sincere ─────────────────────────────────────

class TestBulletVotingNone:
    def test_approval_unchanged(self, client):
        body = json.loads(post(client).data)
        ms = body["method_sensitivity"]
        assert ms["approval"]["sincere"] == ms["approval"]["biased"]


# ── Primacy effect ────────────────────────────────────────────────────────────

class TestPrimacyEffect:
    def test_primacy_affected_count(self, client):
        payload = {**BASE, "primacy_bonus": 0.1}
        body = json.loads(client.post(URL, json=payload).data)
        # 10% of 100 = 10 voters affected
        assert body["vote_breakdown"]["primacy_affected"] == 10

    def test_first_listed_is_first_in_order(self, client):
        payload = {
            **BASE,
            "primacy_bonus":    0.1,
            "candidate_order": ["Carol", "Alice", "Bob"],
        }
        body = json.loads(client.post(URL, json=payload).data)
        assert body["vote_breakdown"]["first_listed"] == "Carol"
        assert body["vote_breakdown"]["candidate_order"][0] == "Carol"

    def test_primacy_zero_no_effect(self, client):
        payload = {**BASE, "primacy_bonus": 0.0}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["vote_breakdown"]["primacy_affected"] == 0


# ── Expressive voting ─────────────────────────────────────────────────────────

class TestExpressiveVoting:
    def test_expressive_count(self, client):
        payload = {**BASE, "expressive_pct": 0.3}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["vote_breakdown"]["expressive_voters"] == 30

    def test_expressive_does_not_change_plurality(self, client):
        # Expressive boosts top-choice utility ×10, ranking unchanged → plurality stable
        payload = {**BASE, "expressive_pct": 1.0}
        body = json.loads(client.post(URL, json=payload).data)
        ms = body["method_sensitivity"]
        assert ms["plurality"]["sincere"] == ms["plurality"]["biased"]

    def test_expressive_may_change_approval(self, client):
        # Not guaranteed but structure must be present
        payload = {**BASE, "expressive_pct": 1.0}
        body = json.loads(client.post(URL, json=payload).data)
        assert "approval" in body["method_sensitivity"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["sincere_winner"] == b["sincere_winner"]
        assert a["biased_winner"]  == b["biased_winner"]

    def test_different_seed(self, client):
        a = json.loads(post(client).data)
        b = json.loads(client.post(URL, json={**BASE, "seed": 7}).data)
        # Different seeds are independent runs — just check structure
        assert "sincere_winner" in b


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_two_candidates(self, client):
        payload = {
            **BASE,
            "candidates": [
                {"name": "A", "x": -0.5, "y": 0.0},
                {"name": "B", "x":  0.5, "y": 0.0},
            ],
        }
        resp = client.post(URL, json=payload)
        assert resp.status_code == 200

    def test_single_candidate_rejected(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_invalid_candidate_order_falls_back(self, client):
        payload = {**BASE, "candidate_order": ["Unknown", "Also_unknown"]}
        body = json.loads(client.post(URL, json=payload).data)
        assert set(body["vote_breakdown"]["candidate_order"]) == {"Alice", "Bob", "Carol"}

    def test_all_biases_combined(self, client):
        payload = {
            **BASE,
            "expressive_pct":    0.2,
            "bullet_voting_pct": 0.2,
            "primacy_bonus":     0.05,
        }
        resp = client.post(URL, json=payload)
        assert resp.status_code == 200

    def test_bullet_immune_methods_listed(self, client):
        body = json.loads(post(client).data)
        immune = body["bullet_immune_methods"]
        assert isinstance(immune, list)
        assert "majority_judgment" in immune
