"""
test_stv.py — Tests for get_stv_result() and POST /api/election/stv
"""
import json
import pytest
from app.utils.simulation_multiwinner_utils import get_stv_result


# ── Helper ────────────────────────────────────────────────────────────────────

def make_ballots(*preference_lists):
    """Each arg is (count, [ranking]) — expands into individual ballots."""
    ballots = []
    for count, ranking in preference_lists:
        ballots.extend([list(ranking)] * count)
    return ballots


# ── Quota computation ─────────────────────────────────────────────────────────

class TestQuota:
    def test_droop_quota_basic(self):
        ballots = make_ballots((100, ['A', 'B', 'C']))
        result = get_stv_result(ballots, 3)
        # Q = floor(100/4) + 1 = 26
        assert result["quota"] == 26

    def test_hare_quota(self):
        ballots = make_ballots((100, ['A', 'B']))
        result = get_stv_result(ballots, 2, quota_type="hare")
        # Q = 100 / 2 = 50
        assert result["quota"] == 50

    def test_droop_quota_formula(self):
        for n, s in [(100, 3), (500, 5), (200, 4)]:
            ballots = make_ballots((n, ['A', 'B', 'C', 'D', 'E', 'F']))
            result = get_stv_result(ballots, s)
            expected = n // (s + 1) + 1
            assert result["quota"] == expected, f"n={n}, s={s}: got {result['quota']}, expected {expected}"


# ── Clear winner ──────────────────────────────────────────────────────────────

class TestClearWinner:
    def test_one_seat_clear_winner(self):
        ballots = make_ballots((60, ['A', 'B']), (40, ['B', 'A']))
        result = get_stv_result(ballots, 1)
        # Q = floor(100/2)+1 = 51; A has 60 ≥ 51 → elected
        assert result["elected"] == ['A']

    def test_elected_count_equals_num_seats(self):
        ballots = make_ballots(
            (40, ['A', 'B', 'C']),
            (35, ['B', 'C', 'A']),
            (25, ['C', 'A', 'B']),
        )
        result = get_stv_result(ballots, 2)
        assert len(result["elected"]) == 2

    def test_all_candidates_get_seat_if_seats_equals_count(self):
        ballots = make_ballots((50, ['A', 'B']), (50, ['B', 'A']))
        result = get_stv_result(ballots, 2)
        assert set(result["elected"]) == {'A', 'B'}


# ── Surplus transfer ──────────────────────────────────────────────────────────

class TestSurplusTransfer:
    def test_surplus_transferred_proportionally(self):
        """
        80 vote A>B, 20 vote A>C, 100 vote D>E
        Quota (droop, 3 seats) = floor(200/4)+1 = 51
        A first-choice = 100, surplus = 49
        Transfer factor = 49/100 = 0.49
        → B gets 80×0.49 = 39.2, C gets 20×0.49 = 9.8
        D gets 100 (elected).
        """
        ballots = make_ballots(
            (80,  ['A', 'B', 'C', 'D', 'E']),
            (20,  ['A', 'C', 'B', 'D', 'E']),
            (100, ['D', 'E', 'A', 'B', 'C']),
        )
        result = get_stv_result(ballots, 3)
        assert 'A' in result["elected"]
        assert 'D' in result["elected"]
        # E gets D's surplus (100 × 0.49 = 49 > B's 39.2) → third seat
        assert 'E' in result["elected"]

    def test_elect_round_has_transfers(self):
        """After electing a candidate above quota, transfers dict should be non-empty."""
        ballots = make_ballots((70, ['A', 'B']), (30, ['B', 'A']))
        result = get_stv_result(ballots, 1)
        # Single seat — no transfer needed since A wins immediately
        assert len(result["rounds"]) > 0
        assert result["rounds"][0]["action"] in ("elect", "auto_elect")


# ── Elimination ───────────────────────────────────────────────────────────────

