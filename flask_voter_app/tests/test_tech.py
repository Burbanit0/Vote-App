"""
test_tech.py — Tests for /api/tech/e2e-demo and /api/tech/polis-simulation
"""
import json
import pytest

E2E_URL   = "/api/tech/e2e-demo"
POLIS_URL = "/api/tech/polis-simulation"

STATEMENTS = [
    "Les plateformes de location courte durée doivent être réglementées.",
    "Les hôtes devraient payer des taxes identiques aux hôtels.",
    "Les VTC doivent respecter les mêmes obligations que les taxis.",
    "La tarification dynamique est équitable pour les consommateurs.",
    "La sécurité des passagers prime sur la commodité des plateformes.",
    "Les travailleurs de plateforme méritent des protections sociales.",
    "L'innovation technologique devrait primer sur la réglementation.",
    "Les gouvernements locaux devraient contrôler les plateformes.",
]

BASE_POLIS = {
    "statements":       STATEMENTS,
    "num_participants": 80,
    "ideology":         "random",
    "seed":             42,
    "num_clusters":     3,
}


# ── E2E demo ──────────────────────────────────────────────────────────────────

class TestE2EDemo:
    def _run(self, client, **kw):
        payload = {"candidates": ["Alice", "Bob", "Carol"], "num_voters": 10, "seed": 42, **kw}
        return json.loads(client.post(E2E_URL, json=payload).data)

    def test_returns_200(self, client):
        assert client.post(E2E_URL, json={"num_voters": 10, "seed": 42}).status_code == 200

    def test_response_keys(self, client):
        body = self._run(client)
        for k in ("num_voters", "candidates", "encrypted_ballots",
                  "aggregate_result", "verification_demonstration", "privacy_guarantee"):
            assert k in body

    def test_correct_ballot_count(self, client):
        body = self._run(client)
        assert len(body["encrypted_ballots"]) == 10

    def test_verification_codes_unique(self, client):
        body = self._run(client)
        codes = [b["code"] for b in body["encrypted_ballots"]]
        assert len(codes) == len(set(codes)), "Verification codes must be unique"

    def test_no_individual_vote_revealed(self, client):
        body = self._run(client)
        candidates = set(body["candidates"])
        for ballot in body["encrypted_ballots"]:
            # The ballot must NOT contain the actual choice
            assert "choice" not in ballot
            # The encrypted field should not equal any candidate name
            for cand in candidates:
                assert cand not in ballot["encrypted"]

    def test_aggregate_sums_to_num_voters(self, client):
        body = self._run(client)
        total = sum(body["aggregate_result"].values())
        assert total == body["num_voters"]

    def test_aggregate_correct(self, client):
        """Sum of votes per candidate must equal num_voters."""
        body = self._run(client)
        agg = body["aggregate_result"]
        assert all(v >= 0 for v in agg.values())
        assert sum(agg.values()) == 10

    def test_all_candidates_in_result(self, client):
        body = self._run(client)
        assert set(body["aggregate_result"].keys()) == {"Alice", "Bob", "Carol"}

    def test_code_format(self, client):
        body = self._run(client)
        for b in body["encrypted_ballots"]:
            parts = b["code"].split("-")
            assert len(parts) == 3
            assert all(len(p) == 3 for p in parts)

    def test_reproducibility(self, client):
        a = self._run(client)
        b = self._run(client)
        assert a["aggregate_result"] == b["aggregate_result"]
        assert [x["code"] for x in a["encrypted_ballots"]] == \
               [x["code"] for x in b["encrypted_ballots"]]

    def test_single_candidate_rejected(self, client):
        assert client.post(E2E_URL, json={"candidates": ["Solo"], "num_voters": 5}).status_code == 400


# ── Pol.is simulation ─────────────────────────────────────────────────────────

