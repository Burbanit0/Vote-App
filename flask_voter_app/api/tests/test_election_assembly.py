"""Tests for POST /api/v2/election/assembly — Lab reshape P3.

Pins the party-level engine to structural truths: PR is more proportional than
FPTP on the same electorate, thresholds exclude small parties, MMP compensates,
and coalition math respects the majority line.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


SIX_PARTIES = [
    {"name": "Verts",      "x": -0.3, "y": -0.4},
    {"name": "Soc",        "x": -0.5, "y": -0.1},
    {"name": "Centre",     "x":  0.0, "y":  0.0},
    {"name": "Lib",        "x":  0.3, "y":  0.0},
    {"name": "Cons",       "x":  0.5, "y":  0.3},
    {"name": "DroiteRad",  "x":  0.8, "y":  0.7},
]


def _payload(**overrides) -> dict:
    base = {
        "parties": SIX_PARTIES,
        "num_voters": 600,
        "ideology": "random",
        "seed": 42,
        "structure": "pr",
        "seats": 100,
        "threshold": 0.05,
        "apportionment": "dhondt",
    }
    base.update(overrides)
    return base


def test_pr_basic_shape(client: TestClient):
    res = client.post("/api/v2/election/assembly", json=_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["assembly_size"] == 100
    assert body["majority"] == 51
    assert sum(p["seats"] for p in body["parties"]) == 100
    # Shares are consistent.
    for p in body["parties"]:
        assert abs(p["seat_share"] - p["seats"] / 100) < 1e-6
    assert 0.0 <= body["wasted_vote_share"] <= 1.0


def test_fptp_less_proportional_than_pr(client: TestClient):
    """Same electorate: FPTP's Gallagher index ≥ PR's (winner's bonus)."""
    pr   = client.post("/api/v2/election/assembly", json=_payload(structure="pr", threshold=0.0)).json()
    fptp = client.post("/api/v2/election/assembly", json=_payload(structure="fptp")).json()
    assert pr["gallagher_index"] is not None and fptp["gallagher_index"] is not None
    assert fptp["gallagher_index"] >= pr["gallagher_index"]
    # FPTP also reduces the effective number of parties in seats.
    assert fptp["effective_parties_seats"] <= pr["effective_parties_seats"]


def test_threshold_excludes_small_parties(client: TestClient):
    """Raising the threshold can only exclude more (or equal) parties, and
    excluded parties hold zero list seats."""
    low  = client.post("/api/v2/election/assembly", json=_payload(threshold=0.0)).json()
    high = client.post("/api/v2/election/assembly", json=_payload(threshold=0.15)).json()
    excl_low  = {p["name"] for p in low["parties"] if p["excluded_by_threshold"]}
    excl_high = {p["name"] for p in high["parties"] if p["excluded_by_threshold"]}
    assert excl_low <= excl_high
    if not high["threshold_waived"]:
        for p in high["parties"]:
            if p["excluded_by_threshold"]:
                assert p["seats"] == 0


def test_mmp_compensates_toward_proportionality(client: TestClient):
    """MMP's disproportionality sits at or below FPTP's on the same electorate."""
    fptp = client.post("/api/v2/election/assembly", json=_payload(structure="fptp")).json()
    mmp  = client.post("/api/v2/election/assembly", json=_payload(structure="mmp")).json()
    assert mmp["gallagher_index"] <= fptp["gallagher_index"]
    # District wins are reported and bounded by total seats per party.
    for p in mmp["parties"]:
        assert 0 <= p["district_seats"] <= p["seats"]


def test_coalitions_are_minimal_and_winning(client: TestClient):
    body = client.post("/api/v2/election/assembly", json=_payload()).json()
    seats = {p["name"]: p["seats"] for p in body["parties"]}
    for c in body["coalitions"]:
        assert c["seats"] >= body["majority"]
        assert c["seats"] == sum(seats[m] for m in c["parties"])
        # minimal: every member is pivotal
        for m in c["parties"]:
            assert c["seats"] - seats[m] < body["majority"]


def test_deterministic_same_seed(client: TestClient):
    a = client.post("/api/v2/election/assembly", json=_payload()).json()
    b = client.post("/api/v2/election/assembly", json=_payload()).json()
    assert a == b


def test_rejects_single_party(client: TestClient):
    res = client.post("/api/v2/election/assembly", json=_payload(parties=SIX_PARTIES[:1]))
    assert res.status_code == 422  # Pydantic min_length=2
