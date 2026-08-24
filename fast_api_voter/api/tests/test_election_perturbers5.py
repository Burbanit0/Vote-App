"""Tests for Phase 3 batch 7:
/api/v2/election/{simulate-pipeline, districts, primary, stv}."""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]


# ── /simulate-pipeline ──────────────────────────────────────────────────────

class TestSimulatePipeline:
    payload = {
        "candidates": CANDS, "num_voters": 60, "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/simulate-pipeline", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("steps", "candidates", "num_steps"):
            assert k in body
        assert body["num_steps"] >= 2  # at least base + results

    def test_accepts_campaign_and_blank(self, client):
        ok = {
            **self.payload,
            "campaign": {"enabled": True, "num_days": 15, "polling_effect": 0.3},
            "blank_vote": {"enabled": True, "rule": "symbolic"},
        }
        r = client.post("/api/v2/election/simulate-pipeline", json=ok)
        assert r.status_code == 200, r.text

    def test_rejects_too_many_voters(self, client):
        bad = {**self.payload, "num_voters": 999}
        assert client.post("/api/v2/election/simulate-pipeline",
                           json=bad).status_code == 422

    def test_rejects_single_candidate(self, client):
        bad = {**self.payload, "candidates": [CANDS[0]]}
        assert client.post("/api/v2/election/simulate-pipeline",
                           json=bad).status_code == 422


# ── /districts ──────────────────────────────────────────────────────────────

class TestDistricts:
    payload = {
        "candidates": CANDS, "num_districts": 8,
        "voters_per_district": 80, "seed": 42,
        "district_ideology_variance": 0.3,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/districts", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("districts", "parliament_fptp", "parliament_proportional",
                  "national_vote_share", "distortion", "fptp_winner",
                  "proportional_winner", "num_districts"):
            assert k in body
        assert len(body["districts"]) == 8

    def test_rejects_too_few_districts(self, client):
        bad = {**self.payload, "num_districts": 2}
        assert client.post("/api/v2/election/districts",
                           json=bad).status_code == 422

    def test_rejects_too_many_districts(self, client):
        bad = {**self.payload, "num_districts": 99}
        assert client.post("/api/v2/election/districts",
                           json=bad).status_code == 422

    def test_ideology_variance_is_wired_into_the_district_simulation(self):
        """ideology_variance must actually perturb intra-district voter
        positions, not just be silently dropped (regression for a dead
        parameter found by the code audit)."""
        from api.domain.election.workers import _run_district_fptp
        from api.engine.constants import DEFAULT_ISSUES
        from api.domain.election._helpers import build_candidate_from_xy

        issues = DEFAULT_ISSUES
        candidates = [
            build_candidate_from_xy(0, "Alice", -0.5, -0.2, issues),
            build_candidate_from_xy(1, "Bob",    0.5,  0.2, issues),
        ]
        args = (["Alice", "Bob"], candidates, 200, 0.1)

        # variance=0 must reduce to the old deterministic (noise-free) shift,
        # so repeating it with the same seed is exactly reproducible.
        no_variance_a = _run_district_fptp(*args, 0.0, issues, seed=7)
        no_variance_b = _run_district_fptp(*args, 0.0, issues, seed=7)
        assert no_variance_a == no_variance_b

        # A nonzero variance must, for at least some seeds, actually move the
        # outcome relative to the noise-free run — otherwise the parameter is
        # still being ignored. Checked over several seeds since any single
        # seed's per-voter noise can coincidentally net out to the same shares.
        differs = any(
            _run_district_fptp(*args, 1.0, issues, seed=s)["vote_shares"]
            != _run_district_fptp(*args, 0.0, issues, seed=s)["vote_shares"]
            for s in range(1, 6)
        )
        assert differs


# ── /primary ────────────────────────────────────────────────────────────────

class TestPrimary:
    payload = {
        "parties": [
            {
                "name": "Left", "ideology_center": -0.5,
                "primary_voters_pct": 0.3,
                "primary_candidates": [
                    {"name": "L1", "ideology_position": -0.6},
                    {"name": "L2", "ideology_position": -0.3},
                ],
            },
            {
                "name": "Right", "ideology_center": 0.5,
                "primary_voters_pct": 0.3,
                "primary_candidates": [
                    {"name": "R1", "ideology_position": 0.6},
                    {"name": "R2", "ideology_position": 0.3},
                ],
            },
        ],
        "general_num_voters": 200,
        "general_ideology": "random",
        "primary_method": "plurality",
        "general_method": "plurality",
        "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/primary", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("primaries", "general_ballot", "general_winner",
                  "general_vote_shares", "median_voter_distance",
                  "without_primaries_winner"):
            assert k in body
        assert len(body["primaries"]) == 2

    def test_rejects_single_party(self, client):
        bad = {**self.payload, "parties": [self.payload["parties"][0]]}
        assert client.post("/api/v2/election/primary",
                           json=bad).status_code == 422

    def test_rejects_party_with_one_primary_candidate(self, client):
        bad = {
            **self.payload,
            "parties": [
                {
                    "name": "Left", "ideology_center": -0.5,
                    "primary_voters_pct": 0.3,
                    "primary_candidates": [
                        {"name": "L1", "ideology_position": -0.6},
                    ],
                },
                self.payload["parties"][1],
            ],
        }
        assert client.post("/api/v2/election/primary",
                           json=bad).status_code == 422


# ── /stv ────────────────────────────────────────────────────────────────────

class TestStv:
    payload = {
        "candidates": [
            {"name": "Alice", "x": -0.5, "y": -0.2},
            {"name": "Bob",   "x":  0.5, "y":  0.2},
            {"name": "Carol", "x":  0.0, "y":  0.1},
            {"name": "Dave",  "x": -0.2, "y":  0.4},
        ],
        "num_voters": 200, "seed": 42, "num_seats": 3,
        "quota_type": "droop",
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/election/stv", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("stv", "dhondt", "fptp", "vote_shares", "num_seats",
                  "quota", "quota_type", "distortion_stv_dhondt",
                  "distortion_stv_fptp", "candidates"):
            assert k in body
        assert len(body["stv"]["elected"]) == 3

    def test_rejects_too_many_seats(self, client):
        bad = {**self.payload, "num_seats": 99}
        assert client.post("/api/v2/election/stv",
                           json=bad).status_code == 422

    def test_rejects_seats_geq_candidates(self, client):
        # Pydantic accepts num_seats=4 but worker returns 400
        bad = {**self.payload, "num_seats": 4}
        r = client.post("/api/v2/election/stv", json=bad)
        assert r.status_code == 400, r.text

    def test_rejects_too_few_voters(self, client):
        bad = {**self.payload, "num_voters": 10}
        assert client.post("/api/v2/election/stv",
                           json=bad).status_code == 422
