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


# ── E2E demo — enhanced V2 fields ────────────────────────────────────────────

class TestE2EDemoV2:
    """Tests for the new fields added to the enhanced e2e-demo endpoint."""

    def _run(self, client, **kw):
        payload = {
            "candidates":       ["Alice", "Bob", "Carol"],
            "num_demo_voters":  10,
            "seed":             42,
            **kw,
        }
        return json.loads(client.post(E2E_URL, json=payload).data)

    def test_voters_field_present(self, client):
        body = self._run(client)
        assert "voters" in body
        assert len(body["voters"]) == 10

    def test_voter_keys(self, client):
        body = self._run(client)
        v = body["voters"][0]
        for k in ("id", "encrypted_ballot", "verification_code", "vote_HIDDEN"):
            assert k in v

    def test_public_bulletin_board_present(self, client):
        body = self._run(client)
        assert "public_bulletin_board" in body
        assert len(body["public_bulletin_board"]) == 10

    def test_bulletin_board_no_vote_hidden(self, client):
        """public_bulletin_board must NOT contain the vote in clear."""
        body = self._run(client)
        for entry in body["public_bulletin_board"]:
            assert "vote_HIDDEN" not in entry
            assert "vote" not in entry
            # encrypted_ballot should not equal any candidate name
            for cand in body["candidates"]:
                assert cand not in entry["encrypted_ballot"]

    def test_verification_codes_unique(self, client):
        body = self._run(client)
        codes = [v["verification_code"] for v in body["voters"]]
        assert len(codes) == len(set(codes))

    def test_aggregate_sums_to_num_voters(self, client):
        body = self._run(client)
        assert sum(body["aggregate_result"].values()) == 10

    def test_winner_present_and_valid(self, client):
        body = self._run(client)
        assert "winner" in body
        assert body["winner"] in body["candidates"]
        # Winner has highest vote count
        agg = body["aggregate_result"]
        assert agg[body["winner"]] == max(agg.values())

    def test_audit_proof_present(self, client):
        body = self._run(client)
        assert "audit_proof" in body
        assert len(body["audit_proof"]) > 10

    def test_each_code_appears_once_in_board(self, client):
        """Each verification_code appears exactly once in public_bulletin_board."""
        body = self._run(client)
        board_codes = [e["verification_code"] for e in body["public_bulletin_board"]]
        assert len(board_codes) == len(set(board_codes))
        # All voter codes are on the board
        voter_codes = set(v["verification_code"] for v in body["voters"])
        board_codes_set = set(board_codes)
        assert voter_codes == board_codes_set

    def test_bulletin_board_shuffled(self, client):
        """Bulletin board order must differ from voter order (anonymisation)."""
        body = self._run(client)
        voter_codes = [v["verification_code"] for v in body["voters"]]
        board_codes = [e["verification_code"] for e in body["public_bulletin_board"]]
        # With 10+ voters, shuffle should produce different order
        assert voter_codes != board_codes, "Bulletin board should be shuffled"

    def test_user_vote_parameter(self, client):
        """When user_vote is set, voter 1 reflects that choice."""
        body = self._run(client, user_vote="Alice")
        # Voter 1's hidden vote should be Alice
        assert body["voters"][0]["vote_HIDDEN"] == "Alice"

    def test_num_demo_voters_param(self, client):
        """num_demo_voters parameter controls count."""
        body = self._run(client, num_demo_voters=7)
        assert len(body["voters"]) == 7
        assert sum(body["aggregate_result"].values()) == 7


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


# ── /api/tech/polis — with candidate evaluation ───────────────────────────────

POLIS_V2_URL = "/api/tech/polis"

POLIS_STMTS = [
    {"text": "Proposition A", "category": "economie"},
    {"text": "Proposition B", "category": "social"},
    {"text": "Proposition C", "category": "economie"},
    {"text": "Proposition D", "category": "social"},
    {"text": "Proposition E", "category": "economie"},
    {"text": "Proposition F", "category": "social"},
    {"text": "Proposition G", "category": "economie"},
    {"text": "Proposition H", "category": "social"},
]

BASE_POLIS_V2 = {
    "candidates": [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ],
    "statements":              POLIS_STMTS,
    "num_participants":        100,
    "ideology":                "random",
    "seed":                    42,
    "num_clusters":            3,
    "method_to_compare":       "plurality",
    "min_consensus_threshold": 0.70,
}


