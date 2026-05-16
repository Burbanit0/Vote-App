"""
test_api_public.py — Tests for the Vote Lab Public Research API v1.
"""
import json
import pytest
from app.routes.api_public import METHODS_CATALOG, OPENAPI_SPEC


# ── /api/v1/methods ───────────────────────────────────────────────────────────

def test_methods_returns_200(client):
    resp = client.get("/api/v1/methods")
    assert resp.status_code == 200


def test_methods_returns_16_or_more(client):
    resp = client.get("/api/v1/methods")
    data = resp.get_json()
    assert data["count"] >= 16


def test_methods_response_structure(client):
    resp = client.get("/api/v1/methods")
    data = resp.get_json()
    assert "count" in data
    assert "methods" in data
    assert "families" in data
    for m in data["methods"]:
        assert "key"    in m
        assert "name"   in m
        assert "family" in m
        assert "ref"    in m


def test_methods_includes_standard_methods(client):
    resp = client.get("/api/v1/methods")
    keys = {m["key"] for m in resp.get_json()["methods"]}
    for key in ("plurality", "borda", "schulze", "irv", "approval", "condorcet"):
        assert key in keys, f"Missing method key: {key}"


def test_methods_filter_by_family(client):
    resp = client.get("/api/v1/methods?family=ranked")
    data = resp.get_json()
    for m in data["methods"]:
        assert m["family"] == "ranked"


def test_methods_includes_quadratic(client):
    resp = client.get("/api/v1/methods")
    keys = {m["key"] for m in resp.get_json()["methods"]}
    assert "quadratic" in keys


def test_methods_catalog_has_16_plus_entries():
    """Data-layer check independent of HTTP."""
    assert len(METHODS_CATALOG) >= 16


# ── /api/v1/simulate ─────────────────────────────────────────────────────────

def test_simulate_returns_200_with_valid_params(client):
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 3,
        "num_voters":     80,
        "methods":        ["plurality", "borda"],
    })
    assert resp.status_code == 200


def test_simulate_result_has_winner(client):
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 3,
        "num_voters":     80,
        "methods":        ["plurality"],
    })
    data = resp.get_json()
    assert "methods" in data
    assert "plurality" in data["methods"]
    winner = data["methods"]["plurality"]["winner"]
    # winner is one of the synthetic candidate names
    assert winner in ("Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo")


def test_simulate_returns_condorcet_winner(client):
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 3,
        "num_voters":     100,
    })
    data = resp.get_json()
    assert "condorcet_winner" in data


def test_simulate_filters_requested_methods(client):
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 3,
        "num_voters":     60,
        "methods":        ["borda", "schulze"],
    })
    data = resp.get_json()
    method_keys = set(data["methods"].keys())
    assert "borda"   in method_keys
    assert "schulze" in method_keys
    assert "plurality" not in method_keys   # not requested


def test_simulate_all_methods_when_not_specified(client):
    resp = client.post("/api/v1/simulate", json={"num_candidates": 3, "num_voters": 60})
    data = resp.get_json()
    # Should have many methods
    assert len(data["methods"]) >= 10


def test_simulate_returns_metrics(client):
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 3, "num_voters": 60, "methods": ["borda"],
    })
    m = resp.get_json()["methods"]["borda"]
    for key in ("winner", "bayesian_regret", "majority_satisfaction", "condorcet_consistent"):
        assert key in m


def test_simulate_invalid_num_candidates(client):
    resp = client.post("/api/v1/simulate", json={"num_candidates": "bad"})
    assert resp.status_code == 400


def test_simulate_caps_num_voters(client):
    """num_voters above 2000 should be capped silently (no error)."""
    resp = client.post("/api/v1/simulate", json={
        "num_candidates": 2, "num_voters": 99999, "methods": ["plurality"],
    })
    assert resp.status_code == 200


# ── /api/v1/compare ──────────────────────────────────────────────────────────

