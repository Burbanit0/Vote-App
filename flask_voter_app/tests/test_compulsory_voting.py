"""
test_compulsory_voting.py — Tests for POST /api/election/compulsory-voting
"""
import json
import pytest

URL = "/api/election/compulsory-voting"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":           200,
    "ideology":             "random",
    "seed":                 42,
    "voluntary_turnout":    0.65,
    "compulsory_turnout":   0.92,
    "reluctant_null_rate":  0.04,
    "reluctant_random_pct": 0.08,
    "method":               "plurality",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestCompulsoryBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("voluntary", "compulsory", "winner_changed",
                  "representation_improvement", "quality_degradation",
                  "pedagogical_note"):
            assert k in body

    def test_voluntary_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("turnout", "winner", "vote_shares", "null_rate", "voter_profile"):
            assert k in body["voluntary"]

    def test_compulsory_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("turnout", "winner", "vote_shares", "null_rate",
                  "reluctant_count", "noise_effect"):
            assert k in body["compulsory"]

    def test_turnout_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 < body["voluntary"]["turnout"] <= 1.0
        assert 0.0 < body["compulsory"]["turnout"] <= 1.0

    def test_compulsory_turnout_gte_voluntary(self, client):
        body = json.loads(post(client).data)
        assert body["compulsory"]["turnout"] >= body["voluntary"]["turnout"] - 0.02

    def test_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for key in ("voluntary", "compulsory"):
            total = sum(body[key]["vote_shares"].values())
            assert abs(total - 1.0) < 0.02

    def test_quality_degradation_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["quality_degradation"] <= 1.0

    def test_representation_improvement_nonneg(self, client):
        body = json.loads(post(client).data)
        assert body["representation_improvement"] >= 0.0


# ── null=0, random=0 → quality_degradation=0 ─────────────────────────────────

class TestNoNoise:
    def _run(self, client):
        payload = {**BASE, "reluctant_null_rate": 0.0, "reluctant_random_pct": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_quality_degradation_zero(self, client):
        body = self._run(client)
        assert body["quality_degradation"] == pytest.approx(0.0)

    def test_compulsory_null_zero(self, client):
        body = self._run(client)
        assert body["compulsory"]["null_rate"] == pytest.approx(0.0)

    def test_reluctant_noise_effect_zero(self, client):
        body = self._run(client)
        assert body["compulsory"]["noise_effect"] == pytest.approx(0.0)


# ── voluntary = compulsory turnout → same results ─────────────────────────────

class TestSameTurnout:
    def _run(self, client):
        payload = {**BASE, "voluntary_turnout": 0.70, "compulsory_turnout": 0.70}
        return json.loads(client.post(URL, json=payload).data)

    def test_no_reluctant_voters(self, client):
        body = self._run(client)
        assert body["compulsory"]["reluctant_count"] == 0

    def test_same_winner(self, client):
        body = self._run(client)
        assert body["voluntary"]["winner"] == body["compulsory"]["winner"]

    def test_winner_not_changed(self, client):
        body = self._run(client)
        assert body["winner_changed"] is False

    def test_same_vote_shares(self, client):
        body = self._run(client)
        for c in ("Alice", "Bob", "Carol"):
            assert body["voluntary"]["vote_shares"][c] == pytest.approx(
                body["compulsory"]["vote_shares"][c], abs=0.02
            )


# ── reluctant_random_pct=1.0 → high noise ────────────────────────────────────

class TestFullRandom:
    def _run(self, client):
        payload = {**BASE, "reluctant_random_pct": 1.0, "reluctant_null_rate": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_quality_degradation_positive(self, client):
        body = self._run(client)
        assert body["quality_degradation"] > 0.0

    def test_noise_effect_positive(self, client):
        body = self._run(client)
        assert body["compulsory"]["noise_effect"] > 0.0


# ── quality_degradation > 0 when random_pct > 0 ──────────────────────────────

class TestQualityDegradation:
    def test_zero_when_random_zero(self, client):
        payload = {**BASE, "reluctant_random_pct": 0.0}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["quality_degradation"] == pytest.approx(0.0)

    def test_positive_when_random_nonzero(self, client):
        # Requires compulsory > voluntary so reluctant voters exist
        body = json.loads(post(client).data)
        if body["compulsory"]["reluctant_count"] > 0:
            assert body["quality_degradation"] > 0.0


# ── representation_improvement ───────────────────────────────────────────────

class TestRepresentationImprovement:
    def test_always_nonneg(self, client):
        body = json.loads(post(client).data)
        assert body["representation_improvement"] >= 0.0

    def test_zero_when_same_turnout(self, client):
        payload = {**BASE, "voluntary_turnout": 0.7, "compulsory_turnout": 0.7}
        body = json.loads(client.post(URL, json=payload).data)
        # No new voters → drift unchanged → improvement = 0
        assert body["representation_improvement"] == pytest.approx(0.0, abs=0.01)


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["voluntary"]["winner"] == b["voluntary"]["winner"]
        assert a["quality_degradation"] == b["quality_degradation"]
        assert a["winner_changed"] == b["winner_changed"]


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_candidate_rejected(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_two_candidates(self, client):
        payload = {
            **BASE,
            "candidates": [{"name": "A", "x": -0.5, "y": 0.0},
                           {"name": "B", "x":  0.5, "y": 0.0}],
        }
        assert client.post(URL, json=payload).status_code == 200

    def test_winner_changed_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["winner_changed"], bool)
        assert body["winner_changed"] == (
            body["voluntary"]["winner"] != body["compulsory"]["winner"]
        )
