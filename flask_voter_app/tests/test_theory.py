"""
test_theory.py — Tests for /api/theory/arrow and /api/theory/iia-rate
"""
import json
import pytest

ARROW_URL = "/api/theory/arrow"
RATE_URL  = "/api/theory/iia-rate"


def arrow_post(client, method="plurality", **kw):
    return json.loads(client.post(ARROW_URL, json={"method": method, **kw}).data)


def rate_post(client, method="plurality", **kw):
    return json.loads(client.post(RATE_URL, json={"method": method, **kw}).data)


# ── /api/theory/arrow — basic structure ──────────────────────────────────────

class TestArrowBasic:
    def test_returns_200(self, client):
        assert client.post(ARROW_URL, json={"method": "plurality"}).status_code == 200

    def test_response_keys(self, client):
        body = arrow_post(client)
        for k in ("method", "violations", "arrow_summary", "tradeoff_type"):
            assert k in body

    def test_violations_has_all_axioms(self, client):
        body = arrow_post(client)
        for ax in ("iia", "pareto", "transitivity", "non_dictatorship"):
            assert ax in body["violations"]

    def test_each_violation_has_violated_field(self, client):
        body = arrow_post(client)
        for ax, v in body["violations"].items():
            assert "violated" in v
            assert isinstance(v["violated"], bool)


# ── Plurality: IIA.violated = True ───────────────────────────────────────────

class TestPluralityIIA:
    def test_iia_violated(self, client):
        body = arrow_post(client, "plurality")
        assert body["violations"]["iia"]["violated"] is True

    def test_iia_counterexample_present(self, client):
        body = arrow_post(client, "plurality")
        ce = body["violations"]["iia"]["counterexample"]
        assert ce is not None

    def test_counterexample_consistent(self, client):
        """without_c winner != with_c winner."""
        body = arrow_post(client, "plurality")
        ce = body["violations"]["iia"]["counterexample"]
        assert ce["without_c"] != ce["with_c"], (
            f"Counterexample not convincing: both without_c and with_c are '{ce['without_c']}'"
        )

    def test_iia_profile_has_rows(self, client):
        body = arrow_post(client, "plurality")
        profile = body["violations"]["iia"]["counterexample"]["profile"]
        assert len(profile) > 0
        for row in profile:
            assert isinstance(row, list)
            assert len(row) >= 2


# ── Schulze: IIA.violated = True ─────────────────────────────────────────────

class TestSchulzeIIA:
    def test_iia_violated(self, client):
        body = arrow_post(client, "schulze")
        assert body["violations"]["iia"]["violated"] is True


# ── Borda: Pareto.violated = False ───────────────────────────────────────────

class TestBordaPareto:
    def test_pareto_satisfied(self, client):
        body = arrow_post(client, "borda")
        assert body["violations"]["pareto"]["violated"] is False


# ── Condorcet: Transitivity.violated = True ──────────────────────────────────

class TestCondorcetTransitivity:
    def test_transitivity_violated(self, client):
        body = arrow_post(client, "condorcet")
        assert body["violations"]["transitivity"]["violated"] is True

    def test_cycle_returned(self, client):
        body = arrow_post(client, "condorcet")
        ce = body["violations"]["transitivity"]["counterexample"]
        assert ce is not None
        assert "cycle" in ce
        assert len(ce["cycle"]) >= 3   # at least A > B > C > A (4 elements)


# ── All standard methods: Non-dictatorship satisfied ─────────────────────────

class TestNonDictatorship:
    @pytest.mark.parametrize("method", ["plurality", "borda", "schulze", "irv"])
    def test_non_dictatorship_satisfied(self, client, method):
        body = arrow_post(client, method)
        assert body["violations"]["non_dictatorship"]["violated"] is False


# ── All standard methods: Pareto satisfied ───────────────────────────────────

class TestPareto:
    @pytest.mark.parametrize("method", ["plurality", "borda", "schulze", "irv", "approval"])
    def test_pareto_satisfied(self, client, method):
        body = arrow_post(client, method)
        assert body["violations"]["pareto"]["violated"] is False


# ── tradeoff_type classification ─────────────────────────────────────────────

class TestTradeoffType:
    def test_plurality_is_majority(self, client):
        body = arrow_post(client, "plurality")
        assert body["tradeoff_type"] == "majority_focus"

    def test_borda_is_utility(self, client):
        body = arrow_post(client, "borda")
        assert body["tradeoff_type"] == "utility_focus"

    def test_schulze_is_condorcet(self, client):
        body = arrow_post(client, "schulze")
        assert body["tradeoff_type"] == "condorcet_focus"


# ── /api/theory/iia-rate ─────────────────────────────────────────────────────

class TestIIARate:
    def test_returns_200(self, client):
        assert client.post(RATE_URL, json={"method": "plurality"}).status_code == 200

    def test_response_keys(self, client):
        body = rate_post(client)
        assert "method" in body
        assert "curve" in body

    def test_curve_starts_at_zero(self, client):
        body = rate_post(client, max_candidates=5)
        first = body["curve"][0]
        assert first["n_candidates"] == 2
        assert first["violation_rate"] == pytest.approx(0.0)

    def test_curve_increases_with_candidates(self, client):
        body = rate_post(client, "plurality", max_candidates=6, num_trials=50)
        rates = [pt["violation_rate"] for pt in body["curve"]]
        # Generally increasing trend (allow small decreases)
        assert rates[-1] >= rates[0]  # last > first

    def test_curve_length(self, client):
        body = rate_post(client, max_candidates=5)
        assert len(body["curve"]) == 4  # n=2,3,4,5

    def test_violation_rates_in_range(self, client):
        body = rate_post(client)
        for pt in body["curve"]:
            assert 0.0 <= pt["violation_rate"] <= 1.0

    def test_reproducibility(self, client):
        a = rate_post(client, "plurality", num_trials=50)
        b = rate_post(client, "plurality", num_trials=50)
        assert a["curve"] == b["curve"]
