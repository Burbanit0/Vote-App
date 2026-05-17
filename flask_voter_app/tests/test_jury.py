"""
test_jury.py — Tests for POST /api/election/jury
"""
import json
import pytest

URL = "/api/election/jury"

BASE = {
    "num_voters":           100,
    "num_options":          2,
    "correct_option_index": 0,
    "voter_competence":     0.70,
    "num_simulations":      100,
    "seed":                 42,
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestJuryBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for key in ("theoretical_accuracy", "methods", "best_method",
                    "worst_method", "voter_competence", "competence_curve",
                    "pedagogical_note", "pedagogical_note_en"):
            assert key in body, f"Missing key: {key}"

    def test_methods_present(self, client):
        body = json.loads(post(client).data)
        for m in ("plurality", "borda", "irv", "approval", "schulze"):
            assert m in body["methods"], f"Missing method: {m}"

    def test_each_method_has_required_keys(self, client):
        body = json.loads(post(client).data)
        for m, md in body["methods"].items():
            for key in ("accuracy", "beats_majority", "beats_theory"):
                assert key in md, f"{m} missing key: {key}"

    def test_accuracy_in_range(self, client):
        body = json.loads(post(client).data)
        for m, md in body["methods"].items():
            assert 0.0 <= md["accuracy"] <= 1.0, f"{m}: accuracy={md['accuracy']}"

    def test_theoretical_accuracy_in_range(self, client):
        body = json.loads(post(client).data)
        assert 0.0 <= body["theoretical_accuracy"] <= 1.0

    def test_competence_curve_has_20_points(self, client):
        body = json.loads(post(client).data)
        assert len(body["competence_curve"]) == 20

    def test_competence_curve_point_keys(self, client):
        body = json.loads(post(client).data)
        for pt in body["competence_curve"]:
            assert "competence" in pt
            assert "theoretical" in pt


# ── Condorcet Jury Theorem properties ────────────────────────────────────────

class TestJuryTheorem:
    def test_competence_1_accuracy_is_1(self, client):
        """Perfect voters → every method is perfect."""
        body = json.loads(post(client, {**BASE, "voter_competence": 1.0}).data)
        for m, md in body["methods"].items():
            assert md["accuracy"] == 1.0, f"{m}: accuracy={md['accuracy']}"

    def test_competence_0_5_accuracy_near_0_5(self, client):
        """Random voters → collective accuracy ≈ 0.5 (within ±15pp for stochastic test)."""
        body = json.loads(post(client, {
            **BASE,
            "voter_competence":  0.50,
            "num_simulations":   200,
        }).data)
        for m, md in body["methods"].items():
            assert 0.35 <= md["accuracy"] <= 0.65, (
                f"{m}: accuracy={md['accuracy']} not near 0.5"
            )

    def test_theoretical_accuracy_above_half_when_competence_above_half(self, client):
        body = json.loads(post(client, {**BASE, "voter_competence": 0.6}).data)
        assert body["theoretical_accuracy"] > 0.5

    def test_theoretical_accuracy_increases_with_competence(self, client):
        low  = json.loads(post(client, {**BASE, "voter_competence": 0.55}).data)
        high = json.loads(post(client, {**BASE, "voter_competence": 0.80}).data)
        assert high["theoretical_accuracy"] > low["theoretical_accuracy"]

    def test_theoretical_accuracy_increases_with_voters(self, client):
        few  = json.loads(post(client, {**BASE, "num_voters":  20}).data)
        many = json.loads(post(client, {**BASE, "num_voters": 200}).data)
        assert many["theoretical_accuracy"] >= few["theoretical_accuracy"]


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestJuryReproducibility:
    def test_same_seed_same_result(self, client):
        r1 = json.loads(post(client).data)
        r2 = json.loads(post(client).data)
        assert r1["best_method"]  == r2["best_method"]
        assert r1["worst_method"] == r2["worst_method"]
        for m in ("plurality", "borda"):
            assert r1["methods"][m]["accuracy"] == r2["methods"][m]["accuracy"]


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestJuryEdgeCases:
    def test_5_options(self, client):
        payload = {**BASE, "num_options": 5, "correct_option_index": 2}
        r = post(client, payload)
        assert r.status_code == 200
        body = json.loads(r.data)
        assert 0.0 <= body["theoretical_accuracy"] <= 1.0

    def test_small_voter_group(self, client):
        payload = {**BASE, "num_voters": 11}
        r = post(client, payload)
        assert r.status_code == 200

    def test_pedagogical_note_not_empty(self, client):
        body = json.loads(post(client).data)
        assert len(body["pedagogical_note"]) > 20
        assert len(body["pedagogical_note_en"]) > 20
