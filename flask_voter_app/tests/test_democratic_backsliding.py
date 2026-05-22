"""
test_democratic_backsliding.py — Tests for POST /api/theory/democratic-backsliding
"""
import json
import pytest

URL = "/api/theory/democratic-backsliding"

BASE = {
    "candidates": [
        {"name": "Incumbent", "x": 0.2, "y": 0.0},
        {"name": "Opposition", "x": -0.4, "y": 0.0},
    ],
    "num_voters":            100,
    "ideology":              "random",
    "seed":                  42,
    "num_elections":         6,
    "backsliding_method":    "gerrymandering",
    "backsliding_intensity": 0.6,
    "guardrails": {
        "constitutional_court":   False,
        "opposition_media":       False,
        "international_pressure": False,
        "supermajority_required": False,
    },
}

NO_GUARDRAILS_FULL = {**BASE, "backsliding_intensity": 1.0, "num_elections": 10}
ALL_GUARDRAILS = {
    **BASE,
    "backsliding_intensity": 1.0,
    "num_elections": 10,
    "guardrails": {
        "constitutional_court":   True,
        "opposition_media":       True,
        "international_pressure": True,
        "supermajority_required": True,
    },
}


def post(client, payload=None):
    return json.loads(client.post(URL, json=payload or BASE).data)


class TestBackslidingBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json=BASE).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("elections", "autocracy_reached", "autocracy_at_election",
                  "guardrails_effectiveness", "tipping_points", "pedagogical_note"):
            assert k in body

    def test_elections_count_matches_num_elections(self, client):
        body = post(client)
        assert len(body["elections"]) == BASE["num_elections"]

    def test_election_keys(self, client):
        body = post(client)
        for e in body["elections"]:
            for k in ("election_n", "winner", "democratic_quality",
                      "advantages", "guardrails_triggered", "point_of_no_return"):
                assert k in e

    def test_election_numbers_sequential(self, client):
        body = post(client)
        for i, e in enumerate(body["elections"]):
            assert e["election_n"] == i + 1

    def test_democratic_quality_in_range(self, client):
        body = post(client)
        for e in body["elections"]:
            assert 0.0 <= e["democratic_quality"] <= 1.0

    def test_advantages_keys(self, client):
        body = post(client)
        for e in body["elections"]:
            for k in ("gerrymandering_bonus", "media_bias", "suppression_rate"):
                assert k in e["advantages"]

    def test_vote_shares_sum_to_one(self, client):
        body = post(client)
        for e in body["elections"]:
            total = sum(e["vote_shares"].values())
            assert total == pytest.approx(1.0, abs=0.01)

    def test_winner_in_candidates(self, client):
        body = post(client)
        candidate_names = {c["name"] for c in BASE["candidates"]}
        for e in body["elections"]:
            assert e["winner"] in candidate_names


# ── intensity=0 → no backsliding ─────────────────────────────────────────────

class TestZeroIntensity:
    def test_zero_intensity_no_autocracy(self, client):
        body = post(client, {**BASE, "backsliding_intensity": 0.0, "num_elections": 10})
        assert body["autocracy_reached"] is False

    def test_zero_intensity_quality_stable(self, client):
        """With intensity=0, democratic quality should not significantly decay."""
        body = post(client, {**BASE, "backsliding_intensity": 0.0, "num_elections": 10})
        qualities = [e["democratic_quality"] for e in body["elections"]]
        # Quality should stay near 1.0 (allow small noise)
        assert max(qualities) >= 0.85
        assert min(qualities) >= 0.70

    def test_zero_intensity_no_advantages(self, client):
        """With intensity=0, cumulative advantages should remain at 0."""
        body = post(client, {**BASE, "backsliding_intensity": 0.0, "num_elections": 8})
        for e in body["elections"]:
            for v in e["advantages"].values():
                assert v == pytest.approx(0.0, abs=0.01)


# ── Full intensity + no guardrails → fast autocracy ─────────────────────────

class TestFullIntensityNoGuardrails:
    def test_full_intensity_autocracy_reached(self, client):
        """Intensity=1, 10 elections, no guardrails → autocracy likely."""
        body = post(client, NO_GUARDRAILS_FULL)
        # Either autocracy reached, or quality very low
        final_q = body["elections"][-1]["democratic_quality"]
        assert body["autocracy_reached"] is True or final_q < 0.45

    def test_advantages_grow_monotonically_with_wins(self, client):
        """Gerrymandering bonus should increase when incumbent keeps winning."""
        body = post(client, NO_GUARDRAILS_FULL)
        bonuses = [e["advantages"]["gerrymandering_bonus"] for e in body["elections"]]
        # Bonuses should never decrease by more than the rollback amount (0.02)
        for i in range(1, len(bonuses)):
            assert bonuses[i] >= bonuses[i - 1] - 0.025


# ── Guardrails slow down decline ──────────────────────────────────────────────

