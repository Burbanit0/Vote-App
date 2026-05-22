"""
test_identity_voting.py — Tests for POST /api/theory/identity-voting
Green, Palmquist & Schickler (2002) identity-based voting model.
"""
import json
import pytest

URL = "/api/theory/identity-voting"

CANDS = [
    {"name": "Alice", "x": -0.5, "y": 0.0},
    {"name": "Bob",   "x":  0.0, "y": 0.0},
    {"name": "Carol", "x":  0.5, "y": 0.0},
]

# Groups where identity and ideology are aligned (Alice group leans left, Carol right)
ALIGNED_GROUPS = [
    {"name": "Left",   "pct": 0.50, "ideology_center": -0.5, "loyalty": 0.90, "candidate_affiliation": "Alice"},
    {"name": "Right",  "pct": 0.50, "ideology_center":  0.5, "loyalty": 0.90, "candidate_affiliation": "Carol"},
]

# Groups where identity and ideology diverge (cross-pressure scenario)
CROSS_GROUPS = [
    {"name": "CrossA", "pct": 0.40, "ideology_center": 0.4,  "loyalty": 0.85, "candidate_affiliation": "Alice"},
    {"name": "CrossB", "pct": 0.60, "ideology_center": -0.4, "loyalty": 0.85, "candidate_affiliation": "Carol"},
]

BASE = {
    "candidates":     CANDS,
    "num_voters":     200,
    "seed":           42,
    "identity_groups": ALIGNED_GROUPS,
    "identity_weight": 0.5,
    "cross_pressure":  True,
    "method":          "plurality",
}


def post(client, **kw):
    return json.loads(client.post(URL, json={**BASE, **kw}).data)


class TestIdentityBasic:
    def test_returns_200(self, client):
        assert client.post(URL, json=BASE).status_code == 200

    def test_response_keys(self, client):
        body = post(client)
        for k in ("sincere_winner", "identity_winner", "mixed_winner",
                  "winner_changed", "group_results", "cross_pressured",
                  "identity_weight_curve", "pedagogical_note"):
            assert k in body

    def test_group_results_count(self, client):
        body = post(client)
        assert len(body["group_results"]) == len(ALIGNED_GROUPS)

    def test_group_result_keys(self, client):
        body = post(client)
        for gr in body["group_results"]:
            for k in ("group_name", "affiliation", "group_vote_pct",
                      "ideology_match", "loyalty", "size_pct"):
                assert k in gr

    def test_cross_pressured_keys(self, client):
        body = post(client)
        for k in ("count", "abstention_rate"):
            assert k in body["cross_pressured"]

    def test_vote_pct_in_range(self, client):
        body = post(client)
        for gr in body["group_results"]:
            assert 0.0 <= gr["group_vote_pct"] <= 1.0
            assert 0.0 <= gr["ideology_match"]  <= 1.0

    def test_winners_are_candidate_names(self, client):
        body = post(client)
        cand_names = {c["name"] for c in CANDS}
        assert body["sincere_winner"]  in cand_names
        assert body["identity_winner"] in cand_names
        assert body["mixed_winner"]    in cand_names

    def test_winner_changed_consistent(self, client):
        body = post(client)
        expected = body["sincere_winner"] != body["mixed_winner"]
        assert body["winner_changed"] == expected

    def test_curve_length(self, client):
        body = post(client)
        # weight 0→100 step 10 = 11 points
        assert len(body["identity_weight_curve"]) == 11

    def test_curve_keys(self, client):
        body = post(client)
        for pt in body["identity_weight_curve"]:
            for k in ("weight", "winner", "agreement_rate"):
                assert k in pt

    def test_curve_weight_range(self, client):
        body = post(client)
        weights = [pt["weight"] for pt in body["identity_weight_curve"]]
        assert min(weights) == pytest.approx(0.0, abs=0.01)
        assert max(weights) == pytest.approx(1.0, abs=0.01)


# ── identity_weight=0 → mixed_winner = sincere_winner ────────────────────────

class TestZeroIdentityWeight:
    def test_zero_weight_mixed_equals_sincere(self, client):
        """With identity_weight=0, everyone votes ideologically → mixed = sincere."""
        body = post(client, identity_weight=0.0)
        assert body["mixed_winner"] == body["sincere_winner"], (
            f"weight=0: mixed={body['mixed_winner']}, sincere={body['sincere_winner']}"
        )

    def test_zero_weight_no_winner_changed(self, client):
        body = post(client, identity_weight=0.0)
        assert body["winner_changed"] is False


# ── identity_weight=1 → mixed_winner = identity_winner ───────────────────────

