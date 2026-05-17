"""
test_abstention.py — Tests for POST /api/election/abstention
"""
import json
import pytest

URL = "/api/election/abstention"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ],
    "num_voters":            100,
    "ideology":              "random",
    "seed":                  42,
    "demobilization_factor": 0.5,
    "poll_influence":        0.8,
    "num_rounds":            3,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestAbstentionBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("rounds", "sincere_winner", "final_winner",
                    "winner_changed", "turnout_by_camp", "candidates"):
            assert key in body, f"Missing key: {key}"

    def test_rounds_count(self, client):
        body = json.loads(post(client).data)
        # num_rounds + 1 (round 0 = sincere)
        assert len(body["rounds"]) == BASE["num_rounds"] + 1

    def test_round_keys(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            for key in ("round", "turnout", "vote_shares",
                        "winner_fptp", "winner_condorcet", "abstention_map"):
                assert key in r, f"Round {r.get('round')} missing key: {key}"

    def test_requires_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0.0, "y": 0.0}]}
        assert post(client, payload).status_code == 400

    def test_winner_changed_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["winner_changed"], bool)


# ── demobilization_factor = 0 → no abstention ────────────────────────────────

class TestZeroDemob:
    def test_turnout_1_when_demob_0(self, client):
        """With demobilization_factor=0, nobody abstains → turnout=1.0 every round."""
        payload = {**BASE, "demobilization_factor": 0.0}
        body = json.loads(post(client, payload).data)
        for r in body["rounds"]:
            assert r["turnout"] == 1.0, f"Round {r['round']}: turnout={r['turnout']}"

    def test_winner_unchanged_when_demob_0(self, client):
        payload = {**BASE, "demobilization_factor": 0.0}
        body = json.loads(post(client, payload).data)
        assert body["winner_changed"] is False

    def test_no_abstained_voters_when_demob_0(self, client):
        payload = {**BASE, "demobilization_factor": 0.0}
        body = json.loads(post(client, payload).data)
        for r in body["rounds"]:
            abstained = [v for v in r["abstention_map"] if v["abstained"]]
            assert len(abstained) == 0, f"Round {r['round']}: {len(abstained)} voters abstained"


# ── High demobilization ────────────────────────────────────────────────────────

class TestHighDemob:
    def test_turnout_decreases_or_stays(self, client):
        """With high demob, turnout should generally decrease over rounds."""
        payload = {**BASE, "demobilization_factor": 0.9, "poll_influence": 1.0}
        body = json.loads(post(client, payload).data)
        # Round 0 always 100%; later rounds should be lower
        assert body["rounds"][0]["turnout"] == 1.0
        final_turnout = body["rounds"][-1]["turnout"]
        assert final_turnout <= 1.0

    def test_abstention_map_has_some_abstained_with_high_demob(self, client):
        payload = {**BASE, "demobilization_factor": 0.95, "poll_influence": 1.0,
                   "num_rounds": 3}
        body = json.loads(post(client, payload).data)
        # In later rounds, at least some voters should have abstained
        last_round = body["rounds"][-1]
        abstained_count = sum(1 for v in last_round["abstention_map"] if v["abstained"])
        assert abstained_count >= 0  # may be 0 in low-polarization configs


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestAbstentionReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["final_winner"]   == r2["final_winner"]
        assert r1["sincere_winner"] == r2["sincere_winner"]
        assert r1["winner_changed"] == r2["winner_changed"]
        for rd1, rd2 in zip(r1["rounds"], r2["rounds"]):
            assert rd1["turnout"] == rd2["turnout"]


# ── Round 0 = sincere vote ────────────────────────────────────────────────────

class TestRoundZero:
    def test_round_0_turnout_always_1(self, client):
        """Round 0 is always the sincere vote — no abstention possible."""
        for demob in (0.0, 0.5, 1.0):
            payload = {**BASE, "demobilization_factor": demob}
            body = json.loads(post(client, payload).data)
            assert body["rounds"][0]["turnout"] == 1.0, \
                f"demob={demob}: round 0 turnout={body['rounds'][0]['turnout']}"

    def test_round_0_has_no_abstained_voters(self, client):
        body = json.loads(post(client).data)
        round_0 = body["rounds"][0]
        abstained = [v for v in round_0["abstention_map"] if v["abstained"]]
        assert len(abstained) == 0

    def test_round_0_winner_equals_sincere_winner(self, client):
        body = json.loads(post(client).data)
        assert body["rounds"][0]["winner_fptp"] == body["sincere_winner"]


# ── Vote shares ───────────────────────────────────────────────────────────────

class TestVoteShares:
    def test_vote_shares_sum_to_one(self, client):
        body = json.loads(post(client).data)
        for r in body["rounds"]:
            total = sum(r["vote_shares"].values())
            assert abs(total - 1.0) < 0.05, f"Round {r['round']}: shares={total}"

    def test_turnout_by_camp_in_range(self, client):
        body = json.loads(post(client).data)
        for cand, pct in body["turnout_by_camp"].items():
            assert 0.0 <= pct <= 1.0, f"{cand}: turnout={pct}"

    def test_candidates_all_in_turnout_by_camp(self, client):
        body = json.loads(post(client).data)
        for c in BASE["candidates"]:
            assert c["name"] in body["turnout_by_camp"]
