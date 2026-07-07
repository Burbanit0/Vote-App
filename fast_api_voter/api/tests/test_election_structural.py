"""Tests for POST /api/v2/election/structural-fairness — frontier FC-2.

Acceptance: malapportionment visibly distorts the seat-vote relationship;
cumulative voting visibly lifts minority representation; Penrose equalises
citizen power.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


PARTIES = [
    {"name": "Gauche",  "x": -0.5, "y": -0.1},
    {"name": "Centre",  "x":  0.0, "y":  0.0},
    {"name": "Droite",  "x":  0.5, "y":  0.2},
    {"name": "Marges",  "x":  0.85, "y":  0.75},
]


def _payload(**overrides) -> dict:
    base = {
        "parties": PARTIES,
        "num_voters": 600,
        "ideology": "random",
        "seed": 42,
        "districts": 20,
        "malapportionment": 0.8,
        "at_large_seats": 5,
    }
    base.update(overrides)
    return base


def test_malapportionment_distorts_vote_weight(client: TestClient):
    body = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    m = body["malapportionment"]
    # Unequal districts → unequal population per seat…
    assert m["pop_per_seat_ratio"] > 1.5
    # …and a SMALLER vote share can control the seat majority than under
    # equal districts (the acceptance's visible distortion).
    assert m["min_share_majority_skewed"] < m["min_share_majority_equal"]
    assert m["min_share_majority_skewed"] < 0.5


def test_zero_malapportionment_is_neutral(client: TestClient):
    body = client.post("/api/v2/election/structural-fairness",
                       json=_payload(malapportionment=0.0)).json()
    m = body["malapportionment"]
    assert m["pop_per_seat_ratio"] <= 1.1
    assert abs(m["min_share_majority_skewed"] - m["min_share_majority_equal"]) < 0.01
    assert m["gallagher_skewed"] == m["gallagher_equal"]


def test_efficiency_gap_bounded_and_consistent(client: TestClient):
    body = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    eg = body["efficiency_gap"]
    assert -1.0 <= eg["gap"] <= 1.0
    assert eg["party_a"] != eg["party_b"]
    assert eg["wasted_a"] >= 0 and eg["wasted_b"] >= 0


def test_penrose_equalises_citizen_power(client: TestClient):
    body = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    p = body["penrose"]
    # √-weights equalise the citizen-power proxy exactly; the other schemes
    # leave a strictly larger spread over unequal districts.
    assert p["penrose"] <= 1.05
    assert p["proportional"] > p["penrose"]
    assert p["equal"] > p["penrose"]


def test_cumulative_lifts_minority_representation(client: TestClient):
    body = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    c = body["cumulative"]
    # Bloc voting: the plurality party sweeps every at-large seat.
    assert c["minority_seats_bloc"] == 0
    assert c["seats_bloc"][c["largest_party"]] == c["at_large_seats"]
    # Cumulative voting: cohesive minorities concentrate and win seats.
    assert c["minority_seats_cumulative"] > 0
    assert sum(c["seats_cumulative"].values()) == c["at_large_seats"]


def test_deterministic(client: TestClient):
    a = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    b = client.post("/api/v2/election/structural-fairness", json=_payload()).json()
    assert a == b