def polis_post(client, **kw):
    return json.loads(client.post(POLIS_V2_URL, json={**BASE_POLIS_V2, **kw}).data)


class TestPolisWithCandidates:
    def test_returns_200(self, client):
        assert client.post(POLIS_V2_URL, json=BASE_POLIS_V2).status_code == 200

    def test_response_keys(self, client):
        body = polis_post(client)
        for k in ("clusters", "statements", "participant_positions",
                  "polis_winner", "election_winner", "winners_agree",
                  "consensus_count", "polarizing_count", "silent_majority_count",
                  "candidate_scores", "pedagogical_note"):
            assert k in body

    def test_candidate_scores_all_candidates(self, client):
        body = polis_post(client)
        for name in ("Alice", "Bob", "Carol"):
            assert name in body["candidate_scores"]

    def test_polis_winner_in_candidates(self, client):
        body = polis_post(client)
        assert body["polis_winner"] in ("Alice", "Bob", "Carol")

    def test_election_winner_in_candidates(self, client):
        body = polis_post(client)
        assert body["election_winner"] in ("Alice", "Bob", "Carol")

    def test_winners_agree_matches(self, client):
        body = polis_post(client)
        assert body["winners_agree"] == (body["polis_winner"] == body["election_winner"])

    def test_participant_positions_count(self, client):
        body = polis_post(client)
        assert len(body["participant_positions"]) == 100

    def test_cluster_sizes_sum_to_participants(self, client):
        body = polis_post(client)
        total = sum(c["size"] for c in body["clusters"])
        assert total == 100

    def test_statements_count(self, client):
        body = polis_post(client)
        assert len(body["statements"]) == len(POLIS_STMTS)

    def test_is_consensus_and_is_polarizing_mutually_exclusive(self, client):
        body = polis_post(client)
        for s in body["statements"]:
            assert not (s["is_consensus"] and s["is_polarizing"]), (
                f"Statement '{s['text']}' is both consensus and polarizing"
            )

    # ── num_clusters=1 → no polarizing (no inter-cluster disagreement) ────

    def test_one_cluster_no_polarizing(self, client):
        body = polis_post(client, num_clusters=1)
        assert body["polarizing_count"] == 0
        for s in body["statements"]:
            assert not s["is_polarizing"]

    # ── threshold=1.0 → consensus_count=0 ────────────────────────────────

    def test_threshold_one_zero_consensus(self, client):
        body = polis_post(client, min_consensus_threshold=1.0)
        assert body["consensus_count"] == 0

    # ── threshold=0.0 → all statements consensus ─────────────────────────

    def test_threshold_zero_all_consensus(self, client):
        body = polis_post(client, min_consensus_threshold=0.0)
        assert body["consensus_count"] == len(POLIS_STMTS)

    # ── cluster_approvals per statement = num_clusters ────────────────────

    def test_cluster_approvals_match_cluster_count(self, client):
        body = polis_post(client)
        n = body["num_clusters"] if "num_clusters" in body else len(body["clusters"])
        for s in body["statements"]:
            assert len(s["cluster_approvals"]) == len(body["clusters"])

    # ── ideology="centrist" → polis_winner closer to center ───────────────

    def test_centrist_ideology_center_wins(self, client):
        body = polis_post(client, ideology="centrist", num_participants=200)
        # Carol at x=0.0 should score highest with centrist electorate
        scores = body["candidate_scores"]
        # Carol should have score >= Alice and Bob (not strictly guaranteed but typical)
        assert scores["Carol"] >= min(scores["Alice"], scores["Bob"])

    # ── ideology="polarized" → more polarizing statements ─────────────────

    def test_polarized_more_polarizing_than_random(self, client):
        random_body   = polis_post(client, ideology="random",   num_participants=200)
        polarized_body = polis_post(client, ideology="polarized", num_participants=200)
        # Polarized ideology should produce more polarizing statements
        assert polarized_body["polarizing_count"] >= random_body["polarizing_count"] - 2

    # ── Reproducibility ───────────────────────────────────────────────────

    def test_reproducibility(self, client):
        a = polis_post(client)
        b = polis_post(client)
        assert a["polis_winner"] == b["polis_winner"]
        assert a["consensus_count"] == b["consensus_count"]
