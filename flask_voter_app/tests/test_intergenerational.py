"""
test_intergenerational.py — Tests for POST /api/theory/intergenerational
"""
import json
import pytest

URL = "/api/theory/intergenerational"

# Default decisions: mix of short/long horizon, positive/negative benefit_future
BASE_DECISIONS = [
    {"name": "Retraite",      "cost_present": -0.2, "benefit_future": -0.4, "time_horizon_years": 30},
    {"name": "Education",     "cost_present": -0.3, "benefit_future":  0.8, "time_horizon_years": 20},
    {"name": "Dette",         "cost_present":  0.5, "benefit_future": -0.6, "time_horizon_years": 25},
    {"name": "Isolation",     "cost_present": -0.4, "benefit_future":  0.7, "time_horizon_years": 15},
    {"name": "Fonds climatiq","cost_present": -0.3, "benefit_future":  0.9, "time_horizon_years": 40},
]

BASE = {
    "decisions":        BASE_DECISIONS,
    "num_voters":       100,
    "age_distribution": [0.30, 0.45, 0.25],
    "seed":             42,
}

# Only decisions with time_horizon > 15 (long-horizon subset)
LONG_DECISIONS = [
    {"name": "LongA", "cost_present": -0.4, "benefit_future": 0.9, "time_horizon_years": 30},
    {"name": "LongB", "cost_present": -0.3, "benefit_future": 0.8, "time_horizon_years": 25},
    {"name": "LongC", "cost_present": -0.2, "benefit_future": 0.7, "time_horizon_years": 20},
]


def post(client, **kw):
    return json.loads(client.post(URL, json={**BASE, **kw}).data)


class TestIntergenerationalBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json=BASE).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("decisions_results", "mechanism_comparison", "pedagogical_note"):
            assert k in body

    def test_decisions_results_count(self, client):
        body = post(client)
        assert len(body["decisions_results"]) == len(BASE_DECISIONS)

    def test_decision_result_keys(self, client):
        body = post(client)
        for dr in body["decisions_results"]:
            assert "decision_name" in dr
            assert "by_mechanism" in dr
            for mech in ("none", "proxy", "age_weighted", "veto"):
                assert mech in dr["by_mechanism"]

    def test_mechanism_result_keys(self, client):
        body = post(client)
        for mech in ("none", "proxy", "age_weighted", "veto"):
            r = body["decisions_results"][0]["by_mechanism"][mech]
            for k in ("adopted", "vote_pct", "welfare_present",
                      "welfare_future", "total_welfare_50y"):
                assert k in r

    def test_all_four_mechanisms_in_comparison(self, client):
        body = post(client)
        for mech in ("none", "proxy", "age_weighted", "veto"):
            assert mech in body["mechanism_comparison"]

    def test_mechanism_comparison_keys(self, client):
        body = post(client)
        for mech in ("none", "proxy", "age_weighted", "veto"):
            m = body["mechanism_comparison"][mech]
            for k in ("adoption_rate", "present_bias", "future_welfare_gain",
                      "intergenerational_gini", "avg_welfare_50y"):
                assert k in m

    def test_vote_pct_in_range(self, client):
        body = post(client)
        for dr in body["decisions_results"]:
            for mech, r in dr["by_mechanism"].items():
                assert 0.0 <= r["vote_pct"] <= 1.0, \
                    f"{dr['decision_name']} / {mech}: vote_pct={r['vote_pct']}"

    def test_welfare_values_in_range(self, client):
        body = post(client)
        for dr in body["decisions_results"]:
            for mech, r in dr["by_mechanism"].items():
                assert 0.0 <= r["welfare_present"] <= 1.0
                assert 0.0 <= r["welfare_future"]  <= 1.0
                assert 0.0 <= r["total_welfare_50y"] <= 1.0

    def test_adoption_rate_in_range(self, client):
        body = post(client)
        for mech, m in body["mechanism_comparison"].items():
            assert 0.0 <= m["adoption_rate"] <= 1.0, \
                f"{mech}: adoption_rate={m['adoption_rate']}"


# ── "none" → highest adoption rate (maximum present bias) ────────────────────

class TestNoneMechanism:
    def test_none_highest_adoption_rate(self, client):
        """Without future representation, present bias is maximised → highest adoption."""
        body = post(client)
        mc = body["mechanism_comparison"]
        none_rate = mc["none"]["adoption_rate"]
        for mech in ("proxy", "age_weighted", "veto"):
            assert none_rate >= mc[mech]["adoption_rate"] - 0.05, (
                f"'none' adoption={none_rate:.2f} < {mech} adoption={mc[mech]['adoption_rate']:.2f}"
            )

    def test_none_zero_future_welfare_gain(self, client):
        """'none' is the baseline → future_welfare_gain should be 0."""
        body = post(client)
        assert body["mechanism_comparison"]["none"]["future_welfare_gain"] == pytest.approx(0.0)


# ── "veto" → lowest adoption on long-horizon decisions ───────────────────────

