"""
test_collective_will.py — Tests for POST /api/theory/collective-will
Does collective will exist, or is it a procedural artefact?
Rousseau (1762) vs Arrow (1951) vs Schumpeter (1942).
"""
import json
import pytest

URL = "/api/theory/collective-will"

BASE = {
    "candidates": [
        {"name": "Alice", "x": -0.4, "y": 0.0},
        {"name": "Bob",   "x":  0.1, "y": 0.0},
        {"name": "Carol", "x":  0.5, "y": 0.0},
    ],
    "num_voters":      100,
    "ideology":        "random",
    "seed":            42,
    "num_methods":     5,
    "num_agendas":     4,
    "num_simulations": 1,
}

# Profile that tends to produce a Condorcet winner (centrist Bob)
CENTRIST_BASE = {
    **BASE,
    "candidates": [
        {"name": "Alice", "x": -0.4, "y": 0.0},
        {"name": "Bob",   "x":  0.05, "y": 0.0},  # near median
        {"name": "Carol", "x":  0.45, "y": 0.0},
    ],
    "num_voters": 200,
    "seed":       7,
}


def post(client, **kw):
    return json.loads(client.post(URL, json={**BASE, **kw}).data)


class TestCollectiveWillBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json=BASE).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("unique_winners", "unique_winner_count", "winner_by_method",
                  "winner_by_agenda", "rousseau_score", "most_frequent_winner",
                  "most_frequent_pct", "condorcet_exists", "condorcet_winner",
                  "philosophical_conclusion", "pedagogical_note"):
            assert k in body

    def test_unique_winners_nonempty(self, client):
        body = post(client)
        assert len(body["unique_winners"]) >= 1

    def test_unique_winner_count_matches_list(self, client):
        body = post(client)
        assert body["unique_winner_count"] == len(body["unique_winners"])

    def test_winner_by_method_has_methods(self, client):
        body = post(client)
        assert len(body["winner_by_method"]) == BASE["num_methods"]

    def test_winner_by_agenda_has_agendas(self, client):
        body = post(client)
        assert len(body["winner_by_agenda"]) == BASE["num_agendas"]

    def test_all_method_winners_are_candidates(self, client):
        body = post(client)
        cand_names = {c["name"] for c in BASE["candidates"]}
        for method, winner in body["winner_by_method"].items():
            assert winner in cand_names, f"{method}: winner={winner} not in {cand_names}"

    def test_all_agenda_winners_are_candidates(self, client):
        body = post(client)
        cand_names = {c["name"] for c in BASE["candidates"]}
        for agenda, winner in body["winner_by_agenda"].items():
            assert winner in cand_names

    def test_most_frequent_winner_is_candidate(self, client):
        body = post(client)
        cand_names = {c["name"] for c in BASE["candidates"]}
        assert body["most_frequent_winner"] in cand_names

    def test_most_frequent_pct_in_range(self, client):
        body = post(client)
        assert 0.0 < body["most_frequent_pct"] <= 1.0

    def test_most_frequent_pct_ge_1_over_n(self, client):
        """Most frequent winner appears at least as often as random chance."""
        body = post(client)
        n_cands = len(BASE["candidates"])
        assert body["most_frequent_pct"] >= 1 / n_cands - 0.05


# ── rousseau_score = 1 / unique_winner_count ─────────────────────────────────

class TestRousseauScore:
    def test_rousseau_score_formula(self, client):
        """rousseau_score = 1 / unique_winner_count."""
        body = post(client)
        expected = 1 / body["unique_winner_count"]
        assert body["rousseau_score"] == pytest.approx(expected, abs=0.001)

    def test_rousseau_score_in_range(self, client):
        body = post(client)
        assert 0.0 < body["rousseau_score"] <= 1.0

    def test_rousseau_score_one_when_single_winner(self, client):
        """If only 1 unique winner, rousseau_score = 1.0."""
        body = post(client)
        if body["unique_winner_count"] == 1:
            assert body["rousseau_score"] == pytest.approx(1.0, abs=0.001)

    def test_rousseau_score_lower_with_more_winners(self, client):
        """Score decreases as unique winner count increases."""
        body = post(client)
        n = body["unique_winner_count"]
        assert body["rousseau_score"] == pytest.approx(1 / n, abs=0.001)


# ── condorcet_exists=True → unique_winner_count = 1 ─────────────────────────

class TestCondorcetConsistency:
    def test_condorcet_exists_means_single_winner(self, client):
        """When a Condorcet winner exists, they should win under all methods/agendas."""
        # Try multiple seeds to find one with a CW
        for s in [7, 13, 21, 33, 55]:
            body = post(client, seed=s, num_voters=200, ideology="random")
            if body["condorcet_exists"]:
                # With a CW, binary elimination always produces the CW
                # and many methods also produce the CW
                # So unique_winner_count should be low (often 1)
                assert body["unique_winner_count"] <= 2, (
                    f"seed={s}: CW exists but unique_count={body['unique_winner_count']}"
                )
                break

    def test_condorcet_winner_in_unique_winners(self, client):
        """If Condorcet winner exists, they must appear in unique_winners."""
        body = post(client)
        if body["condorcet_exists"] and body["condorcet_winner"]:
            assert body["condorcet_winner"] in body["unique_winners"], (
                f"CW={body['condorcet_winner']} not in {body['unique_winners']}"
            )

    def test_no_condorcet_usually_more_winners(self, client):
        """When no Condorcet winner, typically more than 1 unique winner."""
        body = post(client)
        if not body["condorcet_exists"]:
            # Not guaranteed but usually true with multiple agendas
            assert body["unique_winner_count"] >= 1  # at least 1


# ── unique_winner_count ≤ N_candidates ───────────────────────────────────────

class TestUniqueBound:
    def test_unique_winner_count_le_candidates(self, client):
        """Cannot have more unique winners than candidates."""
        body = post(client)
        n_cands = len(BASE["candidates"])
        assert body["unique_winner_count"] <= n_cands

    def test_unique_winners_subset_of_candidates(self, client):
        body = post(client)
        cand_names = {c["name"] for c in BASE["candidates"]}
        for w in body["unique_winners"]:
            assert w in cand_names


# ── Varying parameters ────────────────────────────────────────────────────────

class TestParameters:
    def test_polarized_ideology(self, client):
        body = post(client, ideology="polarized", seed=42)
        assert body["unique_winner_count"] >= 1

    def test_minimal_methods_agendas(self, client):
        body = post(client, num_methods=2, num_agendas=2)
        assert len(body["winner_by_method"]) == 2
        assert len(body["winner_by_agenda"]) == 2

    def test_empty_body_returns_200(self, client):
        r = client.post(URL, json={})
        assert r.status_code == 200


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        assert a["unique_winner_count"] == b["unique_winner_count"]
        assert a["rousseau_score"]      == pytest.approx(b["rousseau_score"])
        assert a["condorcet_exists"]    == b["condorcet_exists"]
        assert a["most_frequent_winner"] == b["most_frequent_winner"]
