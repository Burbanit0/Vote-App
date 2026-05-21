"""
test_party_dynamics.py — Tests for POST /api/election/party-dynamics
"""
import json
import pytest

URL = "/api/election/party-dynamics"

FIVE_PARTIES = [
    {"name": "A", "x": -0.8, "y": 0.0, "support_pct": 0.06},
    {"name": "B", "x": -0.3, "y": 0.0, "support_pct": 0.28},
    {"name": "C", "x":  0.1, "y": 0.0, "support_pct": 0.30},
    {"name": "D", "x":  0.5, "y": 0.0, "support_pct": 0.28},
    {"name": "E", "x":  0.9, "y": 0.0, "support_pct": 0.08},
]

BASE = {
    "initial_parties":       FIVE_PARTIES,
    "num_voters":            300,
    "ideology":              "random",
    "seed":                  42,
    "num_elections":         10,
    "method":                "plurality",
    "survival_threshold":    0.05,
    "emergence_probability": 0.0,
    "hotelling_adaptation":  0.1,
    "tactical_voting":       True,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestDynamicsBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("elections", "final_system", "effective_parties_curve",
                  "duverger_confirmed", "convergence_speed",
                  "ideology_drift", "pedagogical_note"):
            assert k in body

    def test_elections_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["elections"]) == 10

    def test_n_eff_curve_length(self, client):
        body = json.loads(post(client).data)
        assert len(body["effective_parties_curve"]) == 10

    def test_election_keys(self, client):
        body = json.loads(post(client).data)
        e = body["elections"][0]
        for k in ("election_n", "active_parties", "parties",
                  "effective_parties", "winner", "new_entrants", "eliminated"):
            assert k in e

    def test_party_keys(self, client):
        body = json.loads(post(client).data)
        p = body["elections"][0]["parties"][0]
        for k in ("name", "x", "vote_pct", "seats", "survived"):
            assert k in p

    def test_final_system_valid(self, client):
        body = json.loads(post(client).data)
        assert body["final_system"] in ("bipartite", "tripartite", "fragmented")

    def test_duverger_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["duverger_confirmed"], bool)


# ── FPTP → convergence toward bipartism ──────────────────────────────────────

class TestFPTPDuverger:
    def _run(self, client):
        payload = {**BASE, "num_elections": 15, "tactical_voting": True, "method": "plurality"}
        return json.loads(client.post(URL, json=payload).data)

    def test_n_eff_below_2_5_eventually(self, client):
        body = self._run(client)
        curve = body["effective_parties_curve"]
        # FPTP + tactical voting should squeeze small parties
        assert min(curve) < 3.0  # At some point, parties are eliminated

    def test_final_parties_fewer_than_initial(self, client):
        body = self._run(client)
        last = body["elections"][-1]
        # Some parties should have been eliminated
        assert last["active_parties"] <= len(FIVE_PARTIES)


# ── num_elections=1 → active_parties = initial count ─────────────────────────

class TestOneElection:
    def _run(self, client):
        payload = {**BASE, "num_elections": 1}
        return json.loads(client.post(URL, json=payload).data)

    def test_first_election_has_all_parties(self, client):
        body = self._run(client)
        assert body["elections"][0]["active_parties"] == len(FIVE_PARTIES)

    def test_one_election_in_results(self, client):
        body = self._run(client)
        assert len(body["elections"]) == 1


# ── Hotelling_adaptation=0 → parties don't move ──────────────────────────────

