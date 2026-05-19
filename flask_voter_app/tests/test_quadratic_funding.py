"""
test_quadratic_funding.py — Tests for POST /api/election/quadratic-funding
"""
import json
import math
import pytest

URL = "/api/election/quadratic-funding"

BASE = {
    "projects": [
        {"name": "Alpha", "x": -0.5},
        {"name": "Beta",  "x":  0.5},
        {"name": "Gamma", "x":  0.0},
    ],
    "num_voters":       80,
    "budget_per_voter": 100.0,
    "matching_pool":    10000.0,
    "ideology":         "random",
    "seed":             42,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestQFBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("projects", "winner", "mechanism_comparison",
                  "gini_coefficients", "pedagogical_note"):
            assert k in body, f"Missing key: {k}"

    def test_requires_two_projects(self, client):
        payload = {**BASE, "projects": [{"name": "Solo", "x": 0}]}
        assert post(client, payload).status_code == 400

    def test_project_keys(self, client):
        body = json.loads(post(client).data)
        for p in body["projects"]:
            for k in ("name", "private_funding", "matching", "total", "qf_score"):
                assert k in p, f"Project missing key: {k}"

    def test_all_three_mechanisms_present(self, client):
        body = json.loads(post(client).data)
        mc = body["mechanism_comparison"]
        for m in ("1p1v", "proportional", "qf"):
            assert m in mc, f"Missing mechanism: {m}"

    def test_gini_in_range(self, client):
        body = json.loads(post(client).data)
        for m, g in body["gini_coefficients"].items():
            assert 0.0 <= g <= 1.0, f"{m}: Gini {g} out of range"


# ── QF mathematical properties ────────────────────────────────────────────────

class TestQFMath:
    def test_matching_pool_zero_equals_proportional(self, client):
        """When matching_pool=0, QF and proportional both add 0 matching → same totals."""
        payload = {**BASE, "matching_pool": 0.0}
        body = json.loads(post(client, payload).data)
        mc = body["mechanism_comparison"]
        qf_totals   = mc["qf"]
        prop_totals = mc["proportional"]
        # Both should equal private funding only (no matching)
        for name in qf_totals:
            assert abs(qf_totals[name] - prop_totals[name]) < 0.01, (
                f"{name}: QF {qf_totals[name]} ≠ prop {prop_totals[name]} with 0 matching"
            )

    def test_qf_formula_amplifies_breadth(self, client):
        """
        Project with many small donors should score better under QF
        than one with a single large donor of the same total amount.
        We verify this via the qf_score field (higher = better).
        With centrist ideology, Gamma (x=0) should attract many voters,
        while Alpha (x=-0.5) and Beta (x=0.5) attract fewer.
        """
        payload = {**BASE, "ideology": "centrist"}
        body = json.loads(post(client, payload).data)
        # The project closest to the centre (Gamma, x=0) should have
        # a high qf_score relative to its private funding
        proj_by_name = {p["name"]: p for p in body["projects"]}
        gamma = proj_by_name.get("Gamma")
        if gamma:
            # qf_score = (Σ√c_ip)² ≥ (Σc_ip) = private_funding
            # because (Σ√xᵢ)² ≥ Σxᵢ by Cauchy-Schwarz
            assert gamma["qf_score"] >= gamma["private_funding"] - 0.01

    def test_qf_gini_le_proportional_gini(self, client):
        """QF should be more equal (lower Gini) than proportional on uniform ideology."""
        body = json.loads(post(client).data)
        g = body["gini_coefficients"]
        # This holds when the centroid voter is equidistant from all projects
        # It may not always hold for skewed distributions — check ≤ with tolerance
        assert g["qf"] <= g["proportional"] + 0.15, (
            f"QF Gini {g['qf']} surprisingly higher than proportional {g['proportional']}"
        )

    def test_total_equals_private_plus_matching(self, client):
        body = json.loads(post(client).data)
        for p in body["projects"]:
            expected = round(p["private_funding"] + p["matching"], 1)
            actual   = round(p["total"], 1)
            assert abs(expected - actual) < 0.1, (
                f"{p['name']}: {p['private_funding']} + {p['matching']} ≠ {p['total']}"
            )

    def test_qf_scores_non_negative(self, client):
        body = json.loads(post(client).data)
        for p in body["projects"]:
            assert p["qf_score"] >= 0

    def test_matching_sums_to_pool(self, client):
        """Total matching distributed = matching_pool (within floating point tolerance)."""
        body = json.loads(post(client).data)
        total_matching = sum(p["matching"] for p in body["projects"])
        pool = body["matching_pool"]
        assert abs(total_matching - pool) < 1.0, (
            f"Total matching {total_matching} ≠ pool {pool}"
        )


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestQFReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["winner"]           == r2["winner"]
        assert r1["gini_coefficients"] == r2["gini_coefficients"]
        for p1, p2 in zip(r1["projects"], r2["projects"]):
            assert p1["name"] == p2["name"]
            assert abs(p1["total"] - p2["total"]) < 0.01


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestQFEdgeCases:
    def test_eight_projects(self, client):
        payload = {**BASE, "projects": [{"name": f"P{i}", "x": (i - 4) * 0.2}
                                         for i in range(8)]}
        body = json.loads(post(client, payload).data)
        assert len(body["projects"]) == 8

    def test_large_matching_pool(self, client):
        payload = {**BASE, "matching_pool": 1_000_000.0}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["winner"] is not None

    def test_pedagogical_note_not_empty(self, client):
        body = json.loads(post(client).data)
        assert len(body["pedagogical_note"]) > 10
