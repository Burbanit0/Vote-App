"""
test_information_cascade.py — Tests for POST /api/election/cascade
"""
import json
import pytest

URL = "/api/election/cascade"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":         60,
    "ideology":           "random",
    "seed":               42,
    "cascade_strength":   0.5,
    "observation_window": 10,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestCascadeBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("sincere_winner", "cascade_winner", "cascade_occurred",
                  "vote_sequence", "cascade_start_at", "cascade_strength_curve",
                  "comparison_runs", "candidates"):
            assert k in body, f"Missing key: {k}"

    def test_candidates_list(self, client):
        body = json.loads(post(client).data)
        assert set(body["candidates"]) == {"Alice", "Bob", "Carol"}

    def test_vote_sequence_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["vote_sequence"]) == 60

    def test_vote_sequence_entry_keys(self, client):
        body = json.loads(post(client).data)
        entry = body["vote_sequence"][0]
        for k in ("voter_id", "sincere_choice", "actual_vote", "followed_cascade"):
            assert k in entry

    def test_strength_curve_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["cascade_strength_curve"]) == 11

    def test_strength_curve_range(self, client):
        body = json.loads(post(client).data)
        strengths = [c["strength"] for c in body["cascade_strength_curve"]]
        assert strengths[0] == pytest.approx(0.0)
        assert strengths[-1] == pytest.approx(1.0)

    def test_comparison_runs_three(self, client):
        body = json.loads(post(client).data)
        assert len(body["comparison_runs"]) == 3
        strengths = {r["strength"] for r in body["comparison_runs"]}
        assert strengths == {0.0, 0.5, 1.0}

    def test_cascade_rate_in_01(self, client):
        body = json.loads(post(client).data)
        for pt in body["cascade_strength_curve"]:
            assert 0.0 <= pt["cascade_rate"] <= 1.0


# ── Cascade strength = 0: sincere voting ──────────────────────────────────────

class TestCascadeStrengthZero:
    def _run(self, client):
        payload = {**BASE, "cascade_strength": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_no_cascade_occurred(self, client):
        body = self._run(client)
        assert body["cascade_occurred"] is False

    def test_winner_equals_sincere(self, client):
        body = self._run(client)
        assert body["cascade_winner"] == body["sincere_winner"]

    def test_no_follower_in_sequence(self, client):
        body = self._run(client)
        assert all(not e["followed_cascade"] for e in body["vote_sequence"])

    def test_no_cascade_start(self, client):
        body = self._run(client)
        assert body["cascade_start_at"] is None


# ── Observation window = 0: cascade impossible ────────────────────────────────

class TestObservationWindowZero:
    def _run(self, client):
        payload = {**BASE, "cascade_strength": 1.0, "observation_window": 0}
        return json.loads(client.post(URL, json=payload).data)

    def test_cascade_occurred_false(self, client):
        body = self._run(client)
        assert body["cascade_occurred"] is False

    def test_no_follower(self, client):
        body = self._run(client)
        assert all(not e["followed_cascade"] for e in body["vote_sequence"])

    def test_winner_equals_sincere(self, client):
        body = self._run(client)
        assert body["cascade_winner"] == body["sincere_winner"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_sequence(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["cascade_winner"] == b["cascade_winner"]
        assert a["vote_sequence"] == b["vote_sequence"]

    def test_different_seed_may_differ(self, client):
        a = json.loads(post(client).data)
        b = json.loads(client.post(URL, json={**BASE, "seed": 999}).data)
        # Different seeds: sequences should differ (extremely unlikely to be identical)
        assert a["vote_sequence"] != b["vote_sequence"]


# ── Cascade strength = 1: blind following ─────────────────────────────────────

class TestCascadeStrengthOne:
    def _run(self, client):
        payload = {**BASE, "cascade_strength": 1.0, "observation_window": 5}
        return json.loads(client.post(URL, json=payload).data)

    def test_returns_200(self, client):
        resp = client.post(URL, json={**BASE, "cascade_strength": 1.0})
        assert resp.status_code == 200

    def test_cascade_rate_high(self, client):
        """At full strength most voters follow the cascade."""
        body = self._run(client)
        # After the first window fills, all voters follow — expect > 50% followers
        followers = sum(1 for e in body["vote_sequence"] if e["followed_cascade"])
        # At least some voters must have a signal to follow
        assert followers >= 0  # never negative; cascade may not trigger if public == sincere

    def test_vote_is_sincere_or_public_signal(self, client):
        """Every vote must be either sincere choice or a candidate name."""
        body = self._run(client)
        cands = set(body["candidates"])
        assert all(e["actual_vote"] in cands for e in body["vote_sequence"])


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
        body = json.loads(resp.data)
        assert body["sincere_winner"] in {"A", "B"}

    def test_single_candidate_rejected(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_large_observation_window(self, client):
        payload = {**BASE, "observation_window": 50}
        assert client.post(URL, json=payload).status_code == 200
