"""Tests for Phase 4 batch 3:
/api/v2/theory/{majority-tyranny, democratic-backsliding, intergenerational, epistocracy}."""
import pytest
from fastapi.testclient import TestClient

from api_v2.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── /majority-tyranny ──────────────────────────────────────────────────────

class TestMajorityTyranny:
    payload = {
        "num_voters": 60, "majority_pct": 0.60,
        "minority_intensity": 3.0, "num_decisions": 30, "seed": 42,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/majority-tyranny", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("results", "tyranny_curve", "best_protector",
                  "least_efficient", "pedagogical_note"):
            assert k in body
        for rule in ("simple_majority", "supermajority_2_3", "unanimous",
                     "qv", "mj"):
            assert rule in body["results"]
        # Unanimity always protects minority (≥1 of them vetoes)
        assert body["results"]["unanimous"]["tyranny_index"] == 0.0

    def test_rejects_majority_pct_below_51(self, client):
        bad = {**self.payload, "majority_pct": 0.50}
        assert client.post("/api/v2/theory/majority-tyranny",
                           json=bad).status_code == 422


# ── /democratic-backsliding ────────────────────────────────────────────────

class TestDemocraticBacksliding:
    payload = {
        "candidates": [
            {"name": "Incumbent",  "x": 0.2, "y": 0.0},
            {"name": "Opposition", "x": -0.4, "y": 0.0},
        ],
        "num_voters": 80, "seed": 42,
        "num_elections": 5,
        "backsliding_method": "gerrymandering",
        "backsliding_intensity": 0.5,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/democratic-backsliding",
                        json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("elections", "autocracy_reached", "guardrails_effectiveness",
                  "tipping_points", "pedagogical_note"):
            assert k in body
        assert len(body["elections"]) == 5

    def test_accepts_guardrails(self, client):
        ok = {
            **self.payload,
            "guardrails": {
                "constitutional_court": True,
                "opposition_media": True,
                "international_pressure": False,
                "supermajority_required": False,
            },
        }
        r = client.post("/api/v2/theory/democratic-backsliding", json=ok)
        assert r.status_code == 200, r.text

    def test_rejects_too_many_elections(self, client):
        bad = {**self.payload, "num_elections": 99}
        assert client.post("/api/v2/theory/democratic-backsliding",
                           json=bad).status_code == 422


# ── /intergenerational ─────────────────────────────────────────────────────

class TestIntergenerational:
    def test_happy_path_default_battery(self, client):
        r = client.post("/api/v2/theory/intergenerational",
                        json={"num_voters": 80, "seed": 42,
                              "future_generations_mechanism": "proxy"})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("decisions_results", "mechanism_comparison",
                  "pedagogical_note"):
            assert k in body
        for mech in ("none", "proxy", "age_weighted", "veto"):
            assert mech in body["mechanism_comparison"]

    def test_accepts_custom_decisions(self, client):
        ok = {
            "num_voters": 60, "seed": 42,
            "future_generations_mechanism": "veto",
            "decisions": [
                {"name": "Climat", "cost_present": -0.3,
                 "benefit_future": 0.8, "time_horizon_years": 30},
                {"name": "Dette", "cost_present": 0.5,
                 "benefit_future": -0.6, "time_horizon_years": 25},
            ],
        }
        r = client.post("/api/v2/theory/intergenerational", json=ok)
        assert r.status_code == 200, r.text
        assert len(r.json()["decisions_results"]) == 2

    def test_rejects_wrong_age_distribution(self, client):
        bad = {"age_distribution": [0.5, 0.5]}   # only 2 buckets
        assert client.post("/api/v2/theory/intergenerational",
                           json=bad).status_code == 422


# ── /epistocracy ───────────────────────────────────────────────────────────

class TestEpistocracy:
    payload = {
        "candidates": [
            {"name": "A", "x": -0.5},
            {"name": "B", "x":  0.0},
            {"name": "C", "x":  0.5},
        ],
        "num_voters": 80, "seed": 42,
        "voter_competence_distribution": "uniform",
        "epistocracy_threshold": 0.7,
    }

    def test_happy_path(self, client):
        r = client.post("/api/v2/theory/epistocracy", json=self.payload)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("voter_competence_stats", "results", "democracy_vs_expert",
                  "condorcet_threshold", "pedagogical_note"):
            assert k in body
        for scheme in ("equal", "competence_weighted", "epistocratic",
                       "lottery"):
            assert scheme in body["results"]

    def test_accepts_bimodal_distribution(self, client):
        ok = {**self.payload, "voter_competence_distribution": "bimodal"}
        r = client.post("/api/v2/theory/epistocracy", json=ok)
        assert r.status_code == 200, r.text

    def test_rejects_threshold_above_1(self, client):
        bad = {**self.payload, "epistocracy_threshold": 1.5}
        assert client.post("/api/v2/theory/epistocracy",
                           json=bad).status_code == 422