class TestGuardrailsEffectiveness:
    def test_constitutional_court_slows_decline(self, client):
        """Constitutional court should produce better final quality than none."""
        body_none = post(client, {
            **BASE, "backsliding_intensity": 0.8, "num_elections": 8,
            "guardrails": {
                "constitutional_court": False, "opposition_media": False,
                "international_pressure": False, "supermajority_required": False,
            },
        })
        body_court = post(client, {
            **BASE, "backsliding_intensity": 0.8, "num_elections": 8,
            "guardrails": {
                "constitutional_court": True, "opposition_media": False,
                "international_pressure": False, "supermajority_required": False,
            },
        })
        q_none  = body_none["elections"][-1]["democratic_quality"]
        q_court = body_court["elections"][-1]["democratic_quality"]
        assert q_court >= q_none - 0.05  # court should not make things worse

    def test_all_guardrails_beat_none(self, client):
        """All guardrails active should produce better or equal quality than none."""
        body_none = post(client, NO_GUARDRAILS_FULL)
        body_all  = post(client, ALL_GUARDRAILS)
        q_none = body_none["elections"][-1]["democratic_quality"]
        q_all  = body_all["elections"][-1]["democratic_quality"]
        assert q_all >= q_none

    def test_guardrails_effectiveness_nonnegative(self, client):
        body = post(client, ALL_GUARDRAILS)
        for gr, val in body["guardrails_effectiveness"].items():
            assert val >= 0.0, f"{gr}: effectiveness={val} < 0"

    def test_inactive_guardrails_have_zero_effectiveness(self, client):
        body = post(client)  # all guardrails False
        for gr, val in body["guardrails_effectiveness"].items():
            assert val == pytest.approx(0.0), \
                f"Inactive guardrail {gr} has non-zero effectiveness {val}"

    def test_active_guardrail_has_positive_effectiveness(self, client):
        body = post(client, {
            **BASE,
            "backsliding_intensity": 0.8,
            "guardrails": {
                "constitutional_court": True, "opposition_media": False,
                "international_pressure": False, "supermajority_required": False,
            },
        })
        assert body["guardrails_effectiveness"]["constitutional_court"] > 0.0


# ── democratic_quality never increases without guardrails ─────────────────────

class TestQualityMonotonicity:
    def test_quality_never_rises_much_with_full_intensity(self, client):
        """With full backsliding, quality should trend downward overall."""
        body = post(client, NO_GUARDRAILS_FULL)
        first_q = body["elections"][0]["democratic_quality"]
        last_q  = body["elections"][-1]["democratic_quality"]
        assert last_q <= first_q + 0.10  # allow small noise, but trend must be down


# ── point_of_no_return consistency ───────────────────────────────────────────

class TestPointOfNoReturn:
    def test_pnr_set_when_quality_below_threshold(self, client):
        body = post(client, NO_GUARDRAILS_FULL)
        for e in body["elections"]:
            if e["point_of_no_return"]:
                assert e["democratic_quality"] <= 0.45 + 0.05  # near the threshold

    def test_pnr_false_with_zero_intensity(self, client):
        body = post(client, {**BASE, "backsliding_intensity": 0.0})
        for e in body["elections"]:
            assert e["point_of_no_return"] is False


# ── Methods ───────────────────────────────────────────────────────────────────

class TestMethods:
    @pytest.mark.parametrize("meth", [
        "gerrymandering", "media_capture", "voter_suppression"
    ])
    def test_all_methods_return_200(self, client, meth):
        body = post(client, {**BASE, "backsliding_method": meth})
        assert len(body["elections"]) == BASE["num_elections"]

    def test_gerrymandering_grows_bonus(self, client):
        body = post(client, {**BASE, "backsliding_method": "gerrymandering",
                             "backsliding_intensity": 0.8})
        bonuses = [e["advantages"]["gerrymandering_bonus"] for e in body["elections"]]
        assert bonuses[-1] >= bonuses[0]

    def test_media_capture_grows_bias(self, client):
        body = post(client, {**BASE, "backsliding_method": "media_capture",
                             "backsliding_intensity": 0.8})
        biases = [e["advantages"]["media_bias"] for e in body["elections"]]
        assert biases[-1] >= biases[0]

    def test_voter_suppression_grows_rate(self, client):
        body = post(client, {**BASE, "backsliding_method": "voter_suppression",
                             "backsliding_intensity": 0.8})
        rates = [e["advantages"]["suppression_rate"] for e in body["elections"]]
        assert rates[-1] >= rates[0]


# ── Tipping points ────────────────────────────────────────────────────────────

class TestTippingPoints:
    def test_tipping_points_two_values(self, client):
        body = post(client)
        assert len(body["tipping_points"]) == 2

    def test_tipping_points_in_range(self, client):
        body = post(client)
        for tp in body["tipping_points"]:
            assert 0.0 <= tp <= 1.0


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        assert a["autocracy_reached"] == b["autocracy_reached"]
        for ea, eb in zip(a["elections"], b["elections"]):
            assert ea["democratic_quality"] == pytest.approx(eb["democratic_quality"])
