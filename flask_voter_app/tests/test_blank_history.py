"""
test_blank_history.py — Tests for the blank-vote time-series route and data helpers.
"""
import pytest
from app.utils.real_election_data import (
    get_blank_history,
    list_blank_history_countries,
    BLANK_VOTE_HISTORY,
)


# ── Data helpers ───────────────────────────────────────────────────────────────

def test_get_blank_history_france_returns_data():
    data = get_blank_history("france")
    assert data is not None
    assert data["country"] == "france"
    assert len(data["series"]) >= 5


def test_get_blank_history_colombia_returns_data():
    data = get_blank_history("colombia")
    assert data is not None
    assert len(data["series"]) >= 4


def test_get_blank_history_uruguay_returns_data():
    data = get_blank_history("uruguay")
    assert data is not None
    assert len(data["series"]) >= 4


def test_series_sorted_ascending_by_year():
    """Series must be sorted by year ascending for all countries."""
    for key in BLANK_VOTE_HISTORY:
        data = get_blank_history(key)
        assert data is not None
        years = [p["year"] for p in data["series"]]
        assert years == sorted(years), f"{key}: years not sorted"


def test_each_series_point_has_required_fields():
    for key in BLANK_VOTE_HISTORY:
        data = get_blank_history(key)
        assert data is not None
        for point in data["series"]:
            assert "year" in point
            assert "blank_pct" in point
            assert "context" in point
            assert isinstance(point["year"], int)
            assert isinstance(point["blank_pct"], float)
            assert len(point["context"]) > 10


def test_blank_pct_in_valid_range():
    for key in BLANK_VOTE_HISTORY:
        data = get_blank_history(key)
        assert data is not None
        for point in data["series"]:
            assert 0.0 <= point["blank_pct"] <= 100.0


def test_response_has_note_and_display_name():
    data = get_blank_history("france")
    assert "note" in data
    assert "display_name" in data
    assert len(data["note"]) > 20
    assert "France" in data["display_name"]


def test_unknown_country_returns_none():
    assert get_blank_history("unknowncountry") is None
    assert get_blank_history("") is None
    assert get_blank_history("USA") is None


def test_case_insensitive_lookup():
    assert get_blank_history("FRANCE") is not None
    assert get_blank_history("France") is not None
    assert get_blank_history("COLOMBIA") is not None


def test_alias_fr_resolves_to_france():
    data = get_blank_history("fr")
    assert data is not None
    assert data["country"] == "france"


def test_list_blank_history_countries_returns_all():
    countries = list_blank_history_countries()
    keys = {c["key"] for c in countries}
    assert "france" in keys
    assert "colombia" in keys
    assert "uruguay" in keys
    for c in countries:
        assert "key" in c
        assert "display_name" in c


# ── API route ──────────────────────────────────────────────────────────────────

def test_route_france_returns_200(client):
    resp = client.get("/simulations/blank-history?country=france")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["country"] == "france"
    assert "series" in data
    assert len(data["series"]) >= 5


def test_route_colombia_returns_200(client):
    resp = client.get("/simulations/blank-history?country=colombia")
    assert resp.status_code == 200
    assert len(resp.get_json()["series"]) >= 4


def test_route_uruguay_returns_200(client):
    resp = client.get("/simulations/blank-history?country=uruguay")
    assert resp.status_code == 200
    assert len(resp.get_json()["series"]) >= 4


def test_route_unknown_country_returns_404(client):
    resp = client.get("/simulations/blank-history?country=germany")
    assert resp.status_code == 404
    data = resp.get_json()
    assert "error" in data
    assert "available" in data


def test_route_missing_country_returns_400(client):
    resp = client.get("/simulations/blank-history")
    assert resp.status_code == 400


def test_route_series_sorted_ascending(client):
    """The API must return series sorted by year ascending."""
    resp = client.get("/simulations/blank-history?country=france")
    assert resp.status_code == 200
    series = resp.get_json()["series"]
    years = [p["year"] for p in series]
    assert years == sorted(years)


def test_route_all_series_points_valid(client):
    """All returned series points must have year, blank_pct, and context."""
    for country in ("france", "colombia", "uruguay"):
        resp = client.get(f"/simulations/blank-history?country={country}")
        assert resp.status_code == 200
        for point in resp.get_json()["series"]:
            assert isinstance(point["year"], int)
            assert isinstance(point["blank_pct"], (int, float))
            assert isinstance(point["context"], str)
            assert len(point["context"]) > 5


def test_route_case_insensitive(client):
    resp = client.get("/simulations/blank-history?country=FRANCE")
    assert resp.status_code == 200


def test_route_returns_note(client):
    resp = client.get("/simulations/blank-history?country=france")
    assert "note" in resp.get_json()