def test_compare_returns_200(client):
    resp = client.post("/api/v1/compare", json={
        "num_candidates": 3, "num_voters": 60, "methods": ["plurality"],
    })
    assert resp.status_code == 200


def test_compare_with_blank_rule(client):
    resp = client.post("/api/v1/compare", json={
        "num_candidates": 3,
        "num_voters":     60,
        "blank_rule":     "threshold_30",
        "methods":        ["plurality"],
    })
    assert resp.status_code == 200
    data = resp.get_json()
    # blank_pct should be present when blank_rule is set
    assert "blank_pct" in data


def test_compare_blank_rule_applied_in_methods(client):
    resp = client.post("/api/v1/compare", json={
        "num_candidates": 3, "num_voters": 60,
        "blank_rule": "symbolic", "methods": ["plurality"],
    })
    data = resp.get_json()
    assert "blank_rule_applied" in data["methods"]["plurality"]


def test_compare_invalid_blank_rule(client):
    resp = client.post("/api/v1/compare", json={
        "num_candidates": 3, "num_voters": 60, "blank_rule": "invalid_rule",
    })
    assert resp.status_code == 400


# ── /api/v1/real-elections ────────────────────────────────────────────────────

def test_real_elections_returns_200(client):
    resp = client.get("/api/v1/real-elections")
    assert resp.status_code == 200


def test_real_elections_response_structure(client):
    data = client.get("/api/v1/real-elections").get_json()
    assert "count" in data
    assert "elections" in data
    assert data["count"] >= 4


def test_real_elections_each_entry_valid(client):
    data = client.get("/api/v1/real-elections").get_json()
    for e in data["elections"]:
        assert "key"     in e
        assert "name"    in e
        assert "year"    in e
        assert "country" in e
        assert isinstance(e["num_candidates"], int)
        assert e["num_candidates"] >= 2


# ── /api/v1/openapi.json ─────────────────────────────────────────────────────

def test_openapi_spec_returns_200(client):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200


def test_openapi_spec_is_valid_json(client):
    resp = client.get("/api/v1/openapi.json")
    data = resp.get_json()
    assert data is not None
    assert data["openapi"] == "3.0.0"


def test_openapi_spec_has_required_fields(client):
    data = client.get("/api/v1/openapi.json").get_json()
    assert "info"    in data
    assert "paths"   in data
    assert "servers" in data


def test_openapi_spec_documents_all_endpoints():
    paths = OPENAPI_SPEC["paths"]
    for path in ("/api/v1/methods", "/api/v1/simulate", "/api/v1/compare", "/api/v1/real-elections"):
        assert path in paths, f"Path {path} missing from OpenAPI spec"


def test_openapi_spec_info_has_title_and_version():
    info = OPENAPI_SPEC["info"]
    assert "title"   in info
    assert "version" in info
    assert len(info["title"]) > 5


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_simulate_rate_limit_returns_429_after_limit(client):
    """
    After 10 successful POST /api/v1/simulate calls, the 11th should be
    rate-limited (HTTP 429).  Tests use memory:// storage so limits reset
    between test runs.
    """
    payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
    status_codes = []
    for _ in range(12):
        resp = client.post("/api/v1/simulate", json=payload)
        status_codes.append(resp.status_code)
    # At least one 429 should appear after the limit is hit
    assert 429 in status_codes, (
        f"Expected 429 after 10 requests, got: {status_codes}"
    )


def test_compare_rate_limit_returns_429_after_limit(client):
    """After 5 POST /api/v1/compare calls, the 6th should be rate-limited."""
    payload = {"num_candidates": 2, "num_voters": 50, "methods": ["plurality"]}
    status_codes = []
    for _ in range(7):
        resp = client.post("/api/v1/compare", json=payload)
        status_codes.append(resp.status_code)
    assert 429 in status_codes, (
        f"Expected 429 after 5 requests, got: {status_codes}"
    )
