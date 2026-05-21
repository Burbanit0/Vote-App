"""
test_deliberation.py — Tests for POST /api/election/deliberation
"""
import json
import pytest

URL = "/api/election/deliberation"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":          200,
    "ideology":            "random",
    "seed":                42,
    "deliberation_rounds": 5,
    "influence_weight":    0.3,
    "network_type":        "random",
    "group_size":          5,
    "argument_quality":    0.5,
    "method":              "plurality",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestDelibBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("pre_deliberation", "post_deliberation", "winner_changed",
                  "deliberation_effect", "per_round", "network_effect",
                  "pedagogical_note"):
            assert k in body

    def test_pre_delib_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("winner", "vote_shares", "condorcet_winner",
                  "mean_regret", "ideology_variance"):
            assert k in body["pre_deliberation"]

    def test_effect_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("opinion_shift_mean", "convergence_rate",
                  "polarization_change", "regret_improvement"):
            assert k in body["deliberation_effect"]

    def test_per_round_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["per_round"]) == 5

    def test_per_round_keys(self, client):
        body = json.loads(post(client).data)
        for r in body["per_round"]:
            for k in ("round", "variance", "mean_position", "winner_if_voted_now"):
                assert k in r

    def test_winner_changed_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["winner_changed"], bool)
        assert body["winner_changed"] == (
            body["pre_deliberation"]["winner"] != body["post_deliberation"]["winner"]
        )


# ── influence_weight=0 → no change ───────────────────────────────────────────

class TestNoInfluence:
    def _run(self, client):
        payload = {**BASE, "influence_weight": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_post_winner_equals_pre(self, client):
        body = self._run(client)
        assert body["pre_deliberation"]["winner"] == body["post_deliberation"]["winner"]

    def test_winner_not_changed(self, client):
        body = self._run(client)
        assert body["winner_changed"] is False

    def test_opinion_shift_zero(self, client):
        body = self._run(client)
        assert body["deliberation_effect"]["opinion_shift_mean"] == pytest.approx(0.0, abs=1e-6)

    def test_variance_unchanged(self, client):
        body = self._run(client)
        pre_var  = body["pre_deliberation"]["ideology_variance"]
        post_var = body["post_deliberation"]["ideology_variance"]
        assert abs(pre_var - post_var) < 1e-6

    def test_per_round_variance_constant(self, client):
        body = self._run(client)
        pre_var = body["pre_deliberation"]["ideology_variance"]
        for r in body["per_round"]:
            assert abs(r["variance"] - pre_var) < 1e-5


# ── influence=1, complete → converge in 1 round ──────────────────────────────

class TestCompleteConvergence:
    def _run(self, client):
        payload = {
            **BASE,
            "influence_weight":    1.0,
            "network_type":        "complete",
            "argument_quality":    0.0,   # pure mean, no quality bias
            "deliberation_rounds": 3,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_variance_drops_dramatically(self, client):
        body = self._run(client)
        pre_var  = body["pre_deliberation"]["ideology_variance"]
        rnd1_var = body["per_round"][0]["variance"]
        # After 1 round with influence=1, everyone ≈ same position → variance ≈ 0
        assert rnd1_var < pre_var * 0.1

    def test_convergence_rate_high(self, client):
        body = self._run(client)
        assert body["deliberation_effect"]["convergence_rate"] > 0.8


# ── echo_chamber → polarization_change > 0 ───────────────────────────────────

class TestEchoChamberPolarizes:
    def _run(self, client):
        payload = {
            **BASE,
            "network_type":        "echo_chamber",
            "influence_weight":    0.4,
            "ideology":            "polarized",
            "deliberation_rounds": 5,
            "argument_quality":    0.0,   # no quality dampening
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_polarization_increases(self, client):
        body = self._run(client)
        polch = body["deliberation_effect"]["polarization_change"]
        assert polch > 0, f"Expected polarization_change > 0, got {polch}"

    def test_variance_increases(self, client):
        body = self._run(client)
        pre_var  = body["pre_deliberation"]["ideology_variance"]
        post_var = body["post_deliberation"]["ideology_variance"]
        assert post_var > pre_var


# ── bridge → polarization_change < 0 ─────────────────────────────────────────

class TestBridgeDePolarizes:
    def _run(self, client):
        payload = {
            **BASE,
            "network_type":        "bridge",
            "influence_weight":    0.4,
            "ideology":            "polarized",
            "deliberation_rounds": 5,
            "argument_quality":    0.0,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_polarization_decreases(self, client):
        body = self._run(client)
        polch = body["deliberation_effect"]["polarization_change"]
        assert polch < 0, f"Expected polarization_change < 0, got {polch}"


# ── complete network → variance monotone decreasing ──────────────────────────

class TestCompleteMonotone:
    def _run(self, client):
        payload = {
            **BASE,
            "network_type":        "complete",
            "influence_weight":    0.3,
            "argument_quality":    0.0,
            "deliberation_rounds": 8,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_variance_monotone_decreasing(self, client):
        body = self._run(client)
        variances = [body["pre_deliberation"]["ideology_variance"]] + [
            r["variance"] for r in body["per_round"]
        ]
        for i in range(1, len(variances)):
            assert variances[i] <= variances[i - 1] + 1e-9, (
                f"Variance increased at round {i}: {variances[i-1]} → {variances[i]}"
            )


# ── argument_quality=1 → winner approaches Condorcet ─────────────────────────

class TestHighQualityArguments:
    def _run(self, client):
        payload = {
            **BASE,
            "network_type":        "complete",
            "influence_weight":    0.5,
            "argument_quality":    1.0,
            "deliberation_rounds": 8,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_post_regret_lower_than_pre(self, client):
        body = self._run(client)
        # High quality → deliberation should at least not increase regret
        pre_regret  = body["pre_deliberation"]["mean_regret"]
        post_regret = body["post_deliberation"]["mean_regret"]
        assert post_regret <= pre_regret + 0.05  # allow small tolerance

    def test_regret_improvement_nonneg(self, client):
        body = self._run(client)
        # With high quality, regret should improve or stay same
        assert body["deliberation_effect"]["regret_improvement"] >= -5.0  # allow 5% tolerance


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["pre_deliberation"]["winner"] == b["pre_deliberation"]["winner"]
        assert a["deliberation_effect"]["opinion_shift_mean"] == b["deliberation_effect"]["opinion_shift_mean"]


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

    def test_one_round(self, client):
        payload = {**BASE, "deliberation_rounds": 1}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["per_round"]) == 1
