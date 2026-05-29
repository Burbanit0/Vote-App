"""Tests for Phase 4.5.a.4 — public research API /api/v1 on FastAPI."""
import pytest
from fastapi.testclient import TestClient

from api_v2.core.ratelimit import limiter
from api_v2.main import app


@pytest.fixture(autouse=True)
def _reset_limiter():
    """slowapi counters are process-global; reset between tests so a rate-limit
    test doesn't poison the next one (and vice-versa)."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── GET /api/v1/methods ─────────────────────────────────────────────────────

class TestMethods:
    def test_returns_200(self, client):
        assert client.get("/api/v1/methods").status_code == 200

    def test_count_16_or_more(self, client):
        assert client.get("/api/v1/methods").json()["count"] >= 16

    def test_structure(self, client):
        data = client.get("/api/v1/methods").json()
        assert {"count", "methods", "families"} <= data.keys()
        for m in data["methods"]:
            assert {"key", "name", "family", "ref"} <= m.keys()

    def test_includes_standard_methods(self, client):
        keys = {m["key"] for m in client.get("/api/v1/methods").json()["methods"]}
        for key in ("plurality", "borda", "schulze", "irv", "approval", "condorcet"):
            assert key in keys, f"Missing method key: {key}"

    def test_includes_quadratic(self, client):
        keys = {m["key"] for m in client.get("/api/v1/methods").json()["methods"]}
        assert "quadratic" in keys

    def test_filter_by_family(self, client):
        data = client.get("/api/v1/methods?family=ranked").json()
        assert data["methods"]
        for m in data["methods"]:
            assert m["family"] == "ranked"


# ── POST /api/v1/simulate ───────────────────────────────────────────────────

class TestSimulate:
    def test_happy_path(self, client):
        r = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 80, "methods": ["plurality", "borda"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "methods" in body
        winner = body["methods"]["plurality"]["winner"]
        assert winner in ("Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo")

    def test_filters_requested_methods(self, client):
        body = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda", "schulze"],
        }).json()
        keys = set(body["methods"].keys())
        assert "borda" in keys and "schulze" in keys
        assert "plurality" not in keys

    def test_all_methods_when_not_specified(self, client):
        body = client.post("/api/v1/simulate",
                           json={"num_candidates": 3, "num_voters": 60}).json()
        assert len(body["methods"]) >= 10

    def test_returns_condorcet_winner(self, client):
        body = client.post("/api/v1/simulate",
                           json={"num_candidates": 3, "num_voters": 100}).json()
        assert "condorcet_winner" in body

    def test_returns_metrics(self, client):
        m = client.post("/api/v1/simulate", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
        }).json()["methods"]["borda"]
        for key in ("winner", "bayesian_regret", "majority_satisfaction",
                    "condorcet_consistent"):
            assert key in m

    def test_invalid_num_candidates_type_422(self, client):
        # Non-int → Pydantic rejects with 422 (the FastAPI analogue of Flask's 400).
        assert client.post("/api/v1/simulate",
                           json={"num_candidates": "bad"}).status_code == 422

    def test_caps_num_voters_silently(self, client):
        # 99999 is clamped to 2000 by the worker, not rejected — 200 expected.
        r = client.post("/api/v1/simulate", json={
            "num_candidates": 2, "num_voters": 99999, "methods": ["plurality"],
        })
        assert r.status_code == 200, r.text


# ── POST /api/v1/compare ────────────────────────────────────────────────────

class TestCompare:
    def test_returns_200(self, client):
        r = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "methods": ["plurality"],
        })
        assert r.status_code == 200, r.text

    def test_with_blank_rule_exposes_blank_pct(self, client):
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60,
            "blank_rule": "threshold_30", "methods": ["plurality"],
        }).json()
        assert "blank_pct" in body

    def test_blank_rule_applied_in_methods(self, client):
        body = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60,
            "blank_rule": "symbolic", "methods": ["plurality"],
        }).json()
        assert "blank_rule_applied" in body["methods"]["plurality"]

    def test_invalid_blank_rule_400(self, client):
        r = client.post("/api/v1/compare", json={
            "num_candidates": 3, "num_voters": 60, "blank_rule": "invalid_rule",
        })
        assert r.status_code == 400, r.text


# ── GET /api/v1/real-elections ──────────────────────────────────────────────

class TestRealElections:
    def test_returns_200(self, client):
        assert client.get("/api/v1/real-elections").status_code == 200

    def test_structure(self, client):
        data = client.get("/api/v1/real-elections").json()
        assert data["count"] >= 4
        for e in data["elections"]:
            assert {"key", "name", "year", "country"} <= e.keys()
            assert isinstance(e["num_candidates"], int) and e["num_candidates"] >= 2


# ── GET /api/v1/openapi.json ────────────────────────────────────────────────

class TestOpenApi:
    def test_returns_200(self, client):
        assert client.get("/api/v1/openapi.json").status_code == 200

    def test_is_3_0_spec_with_paths(self, client):
        data = client.get("/api/v1/openapi.json").json()
        assert data["openapi"] == "3.0.0"
        assert "paths" in data and "info" in data
        for path in ("/api/v1/methods", "/api/v1/simulate", "/api/v1/compare"):
            assert path in data["paths"]


# ── Rate limiting (slowapi) ─────────────────────────────────────────────────

class TestRateLimits:
    def test_simulate_429_after_10(self, client):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        codes = [client.post("/api/v1/simulate", json=payload).status_code
                 for _ in range(12)]
        assert 429 in codes, f"Expected 429 after 10 requests, got: {codes}"

    def test_compare_429_after_5(self, client):
        payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
        codes = [client.post("/api/v1/compare", json=payload).status_code
                 for _ in range(7)]
        assert 429 in codes, f"Expected 429 after 5 requests, got: {codes}"
