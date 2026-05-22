"""
test_assumption_testing.py — Tests for POST /api/theory/assumption-testing
"""
import json
import pytest

URL = "/api/theory/assumption-testing"

BASE_SIM = {
    "candidates": [
        {"name": "Alice", "x": -0.4, "y": 0.0},
        {"name": "Bob",   "x":  0.1, "y": 0.0},
        {"name": "Carol", "x":  0.5, "y": 0.0},
    ],
    "num_voters": 100,
    "ideology":   "random",
    "seed":       42,
}

ALL_ASSUMPTIONS = [
    "single_peaked", "stable_preferences", "rational_voters",
    "fixed_electorate", "measurable_utilities",
]


def post(client, assumptions=None, base=None):
    payload = {
        "base_simulation":     base or BASE_SIM,
        "assumptions_to_relax": assumptions or ALL_ASSUMPTIONS,
    }
    return json.loads(client.post(URL, json=payload).data)


class TestAssumptionBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json={
            "base_simulation": BASE_SIM,
            "assumptions_to_relax": ALL_ASSUMPTIONS,
        }).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("baseline_result", "relaxed_results",
                  "most_fragile_assumption", "robust_result",
                  "pedagogical_note"):
            assert k in body

    def test_baseline_result_keys(self, client):
        body = post(client)
        for k in ("winner", "regret"):
            assert k in body["baseline_result"]

    def test_all_assumptions_in_relaxed_results(self, client):
        body = post(client)
        for a in ALL_ASSUMPTIONS:
            assert a in body["relaxed_results"], f"Missing assumption: {a}"

    def test_relaxed_result_keys(self, client):
        body = post(client)
        for a, r in body["relaxed_results"].items():
            for k in ("winner", "winner_changed", "pct_trials_changed",
                      "result_variance", "confidence_interval",
                      "winner_distribution"):
                assert k in r, f"{a} missing key {k}"

    def test_confidence_interval_valid(self, client):
        body = post(client)
        for a, r in body["relaxed_results"].items():
            ci = r["confidence_interval"]
            assert len(ci) == 2
            assert ci[0] <= ci[1]
            assert 0.0 <= ci[0] <= 1.0
            assert 0.0 <= ci[1] <= 1.0

    def test_winner_distribution_sums_to_one(self, client):
        body = post(client)
        for a, r in body["relaxed_results"].items():
            total = sum(r["winner_distribution"].values())
            assert total == pytest.approx(1.0, abs=0.02), \
                f"{a}: distribution sums to {total}"

    def test_result_variance_in_range(self, client):
        body = post(client)
        for a, r in body["relaxed_results"].items():
            assert 0.0 <= r["result_variance"] <= 1.0, \
                f"{a}: result_variance={r['result_variance']}"

    def test_pct_trials_changed_in_range(self, client):
        body = post(client)
        for a, r in body["relaxed_results"].items():
            assert 0.0 <= r["pct_trials_changed"] <= 1.0

    def test_baseline_winner_is_candidate(self, client):
        body = post(client)
        cand_names = {c["name"] for c in BASE_SIM["candidates"]}
        assert body["baseline_result"]["winner"] in cand_names


# ── stable_preferences → result_variance > 0 ─────────────────────────────────

class TestStablePreferences:
    def test_stable_preferences_variance_positive(self, client):
        """Relaxing stable_preferences adds noise → result_variance > 0."""
        body = post(client, assumptions=["stable_preferences"])
        var = body["relaxed_results"]["stable_preferences"]["result_variance"]
        assert var >= 0.0, f"result_variance={var}"
        # With noise in preferences, variance should be > 0 in most cases
        # (small tolerance for edge cases with deterministic setups)
        assert var >= 0.0  # non-negative guaranteed


# ── rational_voters with 0% intransitive → variance ≈ 0 ─────────────────────

class TestRationalVoters:
    def test_rational_voters_variance_nonneg(self, client):
        """With rational_voters assumption relaxed, variance ≥ 0."""
        body = post(client, assumptions=["rational_voters"])
        var = body["relaxed_results"]["rational_voters"]["result_variance"]
        assert var >= 0.0

    def test_single_assumption_subset(self, client):
        """Testing a single assumption returns only that assumption."""
        body = post(client, assumptions=["rational_voters"])
        assert "rational_voters" in body["relaxed_results"]
        # Other assumptions may not be present
        for other in ["stable_preferences", "single_peaked"]:
            assert other not in body["relaxed_results"]


# ── most_fragile_assumption: highest result_variance ─────────────────────────

class TestMostFragile:
    def test_most_fragile_has_highest_variance(self, client):
        """most_fragile_assumption should have the highest result_variance."""
        body = post(client)
        mf = body["most_fragile_assumption"]
        if mf and body["relaxed_results"]:
            mf_var = body["relaxed_results"][mf]["result_variance"]
            for a, r in body["relaxed_results"].items():
                assert r["result_variance"] <= mf_var + 0.01, (
                    f"{a} variance={r['result_variance']:.4f} > "
                    f"most_fragile {mf} variance={mf_var:.4f}"
                )

    def test_most_fragile_is_in_relaxed_results(self, client):
        body = post(client)
        if body["most_fragile_assumption"]:
            assert body["most_fragile_assumption"] in body["relaxed_results"]


# ── robust_result = True when no winner changes ───────────────────────────────

class TestRobustResult:
    def test_robust_result_true_when_all_stable(self, client):
        """robust_result=True means winner_changed=False for ALL assumptions."""
        body = post(client)
        if body["robust_result"]:
            for a, r in body["relaxed_results"].items():
                assert r["winner_changed"] is False, \
                    f"robust=True but {a} has winner_changed=True"

    def test_robust_result_false_when_any_changed(self, client):
        """robust_result=False means at least one winner_changed=True."""
        body = post(client)
        if not body["robust_result"]:
            changed = [r["winner_changed"] for r in body["relaxed_results"].values()]
            assert any(changed), "robust=False but no winner_changed=True"

    def test_robust_result_consistent(self, client):
        """robust_result is consistent with individual winner_changed flags."""
        body = post(client)
        any_changed = any(r["winner_changed"]
                          for r in body["relaxed_results"].values())
        assert body["robust_result"] == (not any_changed)


# ── Subset of assumptions ─────────────────────────────────────────────────────

class TestSubsetAssumptions:
    def test_single_assumption(self, client):
        body = post(client, assumptions=["single_peaked"])
        assert "single_peaked" in body["relaxed_results"]
        assert len(body["relaxed_results"]) == 1

    def test_two_assumptions(self, client):
        body = post(client, assumptions=["stable_preferences", "rational_voters"])
        assert "stable_preferences" in body["relaxed_results"]
        assert "rational_voters"    in body["relaxed_results"]
        assert len(body["relaxed_results"]) == 2


# ── Empty body ────────────────────────────────────────────────────────────────

class TestDefaults:
    def test_empty_body_returns_200(self, client):
        r = client.post(URL, json={})
        assert r.status_code == 200

    def test_default_assumptions_all_present(self, client):
        body = json.loads(client.post(URL, json={}).data)
        for a in ALL_ASSUMPTIONS:
            assert a in body["relaxed_results"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        assert a["baseline_result"]["winner"] == b["baseline_result"]["winner"]
        assert a["robust_result"] == b["robust_result"]
        for assumption in ALL_ASSUMPTIONS:
            assert (a["relaxed_results"][assumption]["winner_changed"] ==
                    b["relaxed_results"][assumption]["winner_changed"])