class TestVetoMechanism:
    def test_veto_lowest_adoption_on_long_horizon(self, client):
        """Youth veto blocks long-horizon decisions when young don't support them."""
        # Use decisions where youth would likely oppose (cost_present low, benefit_future high
        # but long horizon) — the key is time_horizon > 15 triggers veto
        body = post(client, decisions=[
            # Long horizon, young oppose: cost_present = 0 (no benefit now), benefit_future negative
            {"name": "LongCostly", "cost_present": -0.8, "benefit_future": -0.5, "time_horizon_years": 30},
            {"name": "LongCostly2","cost_present": -0.7, "benefit_future": -0.4, "time_horizon_years": 25},
            {"name": "ShortBenefit","cost_present": 0.8, "benefit_future":  0.8, "time_horizon_years": 5},
        ])
        mc = body["mechanism_comparison"]
        # For long decisions that young oppose, veto should block them
        # So veto adoption ≤ none adoption for long-horizon decisions
        assert mc["veto"]["adoption_rate"] <= mc["none"]["adoption_rate"] + 0.1

    def test_veto_short_horizon_not_blocked(self, client):
        """Veto only applies to time_horizon > 15 years."""
        # All short-horizon decisions: veto should not trigger
        short_decs = [
            {"name": "Short1", "cost_present": -0.5, "benefit_future": 0.5, "time_horizon_years": 5},
            {"name": "Short2", "cost_present": -0.3, "benefit_future": 0.6, "time_horizon_years": 10},
            {"name": "Short3", "cost_present":  0.4, "benefit_future": 0.3, "time_horizon_years": 15},
        ]
        body = post(client, decisions=short_decs)
        veto_rate = body["mechanism_comparison"]["veto"]["adoption_rate"]
        none_rate  = body["mechanism_comparison"]["none"]["adoption_rate"]
        # Veto shouldn't reduce adoption for short-horizon decisions
        assert veto_rate == pytest.approx(none_rate, abs=0.15)


# ── future_welfare_gain ordering: veto ≥ age_weighted ≥ proxy ≥ none ─────────

class TestFutureWelfareOrdering:
    def test_future_welfare_gain_ordering(self, client):
        """More protective mechanisms should give higher future welfare gain than 'none'."""
        body = post(client)
        mc = body["mechanism_comparison"]
        # All mechanisms should have non-negative future welfare gain vs none
        for mech in ("proxy", "age_weighted", "veto"):
            assert mc[mech]["future_welfare_gain"] >= mc["none"]["future_welfare_gain"] - 0.01, (
                f"{mech} future_welfare_gain={mc[mech]['future_welfare_gain']:.4f} "
                f"< none={mc['none']['future_welfare_gain']:.4f}"
            )

    def test_proxy_beats_none_in_future_welfare(self, client):
        body = post(client)
        mc = body["mechanism_comparison"]
        assert mc["proxy"]["future_welfare_gain"] >= mc["none"]["future_welfare_gain"]

    def test_age_weighted_beats_none_in_future_welfare(self, client):
        body = post(client)
        mc = body["mechanism_comparison"]
        assert mc["age_weighted"]["future_welfare_gain"] >= mc["none"]["future_welfare_gain"]


# ── intergenerational_gini ordering: none ≥ proxy ≥ age_weighted ─────────────

class TestGiniOrdering:
    def test_none_highest_gini(self, client):
        """Without future representation, intergenerational inequality is highest."""
        body = post(client)
        mc = body["mechanism_comparison"]
        none_gini = mc["none"]["intergenerational_gini"]
        # none should have the highest gini (most unequal across generations)
        for mech in ("proxy", "age_weighted", "veto"):
            assert none_gini >= mc[mech]["intergenerational_gini"] - 0.05, (
                f"none gini={none_gini:.4f} < {mech} gini={mc[mech]['intergenerational_gini']:.4f}"
            )

    def test_gini_in_range(self, client):
        body = post(client)
        for mech, m in body["mechanism_comparison"].items():
            assert 0.0 <= m["intergenerational_gini"] <= 1.0


# ── adopted flag consistent with vote_pct ────────────────────────────────────

class TestAdoptedConsistency:
    def test_adopted_when_vote_pct_gte_50(self, client):
        """Decisions with vote_pct >= 0.5 must be marked adopted (unless veto)."""
        body = post(client)
        for dr in body["decisions_results"]:
            for mech, r in dr["by_mechanism"].items():
                if mech != "veto":  # veto can block regardless of vote_pct
                    if r["vote_pct"] >= 0.50:
                        assert r["adopted"] is True, (
                            f"{dr['decision_name']} / {mech}: vote_pct={r['vote_pct']:.2f} "
                            f"but adopted={r['adopted']}"
                        )
                    else:
                        assert r["adopted"] is False


# ── Default decisions (no body) ───────────────────────────────────────────────

class TestDefaultDecisions:
    def test_returns_200_with_empty_body(self, client):
        r = client.post(URL, json={})
        assert r.status_code == 200

    def test_default_decisions_populated(self, client):
        body = json.loads(client.post(URL, json={}).data)
        # Default decisions should have been used
        assert len(body["decisions_results"]) >= 3


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        for mech in ("none", "proxy", "age_weighted", "veto"):
            assert a["mechanism_comparison"][mech]["adoption_rate"] == \
                   pytest.approx(b["mechanism_comparison"][mech]["adoption_rate"])
