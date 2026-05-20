"""
test_ballot_complexity.py — Tests for POST /api/election/ballot-complexity
"""
import json
import pytest

URL = "/api/election/ballot-complexity"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":             100,
    "ideology":               "random",
    "seed":                   42,
    "education_level":        0.7,
    "first_time_voter_pct":   0.1,
    "methods_to_compare": [
        "plurality", "approval", "irv", "borda",
        "star_voting", "majority_judgment", "schulze",
    ],
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestBallotBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("results", "candidate_count_curve",
                  "most_inclusive_method", "least_inclusive_method",
                  "pedagogical_note"):
            assert k in body

    def test_results_count(self, client):
        body = json.loads(post(client).data)
        assert len(body["results"]) == len(BASE["methods_to_compare"])

    def test_result_keys(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            for k in ("method", "null_rate", "blank_rate",
                      "effective_voters", "winner", "winner_changed"):
                assert k in r

    def test_null_rates_in_range(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert 0.0 <= r["null_rate"] <= 1.0

    def test_effective_voters_le_num_voters(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert r["effective_voters"] <= 100

    def test_candidate_count_curve_9_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["candidate_count_curve"]) == 9  # n=2..10

    def test_curve_covers_2_to_10(self, client):
        body = json.loads(post(client).data)
        ns = [pt["n_candidates"] for pt in body["candidate_count_curve"]]
        assert ns == list(range(2, 11))


# ── education_level=1, ftv=0 → minimal null rates ────────────────────────────

class TestMinimalNullRates:
    def _run(self, client):
        payload = {**BASE, "education_level": 1.0, "first_time_voter_pct": 0.0}
        return json.loads(client.post(URL, json=payload).data)

    def _run_high(self, client):
        payload = {**BASE, "education_level": 0.0, "first_time_voter_pct": 0.5}
        return json.loads(client.post(URL, json=payload).data)

    def test_lower_null_rate_with_edu1_ftv0(self, client):
        low   = self._run(client)
        high  = self._run_high(client)
        low_nr  = {r["method"]: r["null_rate"] for r in low["results"]}
        high_nr = {r["method"]: r["null_rate"] for r in high["results"]}
        for m in low_nr:
            if m in high_nr:
                assert low_nr[m] < high_nr[m], f"{m}: low_nr not < high_nr"

    def test_null_rates_positive(self, client):
        body = self._run(client)
        for r in body["results"]:
            assert r["null_rate"] > 0.0  # always some irreducible error


# ── plurality < irv < schulze ─────────────────────────────────────────────────

class TestNullRateOrdering:
    def _rates(self, client):
        body = json.loads(post(client).data)
        return {r["method"]: r["null_rate"] for r in body["results"]}

    def test_plurality_less_than_irv(self, client):
        rates = self._rates(client)
        if "plurality" in rates and "irv" in rates:
            assert rates["plurality"] < rates["irv"]

    def test_irv_less_than_schulze(self, client):
        rates = self._rates(client)
        if "irv" in rates and "schulze" in rates:
            assert rates["irv"] < rates["schulze"]

    def test_plurality_less_than_schulze(self, client):
        rates = self._rates(client)
        if "plurality" in rates and "schulze" in rates:
            assert rates["plurality"] < rates["schulze"]

    def test_most_inclusive_is_plurality(self, client):
        body = json.loads(post(client).data)
        # Plurality has the lowest error base (0.01)
        assert body["most_inclusive_method"] == "plurality"

    def test_least_inclusive_is_schulze(self, client):
        body = json.loads(post(client).data)
        # Schulze has the highest error base (0.05) among the default set
        assert body["least_inclusive_method"] == "schulze"


# ── Candidate count curve is monotone increasing ──────────────────────────────

class TestCurveMonotone:
    def test_null_rate_increases_with_candidates(self, client):
        body = json.loads(post(client).data)
        for method in BASE["methods_to_compare"]:
            rates = [
                pt["null_rate_by_method"].get(method, 0)
                for pt in body["candidate_count_curve"]
            ]
            # Each rate should be ≥ previous (monotone non-decreasing)
            for i in range(1, len(rates)):
                assert rates[i] >= rates[i - 1] or abs(rates[i] - rates[i-1]) < 1e-10, \
                    f"{method}: curve not monotone at n={i+2}"


# ── winner_changed detection ──────────────────────────────────────────────────

class TestWinnerChanged:
    def test_winner_changed_is_boolean(self, client):
        body = json.loads(post(client).data)
        for r in body["results"]:
            assert isinstance(r["winner_changed"], bool)

    def test_high_null_rate_may_change_winner(self, client):
        # With very low education and high first-time voter rate,
        # some methods should have high null rates that might flip the winner
        payload = {
            **BASE,
            "education_level":      0.0,
            "first_time_voter_pct": 0.5,
        }
        body = json.loads(client.post(URL, json=payload).data)
        # Just check the structure is valid
        for r in body["results"]:
            assert r["null_rate"] > 0


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["most_inclusive_method"]  == b["most_inclusive_method"]
        assert a["least_inclusive_method"] == b["least_inclusive_method"]
        assert [r["null_rate"] for r in a["results"]] == \
               [r["null_rate"] for r in b["results"]]


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

    def test_single_method(self, client):
        payload = {**BASE, "methods_to_compare": ["plurality"]}
        body = json.loads(client.post(URL, json=payload).data)
        assert len(body["results"]) == 1
        assert body["results"][0]["method"] == "plurality"