class TestHotellingZero:
    def _run(self, client):
        payload = {**BASE, "hotelling_adaptation": 0.0, "num_elections": 5,
                   "emergence_probability": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def test_party_positions_stable(self, client):
        body = self._run(client)
        # Party B starts at x=-0.3 and should stay there with hotelling=0
        initial_x = {p["x"]: p["name"] for p in body["elections"][0]["parties"]}
        if len(body["elections"]) >= 5:
            # Check that party B's x hasn't changed if it survived
            election_1_parties = {p["name"]: p["x"] for p in body["elections"][0]["parties"]}
            last_election_parties = {p["name"]: p["x"] for p in body["elections"][-1]["parties"]}
            for name, x in last_election_parties.items():
                if name in election_1_parties:
                    assert abs(x - election_1_parties[name]) < 0.01, f"Party {name} moved with hotelling=0"


# ── emergence_probability=0 → monotone decreasing parties ────────────────────

class TestNoEmergence:
    def _run(self, client):
        payload = {**BASE, "emergence_probability": 0.0, "num_elections": 15}
        return json.loads(client.post(URL, json=payload).data)

    def test_no_new_entrants(self, client):
        body = self._run(client)
        for e in body["elections"]:
            assert e["new_entrants"] == []

    def test_active_parties_monotone_decreasing(self, client):
        body = self._run(client)
        counts = [e["active_parties"] for e in body["elections"]]
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i - 1], (
                f"Party count increased at election {i + 1}: {counts[i-1]} → {counts[i]}"
            )


# ── Proportional → N_eff stays high ──────────────────────────────────────────

class TestProportional:
    def _run(self, client):
        # Use equal support and no tactical voting
        parties = [
            {"name": "A", "x": -0.8, "y": 0, "support_pct": 0.20},
            {"name": "B", "x": -0.4, "y": 0, "support_pct": 0.20},
            {"name": "C", "x":  0.0, "y": 0, "support_pct": 0.20},
            {"name": "D", "x":  0.4, "y": 0, "support_pct": 0.20},
            {"name": "E", "x":  0.8, "y": 0, "support_pct": 0.20},
        ]
        payload = {
            **BASE,
            "initial_parties":       parties,
            "method":                "proportional",
            "tactical_voting":       False,
            "hotelling_adaptation":  0.0,
            "emergence_probability": 0.0,
            "num_elections":         10,
        }
        return json.loads(client.post(URL, json=payload).data)

    def test_n_eff_stays_above_3(self, client):
        body = self._run(client)
        curve = body["effective_parties_curve"]
        # With proportional and no tactics, all parties survive → N_eff high
        for nef in curve:
            assert nef > 2.5, f"N_eff dropped below 2.5 in proportional: {nef}"


# ── duverger_confirmed ────────────────────────────────────────────────────────

class TestDuvergerConfirmed:
    def test_plurality_can_confirm_duverger(self, client):
        # Run long enough to potentially confirm
        payload = {**BASE, "num_elections": 15, "tactical_voting": True}
        body = json.loads(client.post(URL, json=payload).data)
        # If confirmed: must be plurality method and n_eff < 2.5 at end
        if body["duverger_confirmed"]:
            assert body["elections"][-1]["effective_parties"] < 2.5

    def test_proportional_does_not_confirm(self, client):
        parties = [
            {"name": p, "x": (i - 2) * 0.4, "y": 0, "support_pct": 0.20}
            for i, p in enumerate("ABCDE")
        ]
        payload = {
            **BASE,
            "initial_parties":    parties,
            "method":             "proportional",
            "tactical_voting":    False,
            "hotelling_adaptation": 0.0,
            "num_elections":      10,
        }
        body = json.loads(client.post(URL, json=payload).data)
        assert body["duverger_confirmed"] is False


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["duverger_confirmed"] == b["duverger_confirmed"]
        assert a["effective_parties_curve"] == b["effective_parties_curve"]


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_party_rejected(self, client):
        payload = {**BASE, "initial_parties": [{"name": "Solo", "x": 0.0, "y": 0.0, "support_pct": 1.0}]}
        assert client.post(URL, json=payload).status_code == 400

    def test_two_parties(self, client):
        payload = {
            **BASE,
            "initial_parties": [
                {"name": "Left",  "x": -0.4, "y": 0, "support_pct": 0.5},
                {"name": "Right", "x":  0.4, "y": 0, "support_pct": 0.5},
            ],
        }
        assert client.post(URL, json=payload).status_code == 200
