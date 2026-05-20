"""
test_nota.py — Tests for POST /api/election/nota
"""
import json
import pytest

URL = "/api/election/nota"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":      100,
    "ideology":        "random",
    "seed":            42,
    "nota_threshold":  0.3,
    "nota_rule":       "invalidate",
    "method":          "plurality",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestNotaBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("nota_pct", "election_valid", "winner",
                  "nota_curve", "method_comparison", "pedagogical_note"):
            assert k in body

    def test_nota_pct_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["nota_pct"] <= 1.0

    def test_nota_curve_has_20_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["nota_curve"]) == 20

    def test_nota_curve_thresholds(self, client):
        body = json.loads(post(client).data)
        thresholds = [pt["threshold"] for pt in body["nota_curve"]]
        assert thresholds[0] == pytest.approx(0.0)
        assert thresholds[-1] == pytest.approx(0.95)

    def test_method_comparison_has_all_methods(self, client):
        body = json.loads(post(client).data)
        mc = body["method_comparison"]
        for m in ("plurality", "approval", "borda", "irv", "schulze", "majority_judgment"):
            assert m in mc

    def test_method_comparison_keys(self, client):
        body = json.loads(post(client).data)
        for m, entry in body["method_comparison"].items():
            assert "nota_pct" in entry
            assert "winner" in entry
            assert "election_valid" in entry


# ── nota_threshold = 0 → no NOTA voters ──────────────────────────────────────

class TestThresholdZero:
    def _run(self, client):
        return json.loads(client.post(URL, json={**BASE, "nota_threshold": 0.0}).data)

    def test_nota_pct_zero(self, client):
        body = self._run(client)
        assert body["nota_pct"] == pytest.approx(0.0)

    def test_election_valid(self, client):
        body = self._run(client)
        assert body["election_valid"] is True

    def test_winner_not_null(self, client):
        body = self._run(client)
        assert body["winner"] is not None
        assert body["winner"] != "NOTA"

    def test_all_methods_valid(self, client):
        body = self._run(client)
        for m, entry in body["method_comparison"].items():
            assert entry["election_valid"] is True

    def test_curve_first_point_zero(self, client):
        body = self._run(client)
        assert body["nota_curve"][0]["nota_pct"] == pytest.approx(0.0)


# ── nota_threshold = 1 → all voters choose NOTA ──────────────────────────────

class TestThresholdOne:
    def _run(self, client):
        return json.loads(client.post(URL, json={**BASE, "nota_threshold": 1.0}).data)

    def test_nota_pct_near_one(self, client):
        body = self._run(client)
        assert body["nota_pct"] > 0.99

    def test_election_invalid_for_invalidate_rule(self, client):
        body = self._run(client)
        # nota_rule="invalidate" (from BASE) + nota_pct≈1 → invalid
        assert body["election_valid"] is False

    def test_winner_null(self, client):
        body = self._run(client)
        assert body["winner"] is None


# ── nota_rule = "invalidate" + nota > 50% → invalid ─────────────────────────

class TestInvalidateRule:
    def test_high_threshold_invalidates(self, client):
        # Find a threshold where nota_pct > 0.5
        # Use threshold=0.7 which should produce high NOTA rate
        body = json.loads(client.post(URL, json={
            **BASE, "nota_threshold": 0.7, "nota_rule": "invalidate"
        }).data)
        if body["nota_pct"] > 0.5:
            assert body["election_valid"] is False
            assert body["winner"] is None

    def test_low_threshold_valid(self, client):
        body = json.loads(post(client).data)
        # With threshold=0.3, nota_pct should be low → valid
        if body["nota_pct"] <= 0.5:
            assert body["election_valid"] is True


# ── nota_rule = "winner_take_all" ─────────────────────────────────────────────

class TestWinnerTakeAllRule:
    def _run_high(self, client):
        return json.loads(client.post(URL, json={
            **BASE, "nota_threshold": 0.8, "nota_rule": "winner_take_all"
        }).data)

    def test_nota_elected_when_wins(self, client):
        body = self._run_high(client)
        if body["nota_pct"] > 0.5:
            assert body["winner"] == "NOTA"
            assert body["election_valid"] is True


# ── Approval generates less NOTA than Plurality ───────────────────────────────

class TestApprovalMoreInclusive:
    def test_approval_nota_pct_le_plurality(self, client):
        body = json.loads(post(client).data)
        mc = body["method_comparison"]
        # Approval uses a lower effective threshold → fewer NOTA voters
        assert mc["approval"]["nota_pct"] <= mc["plurality"]["nota_pct"]

    def test_approval_nota_strict_less_for_high_threshold(self, client):
        # At a high threshold (0.7), plurality has NOTA voters that approval doesn't
        body = json.loads(client.post(URL, json={**BASE, "nota_threshold": 0.7}).data)
        mc = body["method_comparison"]
        # Approval effective threshold = 0.7 × 0.5 = 0.35 → much fewer NOTA voters
        assert mc["approval"]["nota_pct"] < mc["plurality"]["nota_pct"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["nota_pct"] == b["nota_pct"]
        assert a["election_valid"] == b["election_valid"]
        assert a["winner"] == b["winner"]


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

    def test_all_nota_rules_run(self, client):
        for rule in ("invalidate", "runoff", "winner_take_all"):
            payload = {**BASE, "nota_rule": rule}
            assert client.post(URL, json=payload).status_code == 200