class TestPolisBasic:
    def _run(self, client, **kw):
        payload = {**BASE_POLIS, **kw}
        return json.loads(client.post(POLIS_URL, json=payload).data)

    def test_returns_200(self, client):
        assert client.post(POLIS_URL, json=BASE_POLIS).status_code == 200

    def test_response_keys(self, client):
        body = self._run(client)
        for k in ("clusters", "consensus_statements", "polarizing_statements",
                  "participant_positions", "num_clusters", "num_participants"):
            assert k in body

    def test_cluster_count(self, client):
        body = self._run(client)
        assert len(body["clusters"]) == 3

    def test_cluster_sizes_sum(self, client):
        body = self._run(client)
        total = sum(c["size"] for c in body["clusters"])
        assert total == body["num_participants"]

    def test_participant_positions_count(self, client):
        body = self._run(client)
        assert len(body["participant_positions"]) == 80

    def test_participant_has_keys(self, client):
        body = self._run(client)
        p = body["participant_positions"][0]
        for k in ("id", "x_pca", "y_pca", "cluster_id"):
            assert k in p

    def test_cluster_ids_in_range(self, client):
        body = self._run(client)
        ids = {p["cluster_id"] for p in body["participant_positions"]}
        assert ids.issubset(set(range(3)))

    def test_votes_have_all_statements(self, client):
        body = self._run(client)
        for c in body["clusters"]:
            assert len(c["votes"]) == len(STATEMENTS)

    def test_vote_rates_in_01(self, client):
        body = self._run(client)
        for c in body["clusters"]:
            for stmt, rate in c["votes"].items():
                assert 0.0 <= rate <= 1.0, f"Invalid rate {rate} for {stmt}"

    def test_reproducibility(self, client):
        a = self._run(client)
        b = self._run(client)
        assert len(a["consensus_statements"]) == len(b["consensus_statements"])
        assert a["clusters"][0]["size"] == b["clusters"][0]["size"]


class TestPolisConsensus:
    def _run(self, client, **kw):
        return json.loads(client.post(POLIS_URL, json={**BASE_POLIS, **kw}).data)

    def test_consensus_has_high_approval(self, client):
        body = self._run(client)
        for s in body["consensus_statements"]:
            assert s["approval_rate"] >= 0.60

    def test_at_least_one_consensus_item(self, client):
        """Every 4th statement is designed as consensus — at least 1 should appear."""
        body = self._run(client)
        assert len(body["consensus_statements"]) >= 1

    def test_polarizing_high_delta(self, client):
        body = self._run(client)
        for s in body["polarizing_statements"]:
            assert s["cluster_delta"] >= 0.35


class TestPolarizedIdeology:
    def _run(self, client):
        return json.loads(client.post(POLIS_URL, json={
            **BASE_POLIS,
            "ideology":     "polarized",
            "num_clusters": 2,
        }).data)

    def test_two_clusters(self, client):
        body = self._run(client)
        assert len(body["clusters"]) == 2

    def test_clusters_non_empty(self, client):
        body = self._run(client)
        for c in body["clusters"]:
            assert c["size"] > 0

    def test_polarizing_statements_exist(self, client):
        body = self._run(client)
        # With polarized ideology and 2 clusters, some statements must be divisive
        assert len(body["polarizing_statements"]) >= 1


class TestNumClustersOne:
    def _run(self, client):
        return json.loads(client.post(POLIS_URL, json={
            **BASE_POLIS, "num_clusters": 1
        }).data)

    def test_one_cluster(self, client):
        body = self._run(client)
        assert len(body["clusters"]) == 1

    def test_no_polarizing_statements(self, client):
        body = self._run(client)
        # With only 1 cluster, no inter-cluster delta → no polarising items
        assert len(body["polarizing_statements"]) == 0

    def test_all_participants_in_cluster_0(self, client):
        body = self._run(client)
        ids = {p["cluster_id"] for p in body["participant_positions"]}
        assert ids == {0}


class TestPolisEdgeCases:
    def test_single_statement_rejected(self, client):
        payload = {**BASE_POLIS, "statements": ["Solo statement"]}
        assert client.post(POLIS_URL, json=payload).status_code == 400

    def test_max_clusters(self, client):
        payload = {**BASE_POLIS, "num_clusters": 5}
        assert client.post(POLIS_URL, json=payload).status_code == 200

    def test_large_electorate(self, client):
        payload = {**BASE_POLIS, "num_participants": 200}
        resp = client.post(POLIS_URL, json=payload)
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["num_participants"] == 200
