"""Tests for POST /api/v2/election/issue-voting — frontier FB-2.

The bundling paradoxes: the acceptance pins the canonical Ostrogorski
construction — a platform wins the election while the issue-by-issue majority
opposes it on EVERY issue.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_canonical_ostrogorski_paradox(client: TestClient):
    """Platforms A=(+,+,+), B=(−,−,−); five voters such that A wins the
    bundled vote 3–2 while every single issue has a majority for −."""
    res = client.post("/api/v2/election/issue-voting", json={
        "mode": "handcrafted",
        "party_names": ["A", "B"],
        "party_platforms": [[1, 1, 1], [-1, -1, -1]],
        "voter_stances": [
            [1, 1, -1],    # agrees A on 2 issues → votes A
            [1, -1, 1],    # → A
            [-1, 1, 1],    # → A
            [-1, -1, -1],  # → B
            [-1, -1, -1],  # → B
        ],
    })
    assert res.status_code == 200
    body = res.json()
    assert body["bundled_winner"] == "A"
    assert body["divergent_count"] == 3
    assert all(i["divergent"] for i in body["issues"])
    assert all(i["majority"] == -1 for i in body["issues"])
    assert body["ostrogorski_paradox"] is True


def test_aligned_profile_has_no_paradox(client: TestClient):
    """When the winning platform matches every issue majority, nothing diverges."""
    res = client.post("/api/v2/election/issue-voting", json={
        "mode": "handcrafted",
        "party_platforms": [[1, 1], [-1, -1]],
        "voter_stances": [[1, 1], [1, 1], [1, -1], [-1, -1]],
    })
    body = res.json()
    assert body["bundled_winner"] == "P1"
    assert body["divergent_count"] == 0
    assert body["ostrogorski_paradox"] is False


def test_spatial_mode_shape_and_determinism(client: TestClient):
    payload = {
        "mode": "spatial",
        "parties": [
            {"name": "Gauche", "x": -0.5, "y": -0.2},
            {"name": "Centre", "x": 0.0, "y": 0.0},
            {"name": "Droite", "x": 0.5, "y": 0.3},
        ],
        "num_voters": 300,
        "num_issues": 5,
        "seed": 42,
    }
    a = client.post("/api/v2/election/issue-voting", json=payload)
    assert a.status_code == 200
    body = a.json()
    assert body["num_issues"] == 5 and len(body["issues"]) == 5
    # Platforms are ±1 vectors of length K; vote shares sum to 1.
    for p in body["parties"]:
        assert len(p["platform"]) == 5
        assert set(p["platform"]) <= {-1, 1}
    assert abs(sum(p["vote_share"] for p in body["parties"]) - 1.0) < 1e-6
    # Same seed → same result.
    assert client.post("/api/v2/election/issue-voting", json=payload).json() == body


def test_divergence_flags_are_consistent(client: TestClient):
    """divergent ⇔ winner_plank ≠ majority, and the count matches."""
    body = client.post("/api/v2/election/issue-voting", json={
        "mode": "spatial",
        "parties": [{"name": "A", "x": -0.6}, {"name": "B", "x": 0.6}],
        "num_voters": 200,
        "num_issues": 6,
    }).json()
    count = 0
    for i in body["issues"]:
        assert i["divergent"] == (i["winner_plank"] != i["majority"])
        count += i["divergent"]
    assert count == body["divergent_count"]


def test_handcrafted_requires_consistent_widths(client: TestClient):
    res = client.post("/api/v2/election/issue-voting", json={
        "mode": "handcrafted",
        "party_platforms": [[1, 1, 1]],
        "voter_stances": [[1, 1]],  # 2 issues vs 3
    })
    assert res.status_code == 400