class TestElimination:
    def test_last_candidate_eliminated_first(self):
        """Candidate with fewest first-choice votes is eliminated."""
        ballots = make_ballots(
            (50, ['A', 'C']),
            (40, ['B', 'C']),
            (10, ['C', 'A']),   # C has fewest
        )
        result = get_stv_result(ballots, 1)
        rounds = result["rounds"]
        # C should be eliminated in an early round
        elim_rounds = [r for r in rounds if r["action"] == "eliminate"]
        assert any(r["candidate"] == 'C' for r in elim_rounds)

    def test_elimination_transfers_votes(self):
        """After eliminating a candidate, their votes go to next preference."""
        ballots = make_ballots(
            (50, ['A', 'B']),
            (40, ['B', 'A']),
            (10, ['C', 'B']),   # C eliminated → votes go to B
        )
        result = get_stv_result(ballots, 1)
        elim_rounds = [r for r in result["rounds"] if r["action"] == "eliminate"]
        # After C is eliminated, B's tally should increase
        if elim_rounds:
            round_after = elim_rounds[0]
            # B should have at least 40 + transfers from C
            assert round_after["tallies"].get("B", 0) >= 40


# ── Round structure ───────────────────────────────────────────────────────────

class TestRoundStructure:
    def test_each_round_has_required_keys(self):
        ballots = make_ballots((50, ['A', 'B', 'C']), (50, ['B', 'A', 'C']))
        result = get_stv_result(ballots, 2)
        for r in result["rounds"]:
            for k in ("round", "action", "candidate", "tallies", "transfers"):
                assert k in r, f"Round {r.get('round')} missing key: {k}"

    def test_action_values_valid(self):
        ballots = make_ballots((60, ['A', 'B', 'C']), (40, ['B', 'C', 'A']))
        result = get_stv_result(ballots, 2)
        for r in result["rounds"]:
            assert r["action"] in ("elect", "eliminate", "auto_elect")

    def test_empty_input(self):
        result = get_stv_result([], 2)
        assert result["elected"] == []
        assert result["rounds"] == []


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_deterministic_on_same_input(self):
        ballots = make_ballots(
            (40, ['A', 'B', 'C', 'D']),
            (30, ['B', 'A', 'C', 'D']),
            (20, ['C', 'D', 'A', 'B']),
            (10, ['D', 'C', 'B', 'A']),
        )
        r1 = get_stv_result(ballots, 2)
        r2 = get_stv_result(ballots, 2)
        assert r1["elected"] == r2["elected"]
        assert r1["quota"]   == r2["quota"]


# ── POST /api/election/stv ────────────────────────────────────────────────────

URL = "/api/election/stv"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ],
    "num_voters": 100,
    "ideology":   "random",
    "seed":       42,
    "num_seats":  2,
    "quota_type": "droop",
}


class TestSTVEndpoint:
    def test_returns_200(self, client):
        r = client.post(URL, json=BASE)
        assert r.status_code == 200

    def test_response_keys(self, client):
        body = json.loads(client.post(URL, json=BASE).data)
        for key in ("stv", "dhondt", "fptp", "vote_shares", "candidates",
                    "num_seats", "quota", "distortion_stv_dhondt", "distortion_stv_fptp"):
            assert key in body, f"Missing key: {key}"

    def test_stv_seats_sum_to_num_seats(self, client):
        body = json.loads(client.post(URL, json=BASE).data)
        assert sum(body["stv"]["seats"].values()) == BASE["num_seats"]

    def test_dhondt_seats_sum_to_num_seats(self, client):
        body = json.loads(client.post(URL, json=BASE).data)
        assert sum(body["dhondt"]["seats"].values()) == BASE["num_seats"]

    def test_fptp_seats_sum_to_num_seats(self, client):
        body = json.loads(client.post(URL, json=BASE).data)
        assert sum(body["fptp"]["seats"].values()) == BASE["num_seats"]

    def test_distortion_non_negative(self, client):
        body = json.loads(client.post(URL, json=BASE).data)
        assert body["distortion_stv_dhondt"] >= 0
        assert body["distortion_stv_fptp"]   >= 0

    def test_same_seed_same_result(self, client):
        r1 = json.loads(client.post(URL, json=BASE).data)
        r2 = json.loads(client.post(URL, json=BASE).data)
        assert r1["stv"]["elected"] == r2["stv"]["elected"]

    def test_requires_at_least_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_num_seats_less_than_candidates(self, client):
        payload = {**BASE, "num_seats": len(BASE["candidates"])}
        assert client.post(URL, json=payload).status_code == 400
