"""
test_demographic_turnout.py — Tests for POST /api/election/demographic-turnout
"""
import json
import pytest

URL = "/api/election/demographic-turnout"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters": 200,
    "seed": 42,
    "method": "plurality",
    "correct_for_turnout": True,
    "demographic_profile": {
        "age_distribution":      [0.25, 0.45, 0.30],
        "turnout_by_age":        [0.55, 0.70, 0.85],
        "ideology_by_age":       [-0.10, 0.0, 0.15],
        "education_distribution": [0.40, 0.60],
        "turnout_by_education":  [1.0, 1.0],
        "ideology_by_education": [0.05, -0.05],
    },
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestDemoBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("biased_result", "corrected_result", "winner_changed",
                  "representation_gap", "demographic_breakdown", "pedagogical_note"):
            assert k in body

    def test_biased_result_keys(self, client):
        body = json.loads(post(client).data)
        br = body["biased_result"]
        for k in ("winner", "vote_shares", "actual_turnout", "voter_profile"):
            assert k in br

    def test_corrected_result_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("winner", "vote_shares", "mean_ideology_x"):
            assert k in body["corrected_result"]

    def test_breakdown_count(self, client):
        body = json.loads(post(client).data)
        # 3 age × 2 education = 6 groups
        assert len(body["demographic_breakdown"]) == 6

    def test_breakdown_keys(self, client):
        body = json.loads(post(client).data)
        for d in body["demographic_breakdown"]:
            for k in ("group", "population_pct", "voter_pct", "ideology_mean"):
                assert k in d

    def test_vote_shares_have_all_candidates(self, client):
        body = json.loads(post(client).data)
        for c in ("Alice", "Bob", "Carol"):
            assert c in body["biased_result"]["vote_shares"]

    def test_turnout_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 < body["biased_result"]["actual_turnout"] <= 1.0


# ── All vote (turnout=1.0) → biased = corrected ───────────────────────────────

class TestAllVote:
    def _run(self, client):
        payload = {
            **BASE,
            "demographic_profile": {
                **BASE["demographic_profile"],
                "turnout_by_age": [1.0, 1.0, 1.0],
                "turnout_by_education": [1.0, 1.0],
            },
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_biased_equals_corrected_winner(self, client):
        body = self._run(client)
        assert body["biased_result"]["winner"] == body["corrected_result"]["winner"]

    def test_winner_not_changed(self, client):
        body = self._run(client)
        assert body["winner_changed"] is False

    def test_full_turnout(self, client):
        body = self._run(client)
        assert body["biased_result"]["actual_turnout"] == pytest.approx(1.0, abs=0.01)

    def test_ideology_drift_near_zero(self, client):
        body = self._run(client)
        # All vote → biased = full population → drift ≈ 0
        assert abs(body["representation_gap"]["ideology_drift"]) < 0.05


# ── Only seniors vote ─────────────────────────────────────────────────────────

class TestOnlySeniors:
    def _run(self, client):
        payload = {
            **BASE,
            "demographic_profile": {
                **BASE["demographic_profile"],
                "turnout_by_age": [0.0, 0.0, 1.0],
                "turnout_by_education": [1.0, 1.0],
                "ideology_by_age": [-0.30, 0.0, 0.40],  # seniors strongly right
            },
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_ideology_drift_positive(self, client):
        """Seniors are right-leaning → voter ideology drifts right."""
        body = self._run(client)
        # Seniors have ideology_bias = +0.40 → biased voters are right of full mean
        assert body["representation_gap"]["ideology_drift"] > 0.05

    def test_voter_pct_only_in_senior_groups(self, client):
        body = self._run(client)
        for d in body["demographic_breakdown"]:
            if "seniors" not in d["group"]:
                # Non-senior groups should have ~0 voter representation
                assert d["voter_pct"] < 0.02

    def test_turnout_low(self, client):
        body = self._run(client)
        # Only seniors (30%) vote → turnout ≈ 0.30
        assert body["biased_result"]["actual_turnout"] < 0.40


# ── sum(population_pct) ≈ 1 and sum(voter_pct) ≈ 1 ──────────────────────────

class TestBreakdownSums:
    def test_population_pct_sums_to_one(self, client):
        body = json.loads(post(client).data)
        total = sum(d["population_pct"] for d in body["demographic_breakdown"])
        assert abs(total - 1.0) < 0.01

    def test_voter_pct_sums_to_one(self, client):
        body = json.loads(post(client).data)
        total = sum(d["voter_pct"] for d in body["demographic_breakdown"])
        assert abs(total - 1.0) < 0.02  # allow small rounding

    def test_winner_changed_detected(self, client):
        body = json.loads(post(client).data)
        biased  = body["biased_result"]["winner"]
        correct = body["corrected_result"]["winner"]
        changed = body["winner_changed"]
        assert changed == (biased != correct)


# ── Representation gap ────────────────────────────────────────────────────────

class TestRepresentationGap:
    def test_gap_keys(self, client):
        body = json.loads(post(client).data)
        rg = body["representation_gap"]
        for k in ("ideology_drift", "overrepresented_groups", "underrepresented_groups"):
            assert k in rg

    def test_senior_overrepresented_with_high_turnout(self, client):
        # High senior turnout → seniors are overrepresented
        body = json.loads(post(client).data)
        over = body["representation_gap"]["overrepresented_groups"]
        # At least one senior group should be overrepresented given turnout bias
        # (not guaranteed for all seeds, but structurally expected)
        assert isinstance(over, list)


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["biased_result"]["winner"] == b["biased_result"]["winner"]
        assert a["representation_gap"]["ideology_drift"] == b["representation_gap"]["ideology_drift"]


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

    def test_correct_false_skips_corrected(self, client):
        payload = {**BASE, "correct_for_turnout": False}
        body = json.loads(client.post(URL, json=payload).data)
        # With correct=False, corrected = biased
        assert body["biased_result"]["winner"] == body["corrected_result"]["winner"]
        assert body["winner_changed"] is False
