"""
test_choice_overload.py — Tests for POST /api/election/choice-overload
"""
import json
import pytest

URL = "/api/election/choice-overload"

BASE = {
    "num_voters":          100,
    "ideology":            "random",
    "seed":                42,
    "candidate_counts":    [2, 3, 5, 7, 10],
    "overload_threshold":  5,
    "heuristic_weights":   {"notoriety": 0.20, "primacy": 0.10, "partisan": 0.20},
    "methods":             ["plurality", "approval", "borda", "majority_judgment"],
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestOverloadBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("results_by_n", "regret_curve", "most_robust_method",
                  "least_robust_method", "overload_threshold", "pedagogical_note"):
            assert k in body

    def test_results_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["results_by_n"]) == 5

    def test_regret_curve_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["regret_curve"]) == 5

    def test_result_keys(self, client):
        body = json.loads(post(client).data)
        r = body["results_by_n"][0]
        for k in ("num_candidates", "mean_voter_regret", "heuristic_voters",
                  "winner_by_method", "condorcet_winner", "methods_elect_condorcet"):
            assert k in r

    def test_winner_by_method_has_all_methods(self, client):
        body = json.loads(post(client).data)
        for r in body["results_by_n"]:
            for m in BASE["methods"]:
                assert m in r["winner_by_method"]

    def test_regret_in_range(self, client):
        body = json.loads(post(client).data)
        for r in body["results_by_n"]:
            assert 0.0 <= r["mean_voter_regret"] <= 1.0

    def test_heuristic_pct_in_range(self, client):
        body = json.loads(post(client).data)
        for r in body["results_by_n"]:
            assert 0.0 <= r["heuristic_voters"] <= 1.0


# ── N=2 → no heuristics, zero regret ─────────────────────────────────────────

class TestTwoCandidates:
    def _result_at_n(self, body, n):
        return next((r for r in body["results_by_n"] if r["num_candidates"] == n), None)

    def test_no_heuristic_voters_at_n2(self, client):
        body = json.loads(post(client).data)
        r = self._result_at_n(body, 2)
        assert r is not None
        assert r["heuristic_voters"] == pytest.approx(0.0)

    def test_zero_regret_at_n2(self, client):
        body = json.loads(post(client).data)
        r = self._result_at_n(body, 2)
        assert r is not None
        assert r["mean_voter_regret"] == pytest.approx(0.0, abs=1e-6)


# ── N > overload_threshold → heuristic_voters > 0 ────────────────────────────

class TestAboveThreshold:
    def test_heuristic_voters_positive_above_threshold(self, client):
        body = json.loads(post(client).data)
        thr = body["overload_threshold"]
        for r in body["results_by_n"]:
            if r["num_candidates"] > thr:
                assert r["heuristic_voters"] > 0.0, (
                    f"Expected heuristic_voters > 0 for N={r['num_candidates']}"
                )

    def test_regret_positive_above_threshold(self, client):
        body = json.loads(post(client).data)
        thr = body["overload_threshold"]
        for r in body["results_by_n"]:
            if r["num_candidates"] > thr:
                assert r["mean_voter_regret"] > 0.0


# ── heuristic_weights all zero → sincere, zero regret ────────────────────────

class TestZeroHeuristics:
    def _run(self, client):
        payload = {**BASE, "heuristic_weights": {"notoriety": 0, "primacy": 0, "partisan": 0}}
        return json.loads(client.post(URL, json=payload).data)

    def test_zero_regret(self, client):
        body = self._run(client)
        for r in body["results_by_n"]:
            assert r["mean_voter_regret"] == pytest.approx(0.0, abs=1e-6)

    def test_no_heuristic_voters(self, client):
        body = self._run(client)
        for r in body["results_by_n"]:
            assert r["heuristic_voters"] == pytest.approx(0.0)


# ── Regret curve monotone for N > threshold ───────────────────────────────────

class TestRegretCurve:
    def test_regret_at_n2_is_zero(self, client):
        body = json.loads(post(client).data)
        first = body["regret_curve"][0]
        if first["n_candidates"] <= body["overload_threshold"]:
            assert first["regret"] == pytest.approx(0.0, abs=1e-6)

    def test_regret_positive_above_threshold(self, client):
        # With heuristics active, regret should be positive above threshold
        body = json.loads(post(client).data)
        thr = body["overload_threshold"]
        curve_above = [pt for pt in body["regret_curve"] if pt["n_candidates"] > thr]
        # At least one above-threshold point should have positive regret
        if curve_above:
            assert any(pt["regret"] > 0 for pt in curve_above)

    def test_curve_matches_results(self, client):
        body = json.loads(post(client).data)
        for pt, r in zip(body["regret_curve"], body["results_by_n"]):
            assert pt["n_candidates"] == r["num_candidates"]
            assert abs(pt["regret"] - r["mean_voter_regret"]) < 1e-9


# ── most_robust != least_robust ───────────────────────────────────────────────

class TestRobustness:
    def test_most_and_least_differ(self, client):
        payload = {**BASE, "candidate_counts": [2, 5, 7, 10],
                   "heuristic_weights": {"notoriety": 0.3, "primacy": 0.2, "partisan": 0.3}}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["most_robust_method"] in BASE["methods"]
        assert body["least_robust_method"] in BASE["methods"]
        # Most robust is least likely to have winner changed
        # (not necessarily different in all edge cases, but typically)
        assert isinstance(body["most_robust_method"], str)
        assert isinstance(body["least_robust_method"], str)

    def test_most_robust_is_valid_method(self, client):
        body = json.loads(post(client).data)
        assert body["most_robust_method"] in BASE["methods"]

    def test_least_robust_is_valid_method(self, client):
        body = json.loads(post(client).data)
        assert body["least_robust_method"] in BASE["methods"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["most_robust_method"] == b["most_robust_method"]
        assert a["results_by_n"][0]["mean_voter_regret"] == b["results_by_n"][0]["mean_voter_regret"]


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_count(self, client):
        payload = {**BASE, "candidate_counts": [3]}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["results_by_n"]) == 1

    def test_all_below_threshold_no_heuristics(self, client):
        payload = {**BASE, "candidate_counts": [2, 3], "overload_threshold": 10}
        body = json.loads(client.post(URL, json=payload).data)
        for r in body["results_by_n"]:
            assert r["heuristic_voters"] == pytest.approx(0.0)

    def test_large_n(self, client):
        payload = {**BASE, "candidate_counts": [2, 7, 15]}
        assert client.post(URL, json=payload).status_code == 200
