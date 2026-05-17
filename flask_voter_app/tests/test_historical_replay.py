"""
test_historical_replay.py — Tests for POST /api/election/historical-replay
"""
import json
import pytest

URL = "/api/election/historical-replay"

BASE = {
    "scenario_id": "france2002",
    "overrides":   [],
    "num_days":    10,
    "seed":        42,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestReplayBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("scenario", "candidates", "days", "final"):
            assert key in body, f"Missing key: {key}"

    def test_days_length_equals_num_days_plus_one(self, client):
        body = json.loads(post(client).data)
        # Days 0..num_days inclusive
        assert len(body["days"]) == BASE["num_days"] + 1

    def test_unknown_scenario_returns_400(self, client):
        r = post(client, {**BASE, "scenario_id": "nonexistent"})
        assert r.status_code == 400

    def test_scenario_meta_returned(self, client):
        body = json.loads(post(client).data)
        assert body["scenario"]["id"] == "france2002"
        assert "name" in body["scenario"]
        assert "real_winner" in body["scenario"]


# ── Per-day structure ─────────────────────────────────────────────────────────

class TestReplayDays:
    def test_each_day_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for d in body["days"]:
            for key in ("day", "vote_shares", "winner_fptp",
                        "winner_condorcet", "winner_borda"):
                assert key in d, f"Day {d.get('day')} missing key: {key}"

    def test_day_indices_sequential(self, client):
        body = json.loads(post(client).data)
        assert [d["day"] for d in body["days"]] == list(range(BASE["num_days"] + 1))

    def test_vote_shares_sum_to_one_each_day(self, client):
        body = json.loads(post(client).data)
        for d in body["days"]:
            total = sum(d["vote_shares"].values())
            assert abs(total - 1.0) < 0.05, f"Day {d['day']}: shares={total:.4f}"

    def test_winner_fptp_is_valid_candidate(self, client):
        body = json.loads(post(client).data)
        cand_names = {c["name"] for c in body["candidates"]}
        for d in body["days"]:
            assert d["winner_fptp"] in cand_names


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReplayReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["final"]["winner_fptp"] == r2["final"]["winner_fptp"]
        for d1, d2 in zip(r1["days"], r2["days"]):
            assert d1["winner_fptp"] == d2["winner_fptp"]

    def test_different_seed_may_differ(self, client):
        r1 = json.loads(post(client, {**BASE, "seed": 42}).data)
        r2 = json.loads(post(client, {**BASE, "seed": 999}).data)
        # Both valid responses
        assert r1["final"]["winner_fptp"] is not None
        assert r2["final"]["winner_fptp"] is not None


# ── Override logic ────────────────────────────────────────────────────────────

class TestReplayOverrides:
    def test_jospin_moved_to_centre_may_change_winner(self, client):
        """
        Moving Jospin to the ideological centre should increase his appeal
        and potentially change the FPTP winner vs the baseline.
        We don't assert the specific winner — only that the system runs.
        """
        override_payload = {
            **BASE,
            "overrides": [{"name": "Jospin", "x": 0.0, "y": 0.0}],
        }
        r = post(client, override_payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["final"]["winner_fptp"] is not None
        # Modified flag is set on Jospin
        jospin = next(c for c in body["candidates"] if c["name"] == "Jospin")
        assert jospin["modified"] is True

    def test_unmodified_candidates_not_flagged(self, client):
        override_payload = {
            **BASE,
            "overrides": [{"name": "Jospin", "x": 0.0, "y": 0.0}],
        }
        body = json.loads(post(client, override_payload).data)
        chirac = next(c for c in body["candidates"] if c["name"] == "Chirac")
        assert chirac["modified"] is False

    def test_pedagogical_note_present(self, client):
        body = json.loads(post(client).data)
        assert len(body["final"]["pedagogical_note"]) > 10
        assert len(body["final"]["pedagogical_note_en"]) > 10

    def test_pedagogical_note_mentions_override(self, client):
        override_payload = {
            **BASE,
            "overrides": [{"name": "Jospin", "x": 0.0, "y": 0.0}],
        }
        body = json.loads(post(client, override_payload).data)
        # Note should mention the moved candidate
        assert "Jospin" in body["final"]["pedagogical_note"]

    def test_differs_from_real_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["final"]["differs_from_real"], bool)


# ── All scenarios ─────────────────────────────────────────────────────────────

class TestReplayAllScenarios:
    @pytest.mark.parametrize("sid", ["france2002", "usa1992", "germany2021", "condorcet_cycle"])
    def test_all_scenarios_return_200(self, client, sid):
        payload = {**BASE, "scenario_id": sid}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert len(body["days"]) == BASE["num_days"] + 1
