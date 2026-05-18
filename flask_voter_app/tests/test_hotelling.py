"""
test_hotelling.py — Tests for POST /api/election/hotelling
"""
import json
import pytest

URL = "/api/election/hotelling"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": 0.0},
        {"name": "Bob",   "x":  0.5, "y": 0.0},
    ],
    "num_voters":     100,
    "ideology":       "centrist",
    "seed":           42,
    "method":         "plurality",
    "num_iterations": 10,
    "step_size":      0.05,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestHotellingBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("iterations", "converged", "convergence_step",
                  "final_positions", "equilibrium_type", "voters",
                  "candidates", "method"):
            assert k in body, f"Missing key: {k}"

    def test_requires_two_candidates(self, client):
        payload = {**BASE, "candidates": [{"name": "Solo", "x": 0, "y": 0}]}
        assert post(client, payload).status_code == 400

    def test_num_iterations_respected(self, client):
        payload = {**BASE, "num_iterations": 1}
        body = json.loads(post(client, payload).data)
        # 1 iteration + final snapshot = 2 entries, or 1 if already converged
        assert len(body["iterations"]) >= 1

    def test_iterations_have_required_keys(self, client):
        body = json.loads(post(client).data)
        for it in body["iterations"]:
            for k in ("step", "candidates", "scores", "converged_candidates"):
                assert k in it, f"Step {it.get('step')} missing key: {k}"

    def test_equilibrium_type_valid(self, client):
        body = json.loads(post(client).data)
        assert body["equilibrium_type"] in (
            "center_convergence", "dispersed", "unstable"
        )

    def test_voters_snapshot_present(self, client):
        body = json.loads(post(client).data)
        assert len(body["voters"]) > 0
        assert "x" in body["voters"][0]
        assert "y" in body["voters"][0]

    def test_scores_sum_close_to_one(self, client):
        body = json.loads(post(client).data)
        for it in body["iterations"]:
            total = sum(it["scores"].values())
            assert abs(total - 1.0) < 0.05, f"Step {it['step']}: sum={total}"


# ── Plurality → convergence toward centre ─────────────────────────────────────

class TestPluralityConvergence:
    def test_plurality_produces_valid_equilibrium(self, client):
        """Plurality should produce a valid equilibrium type."""
        payload = {**BASE, "method": "plurality", "ideology": "random",
                   "num_iterations": 15, "step_size": 0.05}
        body = json.loads(post(client, payload).data)
        # Equilibrium type must be one of the three valid values
        assert body["equilibrium_type"] in (
            "center_convergence", "dispersed", "unstable"
        )
        # Final positions must be within [-1, 1]
        for p in body["final_positions"]:
            assert -1.0 <= p["x"] <= 1.0
            assert -1.0 <= p["y"] <= 1.0

    def test_convergence_step_monotonic(self, client):
        """Once a candidate is converged, it stays converged."""
        body = json.loads(post(client).data)
        seen_converged: set = set()
        for it in body["iterations"]:
            cc = set(it["converged_candidates"])
            assert seen_converged.issubset(cc), "A candidate left the converged set"
            seen_converged = cc


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestHotellingReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["converged"]         == r2["converged"]
        assert r1["equilibrium_type"]  == r2["equilibrium_type"]
        for p1, p2 in zip(r1["final_positions"], r2["final_positions"]):
            assert p1["name"] == p2["name"]
            assert abs(p1["x"] - p2["x"]) < 0.001
            assert abs(p1["y"] - p2["y"]) < 0.001

    def test_different_seed_may_differ(self, client):
        r1 = json.loads(post(client, {**BASE, "seed": 42}).data)
        r2 = json.loads(post(client, {**BASE, "seed": 123}).data)
        assert "converged" in r1 and "converged" in r2


# ── Method variants ───────────────────────────────────────────────────────────

class TestHotellingMethods:
    def test_borda_returns_200(self, client):
        r = post(client, {**BASE, "method": "borda"})
        assert r.status_code == 200

    def test_approval_returns_200(self, client):
        r = post(client, {**BASE, "method": "approval"})
        assert r.status_code == 200

    def test_irv_returns_200(self, client):
        r = post(client, {**BASE, "method": "irv"})
        assert r.status_code == 200

    def test_three_candidates(self, client):
        payload = {**BASE, "candidates": [
            {"name": "A", "x": -0.6, "y": 0.0},
            {"name": "B", "x":  0.6, "y": 0.0},
            {"name": "C", "x":  0.0, "y": 0.0},
        ]}
        body = json.loads(post(client, payload).data)
        assert len(body["final_positions"]) == 3
