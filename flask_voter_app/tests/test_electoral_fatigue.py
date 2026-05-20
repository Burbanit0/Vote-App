"""
test_electoral_fatigue.py — Tests for POST /api/election/electoral-fatigue
"""
import json
import pytest

URL = "/api/election/electoral-fatigue"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":         200,
    "ideology":           "random",
    "seed":               42,
    "num_elections":      6,
    "fatigue_rate":       0.07,
    "engaged_voter_pct":  0.2,
    "method":             "plurality",
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestFatigueBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("elections", "winner_drift", "winner_changed_at",
                  "ideology_drift", "representation_gap",
                  "full_mean_ideology", "pedagogical_note"):
            assert k in body

    def test_elections_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["elections"]) == 6

    def test_election_keys(self, client):
        body = json.loads(post(client).data)
        e = body["elections"][0]
        for k in ("election_n", "turnout", "winner", "voter_profile", "vote_shares"):
            assert k in e

    def test_voter_profile_keys(self, client):
        body = json.loads(post(client).data)
        vp = body["elections"][0]["voter_profile"]
        assert "mean_ideology_x" in vp
        assert "partisan_pct" in vp

    def test_winner_drift_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["winner_drift"]) == 6

    def test_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for e in body["elections"]:
            total = sum(e["vote_shares"].values())
            assert abs(total - 1.0) < 0.02

    def test_turnout_in_range(self, client):
        body = json.loads(post(client).data)
        for e in body["elections"]:
            assert 0.0 < e["turnout"] <= 1.0


# ── fatigue_rate=0 → constant turnout, stable winner ─────────────────────────

class TestNoFatigue:
    def _run(self, client):
        payload = {**BASE, "fatigue_rate": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_turnout_constant_at_one(self, client):
        body = self._run(client)
        for e in body["elections"]:
            assert e["turnout"] == pytest.approx(1.0, abs=0.01)

    def test_winner_stable(self, client):
        body = self._run(client)
        winners = [e["winner"] for e in body["elections"]]
        assert len(set(winners)) == 1, "Winner should be constant with no fatigue"

    def test_winner_changed_at_null(self, client):
        body = self._run(client)
        assert body["winner_changed_at"] is None

    def test_ideology_drift_zero(self, client):
        body = self._run(client)
        # With no fatigue, same voters vote every election → drift = 0
        assert body["ideology_drift"] == pytest.approx(0.0, abs=0.001)


# ── elections[0].turnout = 1.0 ────────────────────────────────────────────────

class TestFirstElectionFullTurnout:
    def test_first_turnout_is_one(self, client):
        body = json.loads(post(client).data)
        assert body["elections"][0]["turnout"] == pytest.approx(1.0, abs=0.01)

    def test_first_election_n_is_one(self, client):
        body = json.loads(post(client).data)
        assert body["elections"][0]["election_n"] == 1


# ── Turnout monotone decreasing ───────────────────────────────────────────────

class TestTurnoutMonotone:
    def test_turnout_non_increasing(self, client):
        body = json.loads(post(client).data)
        turnouts = [e["turnout"] for e in body["elections"]]
        for i in range(1, len(turnouts)):
            # Allow tiny upward tick due to sampling noise
            assert turnouts[i] <= turnouts[i - 1] + 0.05, (
                f"Turnout increased at election {i+1}: {turnouts[i-1]} → {turnouts[i]}"
            )

    def test_last_turnout_below_first(self, client):
        body = json.loads(post(client).data)
        assert body["elections"][-1]["turnout"] < body["elections"][0]["turnout"]


# ── ideology_drift ────────────────────────────────────────────────────────────

class TestIdeologyDrift:
    def test_zero_fatigue_zero_drift(self, client):
        payload = {**BASE, "fatigue_rate": 0.0}
        body = json.loads(client.post(URL, json=payload).data)
        assert abs(body["ideology_drift"]) < 0.002

    def test_high_fatigue_nonzero_drift(self, client):
        payload = {**BASE, "fatigue_rate": 0.1, "num_elections": 8,
                   "engaged_voter_pct": 0.2}
        body = json.loads(client.post(URL, json=payload).data)
        # With high fatigue, final voters differ from full electorate
        # The drift won't be 0 due to sampling variance of engaged subset
        assert body["ideology_drift"] != pytest.approx(0.0, abs=1e-6)

    def test_representation_gap_present_with_fatigue(self, client):
        body = json.loads(post(client).data)
        # representation_gap = last_mean_ideology - full_mean_ideology
        assert isinstance(body["representation_gap"], float)


# ── winner_changed_at detection ───────────────────────────────────────────────

class TestWinnerChangedAt:
    def test_winner_changed_at_is_null_or_int(self, client):
        body = json.loads(post(client).data)
        wca = body["winner_changed_at"]
        assert wca is None or isinstance(wca, int)

    def test_winner_changed_at_matches_drift(self, client):
        body = json.loads(post(client).data)
        wca = body["winner_changed_at"]
        first_winner = body["winner_drift"][0]
        if wca is not None:
            # Election at wca should have different winner from first
            changed_election = next(e for e in body["elections"] if e["election_n"] == wca)
            assert changed_election["winner"] != first_winner
        else:
            # All winners should equal first winner
            assert all(w == first_winner for w in body["winner_drift"])

    def test_high_fatigue_may_change_winner(self, client):
        # Just check structure is valid
        payload = {**BASE, "fatigue_rate": 0.12, "num_elections": 10}
        body = json.loads(client.post(URL, json=payload).data)
        assert isinstance(body["winner_changed_at"], (int, type(None)))


# ── num_elections parameter ───────────────────────────────────────────────────

class TestNumElections:
    @pytest.mark.parametrize("n", [1, 3, 12])
    def test_elections_count_matches(self, client, n):
        payload = {**BASE, "num_elections": n}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["elections"]) == n

    def test_winner_drift_matches(self, client):
        body = json.loads(post(client).data)
        assert len(body["winner_drift"]) == len(body["elections"])


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["elections"][0]["turnout"] == b["elections"][0]["turnout"]
        assert a["ideology_drift"] == b["ideology_drift"]
        assert a["winner_changed_at"] == b["winner_changed_at"]


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

    def test_max_fatigue_floors_at_engaged_pct(self, client):
        # With fatigue_rate=0.15 and 8 elections, P hits engaged_pct floor early
        payload = {**BASE, "fatigue_rate": 0.15, "num_elections": 8,
                   "engaged_voter_pct": 0.25}
        body = json.loads(client.post(URL, json=payload).data)
        last_turnout = body["elections"][-1]["turnout"]
        # Should be around 25% (the engaged floor), allowing sampling variation
        assert last_turnout >= 0.15
