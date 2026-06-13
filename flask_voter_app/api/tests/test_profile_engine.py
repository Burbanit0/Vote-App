"""Validation suite for the profile engine (Lab reshape P1).

The rigor foundation: these tests pin the engine to textbook social-choice results,
so "configure everything" never means "compute anything". A handcrafted utility
matrix lets us build exact paradoxes and check the methods reproduce them.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.engine.utils.profile_engine import (
    condorcet_winner,
    cycle_rate,
    gallagher_index,
    handcrafted_profile,
    build_profile,
)
from api.engine.utils.simulation_metrics import compare_all_methods


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _matrix_from_groups(groups, names):
    """Build a utility matrix from (count, utils-tuple) groups, utils aligned to names."""
    matrix, i = {}, 0
    for count, utils in groups:
        for _ in range(count):
            matrix[i] = {names[j]: float(utils[j]) for j in range(len(names))}
            i += 1
    return matrix


def _winners(matrix, names):
    voters = [{"id": vid} for vid in matrix]
    cands = [{"name": n} for n in names]
    return compare_all_methods(voters, cands, [], override_utilities=matrix)


# ── Condorcet cycle (intransitivity) ──────────────────────────────────────────

def test_condorcet_cycle_has_no_winner():
    """The classic 3-voter cycle A>B>C, B>C>A, C>A>B leaves no Condorcet winner."""
    names = ["A", "B", "C"]
    matrix = handcrafted_profile([[1.0, 0.5, 0.0], [0.0, 1.0, 0.5], [0.5, 0.0, 1.0]], names)
    assert condorcet_winner(matrix, names) is None
    assert _winners(matrix, names).get("condorcet_winner") is None


def test_clear_condorcet_winner_is_found():
    """A candidate that beats both others pairwise is the Condorcet winner."""
    names = ["A", "B", "C"]
    # A is every voter's top or second; it beats B and C head-to-head.
    matrix = handcrafted_profile([[1.0, 0.5, 0.0]] * 3 + [[0.8, 0.0, 0.5]] * 2, names)
    assert condorcet_winner(matrix, names) == "A"


# ── Method divergence on a textbook profile ───────────────────────────────────

def test_textbook_irv_diverges_from_plurality():
    """Documented 100-voter profile: plurality elects A, IRV elects C, and the
    pairwise majority is a cycle (no Condorcet winner). Guards IRV/plurality."""
    names = ["A", "B", "C"]
    matrix = _matrix_from_groups(
        [(42, (1.0, 0.5, 0.0)),   # A > B > C
         (26, (0.0, 1.0, 0.5)),   # B > C > A
         (15, (0.5, 0.0, 1.0)),   # C > A > B
         (17, (0.0, 0.5, 1.0))],  # C > B > A
        names,
    )
    res = _winners(matrix, names)
    assert res["methods"]["plurality"]["winner"] == "A"
    assert res["methods"]["irv"]["winner"] == "C"
    assert res["condorcet_winner"] is None


# ── Gallagher disproportionality math ─────────────────────────────────────────

def test_gallagher_index_known_value():
    """vote=[50,30,20]%, seats=[60,30,10]% → diffs [10,0,10] → sqrt(0.5*200) = 10."""
    assert gallagher_index([0.5, 0.3, 0.2], [0.6, 0.3, 0.1]) == 10.0
    # Perfect proportionality → zero.
    assert gallagher_index([0.5, 0.5], [0.5, 0.5]) == 0.0


# ── Paradox rate rises with disorder ──────────────────────────────────────────

def test_impartial_culture_raises_cycle_rate():
    """Impartial Culture over 5 candidates produces Condorcet cycles at a
    measurable rate; a low-dispersion Mallows (high consensus) produces far fewer."""
    names = ["A", "B", "C", "D", "E"]
    ic = cycle_rate("impartial", names, 51, {}, seed=1, replications=200)
    consensual = cycle_rate("mallows", names, 51, {"phi": 0.05}, seed=1, replications=200)
    assert ic > 0.05
    assert consensual < ic


# ── Behaviour transform ───────────────────────────────────────────────────────

def test_strategic_behavior_compresses_to_frontrunners():
    """Under strategic behaviour every voter ranks a frontrunner top or bottom, so
    the two frontrunners capture all first and last places."""
    names = ["A", "B", "C"]
    built = build_profile(
        "spatial",
        [{"name": "A", "x": -0.6, "y": 0.0}, {"name": "B", "x": 0.6, "y": 0.0},
         {"name": "C", "x": 0.0, "y": 0.9}],
        num_voters=200, dims=2, valence=False, behavior="strategic",
        source_params={}, seed=7,
    )
    matrix = built["matrix"]
    tops = {max(u, key=u.get) for u in matrix.values()}
    # The fringe candidate C is never anyone's strategic first choice.
    assert "C" not in tops


# ── Endpoint wiring ───────────────────────────────────────────────────────────

def test_endpoint_spatial_ok(client: TestClient):
    res = client.post("/api/v2/election/profile-simulate", json={
        "source": "spatial",
        "candidates": [{"name": "A", "x": -0.5, "y": 0.0}, {"name": "B", "x": 0.5, "y": 0.0},
                       {"name": "C", "x": 0.0, "y": 0.4}],
        "num_voters": 200, "dims": 2, "behavior": "sincere", "seed": 42,
    })
    assert res.status_code == 200
    body = res.json()
    assert set(body["methods"]) and "cycle_rate" in body
    assert len(body["display_points"]) == 200
    assert body["candidate_points"] is not None


def test_endpoint_handcrafted_cycle(client: TestClient):
    """A handcrafted cycle through the endpoint yields no Condorcet winner."""
    res = client.post("/api/v2/election/profile-simulate", json={
        "source": "handcrafted",
        "candidates": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
        "handcrafted_matrix": [[1.0, 0.5, 0.0], [0.0, 1.0, 0.5], [0.5, 0.0, 1.0]],
    })
    assert res.status_code == 200
    assert res.json()["condorcet_winner"] is None


def test_endpoint_handcrafted_bad_width_rejected(client: TestClient):
    res = client.post("/api/v2/election/profile-simulate", json={
        "source": "handcrafted",
        "candidates": [{"name": "A"}, {"name": "B"}],
        "handcrafted_matrix": [[1.0, 0.0, 0.0]],  # 3 cols vs 2 candidates
    })
    assert res.status_code == 400


# ── Ballot projection (frontier FA-1) ─────────────────────────────────────────

from api.engine.utils.profile_engine import (  # noqa: E402
    project_ballot,
    ballot_metrics,
    compatible_methods,
)


def test_project_choose_one_is_one_hot():
    names = ["A", "B", "C"]
    matrix = handcrafted_profile([[0.9, 0.5, 0.1], [0.2, 0.8, 0.3]], names)
    out = project_ballot(matrix, names, "choose_one")
    assert out[0] == {"A": 1.0, "B": 0.0, "C": 0.0}
    assert out[1] == {"A": 0.0, "B": 1.0, "C": 0.0}


def test_project_truncation_zeroes_below_k():
    names = ["A", "B", "C", "D"]
    matrix = handcrafted_profile([[1.0, 0.7, 0.4, 0.1]], names)
    out = project_ballot(matrix, names, "rank_truncated", truncate_at=2)
    assert out[0]["A"] == 1.0 and out[0]["B"] == 0.5
    assert out[0]["C"] == 0.0 and out[0]["D"] == 0.0


def test_project_score_quantises_to_levels():
    names = ["A", "B"]
    matrix = handcrafted_profile([[0.63, 0.0]], names)
    out = project_ballot(matrix, names, "score", score_levels=3)
    # 3 levels → only {0, 0.5, 1} possible after min-max normalisation.
    assert set(out[0].values()) <= {0.0, 0.5, 1.0}


def test_ballot_metrics_orderings():
    """Expressiveness and load rise together with richer ballots (conventions)."""
    m = 5
    e = {b: ballot_metrics(b, m)["expressiveness"] for b in
         ("choose_one", "rank_truncated", "rank_full", "score")}
    l_ = {b: ballot_metrics(b, m)["cognitive_load"] for b in
          ("choose_one", "rank_full", "cumulative")}
    assert e["choose_one"] < e["rank_truncated"] < e["rank_full"]
    assert l_["choose_one"] < l_["rank_full"] <= l_["cumulative"]


def test_compatibility_whitelists():
    assert compatible_methods("choose_one") == {"plurality", "two_round"}
    assert "borda" in compatible_methods("rank_truncated")
    assert "star_voting" not in compatible_methods("rank_full")
    assert compatible_methods("approve") == {"approval"}


def test_endpoint_truncation_flips_a_winner(client: TestClient):
    """Headline demo: same counting rules, truncated ballots → different winner.

    On the textbook 100-voter profile, rank_truncated k=1 collapses every
    ranking to a bullet vote: IRV (winner C under full information) degrades
    to plurality behaviour (winner A) — a reported winner flip.
    """
    base = {
        "source": "handcrafted",
        "candidates": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
        "handcrafted_matrix":
            [[1.0, 0.5, 0.0]] * 42 + [[0.0, 1.0, 0.5]] * 26
            + [[0.5, 0.0, 1.0]] * 15 + [[0.0, 0.5, 1.0]] * 17,
    }
    full = client.post("/api/v2/election/profile-simulate", json=base).json()
    trunc = client.post("/api/v2/election/profile-simulate",
                        json={**base, "ballot": {"type": "rank_truncated",
                                                 "truncate_at": 1}}).json()
    assert full["methods"]["irv"]["winner"] == "C"
    assert trunc["methods"]["irv"]["winner"] == "A"
    assert "irv" in trunc["winner_flips"]
    # Cardinal methods cannot run on a ranked ballot — excluded and reported.
    assert "star_voting" in trunc["incompatible_methods"]
    assert "star_voting" not in trunc["methods"]
    # Read-outs present and ordered.
    assert 0 <= trunc["ballot_expressiveness"] < full["ballot_expressiveness"] <= 1
    assert set(trunc["sample_ballot"]) == {"A", "B", "C"}


def test_endpoint_full_ballot_reports_no_flips(client: TestClient):
    res = client.post("/api/v2/election/profile-simulate", json={
        "source": "spatial",
        "candidates": [{"name": "A", "x": -0.5}, {"name": "B", "x": 0.5}],
        "num_voters": 100,
    }).json()
    assert res["ballot_type"] == "full"
    assert res["winner_flips"] == []
    assert res["incompatible_methods"] == []
