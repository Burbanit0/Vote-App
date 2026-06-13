"""Tests for POST /api/v2/election/temporal — frontier FA-3.

Democracy as a repeated game: the acceptance pins Duverger-over-time (FPTP
compresses the party system across rounds while PR sustains it), evolving
metrics, and seed reproducibility.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


SIX_PARTIES = [
    {"name": "Verts",     "x": -0.3, "y": -0.4},
    {"name": "Soc",       "x": -0.5, "y": -0.1},
    {"name": "Centre",    "x":  0.0, "y":  0.0},
    {"name": "Lib",       "x":  0.3, "y":  0.0},
    {"name": "Cons",      "x":  0.5, "y":  0.3},
    {"name": "DroiteRad", "x":  0.8, "y":  0.7},
]


def _payload(**overrides) -> dict:
    base = {
        "parties": SIX_PARTIES,
        "num_voters": 400,
        "ideology": "random",
        "seed": 42,
        "structure": "pr",
        "seats": 100,
        "threshold": 0.0,
        "apportionment": "dhondt",
        "rounds": 20,
    }
    base.update(overrides)
    return base


def test_shape_and_metrics_evolve(client: TestClient):
    res = client.post("/api/v2/election/temporal", json=_payload(rounds=10))
    assert res.status_code == 200
    body = res.json()
    assert len(body["rounds"]) == 10
    r0 = body["rounds"][0]
    assert {p["name"] for p in r0["parties"]} == {p["name"] for p in SIX_PARTIES}
    assert r0["alternation"] is False  # no previous round
    # Parties actually move (adaptation) and positions stay in bounds.
    p0 = {p["name"]: (p["x"], p["y"]) for p in body["rounds"][0]["parties"]}
    pl = {p["name"]: (p["x"], p["y"]) for p in body["rounds"][-1]["parties"]}
    assert p0 != pl
    for x, y in pl.values():
        assert -1.0 <= x <= 1.0 and -1.0 <= y <= 1.0
    assert 0.0 <= body["alternation_rate"] <= 1.0


def test_duverger_over_time(client: TestClient):
    """20 rounds: FPTP + desertion compresses the party system; PR (no
    threshold) sustains it — both vs each other AND vs its own start.

    Districts must be meaningful for the squeeze: 20 seats over 600 voters
    (30-voter districts). With seats≈voters the district top-2 is pure noise.
    """
    knobs = dict(num_voters=600, seats=20, strategic_desertion=True)
    pr = client.post("/api/v2/election/temporal",
                     json=_payload(structure="pr", threshold=0.0, **knobs)).json()
    fptp = client.post("/api/v2/election/temporal",
                       json=_payload(structure="fptp", **knobs)).json()
    assert fptp["enp_votes_final"] < pr["enp_votes_final"]
    assert fptp["enp_votes_final"] < fptp["enp_votes_initial"]


def test_reproducible_by_seed(client: TestClient):
    a = client.post("/api/v2/election/temporal", json=_payload(rounds=6)).json()
    b = client.post("/api/v2/election/temporal", json=_payload(rounds=6)).json()
    assert a == b


def test_zero_dynamics_is_a_fixed_point(client: TestClient):
    """With adaptation and loyalty at 0, every round is identical — the
    dynamics, and only the dynamics, drive the trajectories."""
    body = client.post("/api/v2/election/temporal",
                       json=_payload(rounds=5, adaptation_step=0.0,
                                     loyalty_drift=0.0)).json()
    first = body["rounds"][0]
    for r in body["rounds"][1:]:
        assert {p["name"]: p["seats"] for p in r["parties"]} == \
               {p["name"]: p["seats"] for p in first["parties"]}
        assert r["polarization"] == first["polarization"]


def test_rejects_single_party(client: TestClient):
    res = client.post("/api/v2/election/temporal",
                      json=_payload(parties=SIX_PARTIES[:1]))
    assert res.status_code == 422
