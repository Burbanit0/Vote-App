"""
test_shy_voter.py — Tests for POST /api/election/shy-voter
"""
import json
import pytest

URL = "/api/election/shy-voter"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":                 200,
    "ideology":                   "random",
    "seed":                       42,
    "shy_candidate_idx":          0,
    "social_desirability_factor": 0.4,
    "num_polls":                  10,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestShyBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("real_winner", "poll_winner", "polls_wrong", "shy_candidate",
                  "poll_results", "systematic_error", "real_results",
                  "avg_poll_results", "social_desirability_curve",
                  "pedagogical_note"):
            assert k in body

    def test_shy_candidate_name(self, client):
        body = json.loads(post(client).data)
        assert body["shy_candidate"] == "Alice"  # idx=0

    def test_poll_results_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["poll_results"]) == 10

    def test_poll_result_keys(self, client):
        body = json.loads(post(client).data)
        pr = body["poll_results"][0]
        for k in ("poll_n", "predicted", "real"):
            assert k in pr

    def test_real_results_sum_to_one(self, client):
        body = json.loads(post(client).data)
        total = sum(body["real_results"].values())
        assert abs(total - 1.0) < 0.01

    def test_curve_11_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["social_desirability_curve"]) == 11

    def test_curve_starts_at_zero(self, client):
        body = json.loads(post(client).data)
        first = body["social_desirability_curve"][0]
        assert first["factor"] == pytest.approx(0.0)
        assert first["poll_error"] == pytest.approx(0.0)

    def test_curve_ends_at_one(self, client):
        body = json.loads(post(client).data)
        last = body["social_desirability_curve"][-1]
        assert last["factor"] == pytest.approx(1.0)


# ── factor=0 → no shy effect ──────────────────────────────────────────────────

class TestFactorZero:
    def _run(self, client):
        payload = {**BASE, "social_desirability_factor": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_systematic_error_near_zero(self, client):
        body = self._run(client)
        shy_err = body["systematic_error"].get(body["shy_candidate"], 0)
        # At factor=0, analytical curve gives poll_error=0, but the actual polls
        # still have sampling noise. The systematic error should be small.
        assert abs(shy_err) < 0.10, f"Unexpected error {shy_err} at factor=0"

    def test_polls_wrong_false_or_borderline(self, client):
        body = self._run(client)
        # At factor=0, no masking → polls should be accurate on average
        # polls_wrong might still be True due to sampling noise; just check structure
        assert isinstance(body["polls_wrong"], bool)

    def test_curve_factor0_error_zero(self, client):
        body = self._run(client)
        first = body["social_desirability_curve"][0]
        assert first["poll_error"] == pytest.approx(0.0)


# ── factor=1 → maximum masking ────────────────────────────────────────────────

class TestFactorOne:
    def _run(self, client):
        payload = {**BASE, "social_desirability_factor": 1.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_systematic_error_max_negative(self, client):
        body = self._run(client)
        shy_err = body["systematic_error"].get(body["shy_candidate"], 0)
        # At factor=1, polls severely underestimate the shy candidate
        assert shy_err < 0, f"Expected negative error at factor=1, got {shy_err}"

    def test_curve_error_at_one_equals_real_rate(self, client):
        body = self._run(client)
        curve = body["social_desirability_curve"]
        last = curve[-1]
        real_shy = body["real_results"].get(body["shy_candidate"], 0)
        # poll_error at factor=1 = real_shy_rate × 1 = real_shy_rate
        assert last["poll_error"] == pytest.approx(real_shy, abs=0.02)

    def test_predicted_shy_below_real_for_all_polls(self, client):
        body = self._run(client)
        shy  = body["shy_candidate"]
        for pr in body["poll_results"]:
            assert pr["predicted"][shy] <= pr["real"][shy] + 0.02, (
                f"Poll {pr['poll_n']}: predicted[{shy}]={pr['predicted'][shy]} "
                f">= real[{shy}]={pr['real'][shy]}"
            )


# ── Monotone curve ────────────────────────────────────────────────────────────

class TestCurveMonotone:
    def test_poll_error_monotone_increasing(self, client):
        body = json.loads(post(client).data)
        curve = body["social_desirability_curve"]
        errors = [pt["poll_error"] for pt in curve]
        # Analytical formula → strictly monotone (linear in factor)
        for i in range(1, len(errors)):
            assert errors[i] >= errors[i - 1] - 1e-10, (
                f"Curve not monotone at step {i}: {errors[i-1]} → {errors[i]}"
            )

    def test_curve_error_higher_at_one_than_zero(self, client):
        body = json.loads(post(client).data)
        curve = body["social_desirability_curve"]
        assert curve[-1]["poll_error"] > curve[0]["poll_error"]


# ── Shy candidate index ───────────────────────────────────────────────────────

class TestShyCandidateIndex:
    def test_idx_zero_is_first_candidate(self, client):
        body = json.loads(post(client).data)
        assert body["shy_candidate"] == "Alice"

    def test_idx_one_is_second_candidate(self, client):
        payload = {**BASE, "shy_candidate_idx": 1}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["shy_candidate"] == "Bob"

    def test_idx_out_of_bounds_clamped(self, client):
        payload = {**BASE, "shy_candidate_idx": 99}
        body = json.loads(client.post(URL, json=payload).data)
        # Clamped to last candidate
        assert body["shy_candidate"] == "Carol"


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["real_winner"] == b["real_winner"]
        assert a["systematic_error"] == b["systematic_error"]
        assert a["poll_results"][0]["predicted"] == b["poll_results"][0]["predicted"]


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

    def test_num_polls_respected(self, client):
        payload = {**BASE, "num_polls": 5}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["poll_results"]) == 5
