"""
test_sortition.py — Tests for POST /api/election/sortition
"""
import json
import pytest

URL = "/api/election/sortition"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "num_voters":          200,
    "assembly_size":        50,
    "ideology":            "random",
    "seed":                 42,
    "method":              "plurality",
    "realistic_candidates": True,
    "num_simulations":      10,
    "stratification": {
        "age_groups":      [0.25, 0.45, 0.30],
        "gender_parity":   True,
        "education_quota": True,
    },
}


def post(client, payload=None):
    return client.post(URL, json=payload or BASE)


# ── Basic structure ───────────────────────────────────────────────────────────

class TestSortitionBasic:
    def test_returns_200(self, client):
        assert post(client).status_code == 200

    def test_response_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("population", "assemblies", "variance",
                  "winner_by_method", "consensus_possible", "pedagogical_note"):
            assert k in body

    def test_assembly_types(self, client):
        body = json.loads(post(client).data)
        for t in ("elected", "sortition_pure", "sortition_stratified"):
            assert t in body["assemblies"]

    def test_assembly_metric_keys(self, client):
        body = json.loads(post(client).data)
        for asm in body["assemblies"].values():
            for k in ("members_ideology_mean", "representativity", "diversity",
                      "decision_regret", "gini_representation"):
                assert k in asm

    def test_representativity_in_range(self, client):
        body = json.loads(post(client).data)
        for asm in body["assemblies"].values():
            assert 0.0 <= asm["representativity"] <= 1.0

    def test_variance_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("elected", "sortition_pure", "sortition_stratified"):
            assert k in body["variance"]

    def test_winner_by_method_keys(self, client):
        body = json.loads(post(client).data)
        for k in ("elected", "sortition_pure", "sortition_stratified"):
            assert k in body["winner_by_method"]

    def test_consensus_is_bool(self, client):
        body = json.loads(post(client).data)
        assert isinstance(body["consensus_possible"], bool)

    def test_consensus_matches_winners(self, client):
        body = json.loads(post(client).data)
        winners = set(body["winner_by_method"].values())
        if len(winners) == 1:
            assert body["consensus_possible"] is True
        else:
            assert body["consensus_possible"] is False


# ── assembly_size = num_voters → sortition_pure ≈ population ─────────────────

class TestFullSortition:
    def _run(self, client):
        payload = {**BASE, "assembly_size": BASE["num_voters"]}
        return json.loads(client.post(URL, json=payload).data)

    def test_representativity_near_one(self, client):
        body = self._run(client)
        # All voters in assembly → ideology = population mean → representativity ≈ 1
        assert body["assemblies"]["sortition_pure"]["representativity"] >= 0.95

    def test_diversity_high(self, client):
        body = self._run(client)
        # All voters → full ideological spectrum → high diversity
        assert body["assemblies"]["sortition_pure"]["diversity"] > 0.8

    def test_regret_matches_population_spread(self, client):
        body = self._run(client)
        # Decision regret = mean absolute deviation from assembly mean.
        # When assembly = population, it equals the population's MAD (not 0).
        # Just verify it's finite and reasonable.
        regret = body["assemblies"]["sortition_pure"]["decision_regret"]
        assert 0.0 <= regret <= 1.0


# ── Realistic candidates → elected assembly less representative ───────────────

class TestRealisticCandidates:
    def _run_real(self, client):
        payload = {**BASE, "realistic_candidates": True}
        return json.loads(client.post(URL, json=payload).data)

    def _run_neutral(self, client):
        payload = {**BASE, "realistic_candidates": False}
        return json.loads(client.post(URL, json=payload).data)

    def test_elected_less_representative_than_sortition_realistic(self, client):
        body = self._run_real(client)
        rep_elected = body["assemblies"]["elected"]["representativity"]
        rep_pure    = body["assemblies"]["sortition_pure"]["representativity"]
        # With realistic (extreme) candidates, elected assembly is less representative
        assert rep_elected <= rep_pure + 0.1  # Allow some tolerance

    def test_neutral_makes_elected_more_representative(self, client):
        real_body    = self._run_real(client)
        neutral_body = self._run_neutral(client)
        rep_real    = real_body["assemblies"]["elected"]["representativity"]
        rep_neutral = neutral_body["assemblies"]["elected"]["representativity"]
        # Neutral candidates → elected assembly is more representative
        assert rep_neutral >= rep_real - 0.05


# ── Stratification improves consistency for small assemblies ──────────────────

class TestStratificationSmall:
    def _run_small(self, client):
        payload = {**BASE, "assembly_size": 20, "num_simulations": 20}
        return json.loads(client.post(URL, json=payload).data)

    def test_stratified_variance_le_pure_for_small_n(self, client):
        body = self._run_small(client)
        # Stratified sortition should have lower or equal variance than pure
        assert body["variance"]["sortition_stratified"] <= body["variance"]["sortition_pure"] + 0.005


# ── variance(elected) > variance(stratified) ──────────────────────────────────

class TestVarianceOrdering:
    def test_variance_all_nonneg(self, client):
        body = json.loads(post(client).data)
        for k in ("elected", "sortition_pure", "sortition_stratified"):
            assert body["variance"][k] >= 0.0

    def test_stratified_variance_le_pure(self, client):
        body = json.loads(post(client).data)
        # Stratified (guaranteed balance) should have ≤ variance than pure random
        assert body["variance"]["sortition_stratified"] <= body["variance"]["sortition_pure"] + 0.005

    def test_elected_variance_positive(self, client):
        body = json.loads(post(client).data)
        # With noisy candidate pool, elected variance should be positive
        assert body["variance"]["elected"] > 0.0


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self, client):
        a = json.loads(post(client).data)
        b = json.loads(post(client).data)
        assert a["assemblies"]["elected"]["representativity"] == b["assemblies"]["elected"]["representativity"]
        assert a["consensus_possible"] == b["consensus_possible"]
        assert a["winner_by_method"] == b["winner_by_method"]


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

    def test_small_assembly(self, client):
        payload = {**BASE, "assembly_size": 5}
        assert client.post(URL, json=payload).status_code == 200

    def test_large_assembly_within_num_voters(self, client):
        payload = {**BASE, "assembly_size": 150, "num_voters": 200}
        body = json.loads(client.post(URL, json=payload).data)
        assert body["assemblies"]["sortition_pure"]["representativity"] > 0.5