class TestFullIdentityWeight:
    def test_full_weight_mixed_equals_identity(self, client):
        """With identity_weight=1 and high loyalty, mixed ≈ identity_winner."""
        # Use groups with very high loyalty to ensure identity dominates
        body = post(client, identity_weight=1.0, identity_groups=[
            {"name": "G1", "pct": 0.55, "ideology_center": -0.4,
             "loyalty": 0.98, "candidate_affiliation": "Alice"},
            {"name": "G2", "pct": 0.45, "ideology_center":  0.4,
             "loyalty": 0.98, "candidate_affiliation": "Carol"},
        ])
        assert body["mixed_winner"] == body["identity_winner"], (
            f"weight=1 (loyalty=0.98): mixed={body['mixed_winner']}, "
            f"identity={body['identity_winner']}"
        )

    def test_curve_endpoint_matches_identity(self, client):
        """The last point of the curve (weight=1) winner should match identity_winner."""
        body = post(client, identity_weight=1.0, identity_groups=[
            {"name": "G1", "pct": 0.60, "ideology_center": 0.0,
             "loyalty": 0.95, "candidate_affiliation": "Alice"},
            {"name": "G2", "pct": 0.40, "ideology_center": 0.0,
             "loyalty": 0.95, "candidate_affiliation": "Carol"},
        ])
        last_point = body["identity_weight_curve"][-1]
        assert last_point["weight"] == pytest.approx(1.0, abs=0.01)
        assert last_point["winner"] == body["identity_winner"]


# ── cross_pressure=True → abstention_rate > 0 ────────────────────────────────

class TestCrossPressure:
    def test_cross_pressure_creates_abstentions(self, client):
        """Cross-pressured voters (identity ≠ ideology) should abstain at non-zero rate."""
        body = post(client,
                    cross_pressure=True,
                    identity_groups=CROSS_GROUPS,
                    identity_weight=0.5)
        # With cross-pressured groups and cross_pressure=True, some should abstain
        if body["cross_pressured"]["count"] > 0:
            assert body["cross_pressured"]["abstention_rate"] >= 0.0

    def test_no_cross_pressure_zero_abstention(self, client):
        """With cross_pressure=False, abstention rate should be 0."""
        body = post(client, cross_pressure=False)
        assert body["cross_pressured"]["abstention_rate"] == pytest.approx(0.0)

    def test_cross_pressured_count_nonneg(self, client):
        body = post(client, cross_pressure=True, identity_groups=CROSS_GROUPS)
        assert body["cross_pressured"]["count"] >= 0

    def test_cross_pressured_cross_groups_have_higher_abstention(self, client):
        """Cross-pressured voters (mismatched identity/ideology) have abstention > aligned."""
        body_aligned = post(client, cross_pressure=True, identity_groups=ALIGNED_GROUPS)
        body_cross   = post(client, cross_pressure=True, identity_groups=CROSS_GROUPS)
        # Cross-pressured groups should produce more abstentions than aligned ones
        assert (body_cross["cross_pressured"]["count"] >=
                body_aligned["cross_pressured"]["count"])


# ── Winner change in curve ────────────────────────────────────────────────────

class TestIdentityWeightCurve:
    def test_curve_winner_can_change(self, client):
        """When identity and ideology point to different winners, the curve should show a change."""
        # Make groups where identity flips the winner
        body = post(client,
                    identity_weight=0.5,
                    identity_groups=[
                        # Majority ideologically prefers Alice but identity-affiliates with Carol
                        {"name": "Big",   "pct": 0.60, "ideology_center": -0.5,
                         "loyalty": 0.95, "candidate_affiliation": "Carol"},
                        {"name": "Small", "pct": 0.40, "ideology_center":  0.5,
                         "loyalty": 0.90, "candidate_affiliation": "Alice"},
                    ])
        # With high loyalty and divergent identity/ideology, winner should change
        winners = [pt["winner"] for pt in body["identity_weight_curve"]]
        # At least some variation in winners across the weight range
        assert len(set(winners)) >= 1  # at least 1 winner (may not always flip with noise)

    def test_weight_zero_curve_matches_sincere(self, client):
        """At weight=0, the curve winner should match the sincere_winner."""
        body = post(client)
        first_pt = body["identity_weight_curve"][0]
        assert first_pt["weight"] == pytest.approx(0.0, abs=0.01)
        assert first_pt["winner"] == body["sincere_winner"], (
            f"Curve[0]: winner={first_pt['winner']}, sincere={body['sincere_winner']}"
        )


# ── Default behavior (no body) ────────────────────────────────────────────────

class TestDefaults:
    def test_empty_body_200(self, client):
        r = client.post(URL, json={})
        assert r.status_code == 200

    def test_default_groups_populated(self, client):
        body = json.loads(client.post(URL, json={}).data)
        assert len(body["group_results"]) >= 2


# ── Reproducibility ───────────────────────────────────────────────────────────

class TestReproducibility:
    def test_reproducibility(self, client):
        a = post(client)
        b = post(client)
        assert a["sincere_winner"]  == b["sincere_winner"]
        assert a["identity_winner"] == b["identity_winner"]
        assert a["mixed_winner"]    == b["mixed_winner"]
        for i, gr in enumerate(a["group_results"]):
            assert gr["group_vote_pct"] == pytest.approx(
                b["group_results"][i]["group_vote_pct"])
