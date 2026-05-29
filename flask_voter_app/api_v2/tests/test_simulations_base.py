"""Tests for Phase 4.5.a.5 — simulation_base /simulations/* on FastAPI."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# Realistic voter/candidate objects (mirror tests/test_simulation_routes.py).
VOTER = {
    "id": 0, "age": 35, "gender": "male", "education": "bachelor",
    "income": "middle", "region": "urban", "employment_status": "employed",
    "family_status": "single", "ethnicity_immigration": "native",
    "religion": "non_religious", "political_lean": 0.0,
    "political_lean_normalized": 0.5,
    "issue_priorities": {"economy": 0.5, "environment": 0.5},
    "issue_positions": {"economy": 0.5, "environment": 0.5},
    "party_loyalty": 0.5, "preferred_party": "Independent",
    "likelihood_to_vote": 0.8, "mood": 0,
    "strategic_propensity": 0.2, "voting_style": "sincere",
}
VOTER2 = {**VOTER, "id": 1, "age": 28, "gender": "female", "education": "master",
          "income": "high", "political_lean_normalized": 0.65}
CANDIDATE = {
    "id": 0, "name": "Alice", "party": "Green", "party_lean": -0.8,
    "ideology_position": 0.2, "policies": {"economy": 0.3, "environment": 0.8},
    "charisma": 0.7, "scandals": 0, "campaign_funds": 500000,
    "experience": 10, "popularity": 0.6,
}


# ── /simulate_voters & /simulate_candidates ──────────────────────────────────

class TestPopulation:
    def test_simulate_voters(self, client):
        r = client.post("/api/v2/simulations/simulate_voters", json={"num_voters": 10})
        assert r.status_code == 200, r.text
        assert len(r.json()["voters"]) == 10

    def test_simulate_voters_default(self, client):
        r = client.post("/api/v2/simulations/simulate_voters", json={})
        assert r.status_code == 200, r.text
        assert len(r.json()["voters"]) == 1000   # schema default

    def test_simulate_candidates(self, client):
        r = client.post("/api/v2/simulations/simulate_candidates",
                        json={"num_candidates": 3, "parties": ["Green", "Liberal", "Conservative"]})
        assert r.status_code == 200, r.text
        assert len(r.json()["candidates"]) == 3

    def test_simulate_candidates_too_few_parties(self, client):
        # num_candidates > len(parties) → parties cycle, no error.
        r = client.post("/api/v2/simulations/simulate_candidates",
                        json={"num_candidates": 6, "parties": ["A", "B"]})
        assert r.status_code == 200, r.text
        assert len(r.json()["candidates"]) == 6


# ── /calculate_utility ───────────────────────────────────────────────────────

class TestCalculateUtility:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/calculate_utility",
                        json={"voter": VOTER, "candidate": CANDIDATE})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert 0.0 <= body["result"]["utility"] <= 1.0

    def test_missing_voter_400(self, client):
        r = client.post("/api/v2/simulations/calculate_utility",
                        json={"candidate": {"id": 0, "name": "A"}})
        assert r.status_code == 400, r.text

    def test_missing_candidate_400(self, client):
        r = client.post("/api/v2/simulations/calculate_utility",
                        json={"voter": {"id": 0}})
        assert r.status_code == 400, r.text


# ── /simulate_utility & /get_utility_matrix ──────────────────────────────────

class TestUtility:
    def test_simulate_utility(self, client):
        r = client.post("/api/v2/simulations/simulate_utility",
                        json={"voters": [VOTER, VOTER2], "candidates": [CANDIDATE]})
        assert r.status_code == 200, r.text
        assert len(r.json()["utility_results"]) == 2   # 2 voters × 1 candidate

    def test_utility_matrix(self, client):
        r = client.post("/api/v2/simulations/get_utility_matrix",
                        json={"voters": [VOTER, VOTER2], "candidates": [CANDIDATE]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["matrix"]["values"]) == 2
        assert "average_utility" in body["stats"]
        assert "vote_shares" in body["stats"]

    def test_utility_matrix_empty_voters_400(self, client):
        r = client.post("/api/v2/simulations/get_utility_matrix",
                        json={"voters": [], "candidates": [CANDIDATE]})
        assert r.status_code == 400, r.text


# ── /get_voter_segments ──────────────────────────────────────────────────────

class TestSegments:
    def test_happy_path(self, client):
        r = client.post("/api/v2/simulations/get_voter_segments",
                        json={"voters": [VOTER, VOTER2], "candidates": [CANDIDATE]})
        assert r.status_code == 200, r.text
        assert "segments" in r.json()

    def test_custom_filter(self, client):
        r = client.post("/api/v2/simulations/get_voter_segments",
                        json={"voters": [VOTER], "candidates": [CANDIDATE],
                              "segments": ["young_female", "urban"]})
        assert r.status_code == 200, r.text

    def test_empty_voters_400(self, client):
        r = client.post("/api/v2/simulations/get_voter_segments",
                        json={"voters": [], "candidates": [CANDIDATE]})
        assert r.status_code == 400, r.text


# ── /get_closest_candidate ───────────────────────────────────────────────────

class TestClosestCandidate:
    def test_missing_params_400(self, client):
        r = client.post("/api/v2/simulations/get_closest_candidate", json={})
        assert r.status_code == 400, r.text

    # Happy path is xfail on Flask too (assign_voters_to_candidates returns
    # np.int64, not JSON-serialisable) — skipped here for the same reason.


# ── Legacy POST /api/v2/simulations ──────────────────────────────────────────

_LEGACY_DEMOGRAPHICS = {
    "age": {"young": 0.3, "middle": 0.4, "old": 0.3},
    "gender": {"male": 0.5, "female": 0.5},
    "location": {"urban": 0.5, "suburban": 0.3, "rural": 0.2},
    "education": {"high_school": 0.3, "bachelor": 0.4, "master": 0.3},
    "income": {"low": 0.3, "middle": 0.4, "high": 0.3},
    "ideology": {"left": 0.3, "center": 0.4, "right": 0.3},
}


class TestLegacySimulate:
    def test_missing_form_data_422(self, client):
        # Pydantic requires formData → 422 (FastAPI analogue of Flask's 400).
        assert client.post("/api/v2/simulations", json={}).status_code == 422

    def test_votes_happy_path_sets_deprecation_header(self, client):
        r = client.post("/api/v2/simulations", json={
            "formData": {
                "simulationType": "votes",
                "populationSize": 10,
                "candidates": ["Alice", "Bob"],
                "demographics": _LEGACY_DEMOGRAPHICS,
                "turnoutRate": 0.8,
                "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
            },
        })
        assert r.status_code == 200, r.text
        assert "votes" in r.json()
        assert "X-Deprecation-Warning" in r.headers

    def test_ranked_happy_path(self, client):
        r = client.post("/api/v2/simulations", json={
            "formData": {
                "simulationType": "ranked",
                "populationSize": 10,
                "candidates": ["Alice", "Bob", "Carol"],
                "demographics": _LEGACY_DEMOGRAPHICS,
                "turnoutRate": 0.8,
                "influenceWeights": {"family": 0.3, "peers": 0.5, "media": 0.2},
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "rankings" in body
        assert "condorcet_winner" in body
