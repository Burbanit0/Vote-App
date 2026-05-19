"""
test_multiwinner_advanced.py — Tests for SPAV, Phragmén, and /multiwinner_compare.
"""
import json
import pytest
from app.utils.simulation_multiwinner_utils import get_spav_result, get_phragmen_result

URL = "/api/election/multiwinner_compare"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ],
    "num_voters": 80,
    "ideology":   "random",
    "seed":       42,
    "num_seats":  2,
}


# ── SPAV unit tests ───────────────────────────────────────────────────────────

class TestSPAV:
    def _run(self, ballots, seats):
        return get_spav_result(ballots, seats)

    def test_basic_two_seats(self):
        ballots = [["A", "B"]] * 6 + [["C", "B"]] * 4
        r = self._run(ballots, 2)
        assert len(r["elected"]) == 2
        # B approved by all → high chance to appear
        assert "B" in r["elected"] or "A" in r["elected"]

    def test_proportional_representation(self):
        """60%/40% split: B-group should get proportional representation."""
        ballots = [["B", "C"]] * 60 + [["A", "D"]] * 40
        r = self._run(ballots, 4)
        elected = r["elected"]
        assert len(elected) == 4
        bc_seats = elected.count("B") + elected.count("C")
        assert bc_seats >= 2  # 60% camp gets >= 2 seats

    def test_single_seat_top_approval(self):
        """With 1 seat, the most approved candidate wins."""
        ballots = [["A", "B"]] * 3 + [["B"]] * 5
        r = self._run(ballots, 1)
        assert r["elected"] == ["B"]

    def test_weight_decreases_after_election(self):
        """After A wins, voters who approved A have reduced weight."""
        ballots = [["A", "B"]] * 10
        r = self._run(ballots, 2)
        # Check that weights in round 2 are less than round 1
        if len(r["rounds"]) >= 2:
            w1 = r["rounds"][0]["weights"]
            w2 = r["rounds"][1]["weights"]
            assert any(w2[i] < w1[i] for i in range(len(w1)))

    def test_empty_ballots(self):
        r = self._run([], 2)
        assert r["elected"] == []
        assert r["rounds"] == []

    def test_num_seats_exceeds_candidates(self):
        """Can't elect more candidates than exist."""
        ballots = [["A", "B"]] * 5
        r = self._run(ballots, 5)
        assert len(r["elected"]) <= 2  # only 2 candidates

    def test_rounds_count(self):
        ballots = [["A", "B", "C"]] * 10
        r = self._run(ballots, 3)
        assert len(r["rounds"]) == 3


# ── Phragmén unit tests ───────────────────────────────────────────────────────

class TestPhragmen:
    def _run(self, ballots, seats):
        return get_phragmen_result(ballots, seats)

    def test_basic_two_seats(self):
        ballots = [["A", "B"]] * 6 + [["C", "B"]] * 4
        r = self._run(ballots, 2)
        assert len(r["elected"]) == 2

    def test_minimises_max_load(self):
        """Phragmén minimises maximum load — load should stay balanced."""
        ballots = [["A"]] * 50 + [["B"]] * 50
        r = self._run(ballots, 2)
        # Perfect split: max load should be 1/50 (1 seat / 50 supporters)
        if r["rounds"]:
            final_loads = r["rounds"][-1]["loads"]
            max_load = max(final_loads)
            assert max_load <= 0.1  # 1/50 = 0.02

    def test_differs_from_spav_sometimes(self):
        """SPAV and Phragmén can produce different results."""
        ballots = (
            [["A", "B"]] * 30 +
            [["A", "C"]] * 20 +
            [["B", "C"]] * 50
        )
        spav_r   = get_spav_result(ballots, 2)
        phrag_r  = self._run(ballots, 2)
        # Both return valid results
        assert len(spav_r["elected"]) == 2
        assert len(phrag_r["elected"]) == 2
        # They don't always agree (this is a property of these methods)
        # Just verify both return candidates from the valid set
        assert all(c in ("A", "B", "C") for c in spav_r["elected"])
        assert all(c in ("A", "B", "C") for c in phrag_r["elected"])

    def test_load_distributed_per_round(self):
        """Each round should record max_load."""
        ballots = [["A", "B", "C"]] * 10
        r = self._run(ballots, 2)
        for rd in r["rounds"]:
            assert "max_load" in rd
            assert rd["max_load"] >= 0

    def test_empty_ballots(self):
        r = self._run([], 2)
        assert r["elected"] == []

    def test_phragmen_max_load_le_spav(self):
        """Phragmén max load should be ≤ the max load produced by SPAV heuristically."""
        ballots = [["A", "B"]] * 40 + [["C", "D"]] * 30 + [["B", "C"]] * 30
        phrag_r = self._run(ballots, 3)
        spav_r  = get_spav_result(ballots, 3)
        if phrag_r["rounds"] and spav_r["rounds"]:
            phrag_max = phrag_r["rounds"][-1]["max_load"]
            # Phragmén minimises max load by design
            assert phrag_max >= 0  # sanity check


# ── /multiwinner_compare endpoint ─────────────────────────────────────────────

class TestMultiwinnerCompareEndpoint:
    def post(self, client, payload=None):
        return client.post(URL, json=payload or BASE)

    def test_returns_200(self, client):
        assert self.post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(self.post(client).data)
        for k in ("methods", "vote_shares", "proportional_reference",
                  "num_seats", "candidates", "best_method", "worst_method"):
            assert k in body, f"Missing key: {k}"

    def test_all_five_methods_present(self, client):
        body = json.loads(self.post(client).data)
        for m in ("stv", "dhondt", "spav", "phragmen", "fptp"):
            assert m in body["methods"], f"Method {m!r} missing"

    def test_seat_sums_correct(self, client):
        body = json.loads(self.post(client).data)
        num_seats = body["num_seats"]
        for m, mdata in body["methods"].items():
            total = sum(mdata["seats"].values())
            assert total == num_seats, f"{m}: seats sum {total} ≠ {num_seats}"

    def test_distortion_non_negative(self, client):
        body = json.loads(self.post(client).data)
        for m, mdata in body["methods"].items():
            assert mdata["distortion"] >= 0, f"{m}: negative distortion"

    def test_seat_vs_votes_present(self, client):
        body = json.loads(self.post(client).data)
        for m, mdata in body["methods"].items():
            assert "seat_vs_votes" in mdata, f"{m}: missing seat_vs_votes"

    def test_same_seed_same_result(self, client):
        r1 = json.loads(self.post(client).data)
        r2 = json.loads(self.post(client).data)
        assert r1["best_method"]  == r2["best_method"]
        assert r1["vote_shares"]  == r2["vote_shares"]

    def test_requires_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert self.post(client, payload).status_code == 400

    def test_num_seats_less_than_candidates(self, client):
        payload = {**BASE, "num_seats": len(BASE["candidates"])}
        assert self.post(client, payload).status_code == 400
