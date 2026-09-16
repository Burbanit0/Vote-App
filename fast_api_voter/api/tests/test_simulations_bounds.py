"""Property-based test — the /api/v2/simulations request-schema bounds.

Originally covered BandwagonRequest, MonteCarloRequest and RealElectionRequest
— the only three requests carrying the NumVoters/NumRounds/NumRuns Annotated
bounds (api/schemas/simulations.py) when this file was written. Extended
(PLAN_SURFACE_EXTERIEURE.md §2.A) to cover the remaining 23 previously-bare
int/List fields across every other request in that module, once a full audit
found each was either unbounded end-to-end or only clamped ad-hoc inside its
worker, with no schema-level rejection. This fuzzes values just outside each
bound and asserts FastAPI rejects them with 422 *before* the worker ever runs
(not a slow 200) — the test that would have caught the original gap.

max_examples stays modest deliberately: /api/v2/simulations now sits behind
check_v2_rate_limit (120/minute per path, api/core/ratelimit.py) — a wide-open
hypothesis budget hitting the same path repeatedly within one test function
would trip it, which is exactly the class of self-inflicted flake found (and
fixed) in the v2 rate-limit rollout.
"""
from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient

from api.main import app

CANDS = ["Alice", "Bob", "Charlie"]

client = TestClient(app)

_out_of_range_voters = st.one_of(st.integers(max_value=9), st.integers(min_value=1001))
_out_of_range_rounds = st.one_of(st.integers(max_value=0), st.integers(min_value=11))
_out_of_range_runs = st.one_of(st.integers(max_value=0), st.integers(min_value=501))
_out_of_range_candidates = st.one_of(st.integers(max_value=1), st.integers(min_value=9))
_out_of_range_days = st.one_of(st.integers(max_value=0), st.integers(min_value=91))
_out_of_range_seats = st.one_of(st.integers(max_value=0), st.integers(min_value=1001))
_out_of_range_contagion_rounds = st.one_of(st.integers(max_value=0), st.integers(min_value=51))
_NINE_CANDS = [f"C{i}" for i in range(9)]
_ELEVEN_VALUES = list(range(11))


@settings(max_examples=15, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_bandwagon_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/bandwagon",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_rounds=_out_of_range_rounds)
def test_bandwagon_rejects_out_of_range_num_rounds(num_rounds: int) -> None:
    r = client.post(
        "/api/v2/simulations/bandwagon",
        json={"num_voters": 300, "num_rounds": num_rounds, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_monte_carlo_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/monte-carlo",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_runs=_out_of_range_runs)
def test_monte_carlo_rejects_out_of_range_num_runs(num_runs: int) -> None:
    r = client.post(
        "/api/v2/simulations/monte-carlo",
        json={"num_runs": num_runs, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_real_election_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/real-election",
        json={"election_name": "france2002", "num_voters": num_voters},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_simulate_voters_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post("/api/v2/simulations/simulate_voters", json={"num_voters": num_voters})
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_candidates=_out_of_range_candidates)
def test_simulate_candidates_rejects_out_of_range_num_candidates(num_candidates: int) -> None:
    r = client.post(
        "/api/v2/simulations/simulate_candidates", json={"num_candidates": num_candidates},
    )
    assert r.status_code == 422, r.text


def test_closest_candidate_rejects_oversized_candidates_list() -> None:
    r = client.post(
        "/api/v2/simulations/get_closest_candidate",
        json={"voters": [], "candidates": _NINE_CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_candidates=_out_of_range_candidates)
def test_campaign_rejects_out_of_range_num_candidates(num_candidates: int) -> None:
    r = client.post(
        "/api/v2/simulations/campaign", json={"num_candidates": num_candidates},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_campaign_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post("/api/v2/simulations/campaign", json={"num_voters": num_voters})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_days=_out_of_range_days)
def test_campaign_rejects_out_of_range_num_days(num_days: int) -> None:
    r = client.post("/api/v2/simulations/campaign", json={"num_days": num_days})
    assert r.status_code == 422, r.text


@settings(max_examples=15, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_compare_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/compare", json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


def test_compare_rejects_oversized_candidates_list() -> None:
    r = client.post("/api/v2/simulations/compare", json={"candidates": _NINE_CANDS})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_strategic_impact_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/strategic-impact",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


def test_strategic_impact_rejects_oversized_candidates_list() -> None:
    r = client.post("/api/v2/simulations/strategic-impact", json={"candidates": _NINE_CANDS})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_condorcet_matrix_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/condorcet-matrix",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


def test_condorcet_matrix_rejects_oversized_candidates_list() -> None:
    r = client.post("/api/v2/simulations/condorcet-matrix", json={"candidates": _NINE_CANDS})
    assert r.status_code == 422, r.text


def test_sensitivity_rejects_oversized_values_list() -> None:
    r = client.post("/api/v2/simulations/sensitivity", json={"values": _ELEVEN_VALUES})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_arrow_criteria_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/arrow-criteria",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


def test_arrow_criteria_rejects_oversized_candidates_list() -> None:
    r = client.post("/api/v2/simulations/arrow-criteria", json={"candidates": _NINE_CANDS})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_vote_steps_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post(
        "/api/v2/simulations/vote-steps",
        json={"num_voters": num_voters, "candidates": CANDS},
    )
    assert r.status_code == 422, r.text


def test_vote_steps_rejects_oversized_candidates_list() -> None:
    r = client.post("/api/v2/simulations/vote-steps", json={"candidates": _NINE_CANDS})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_ideology_map_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post("/api/v2/simulations/ideology-map", json={"num_voters": num_voters})
    assert r.status_code == 422, r.text


def test_bandwagon_rejects_oversized_candidates_list() -> None:
    r = client.post(
        "/api/v2/simulations/bandwagon",
        json={"num_voters": 300, "candidates": _NINE_CANDS},
    )
    assert r.status_code == 422, r.text


def test_monte_carlo_rejects_oversized_candidates_list() -> None:
    r = client.post(
        "/api/v2/simulations/monte-carlo",
        json={"num_voters": 150, "candidates": _NINE_CANDS},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_seats=_out_of_range_seats)
def test_multiwinner_rejects_out_of_range_num_seats(num_seats: int) -> None:
    r = client.post(
        "/api/v2/simulations/multiwinner",
        json={"party_votes": {"Green": 40, "Blue": 60}, "num_seats": num_seats},
    )
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_voters=_out_of_range_voters)
def test_blank_contagion_rejects_out_of_range_num_voters(num_voters: int) -> None:
    r = client.post("/api/v2/simulations/blank-contagion", json={"num_voters": num_voters})
    assert r.status_code == 422, r.text


@settings(max_examples=10, deadline=None)
@given(num_rounds=_out_of_range_contagion_rounds)
def test_blank_contagion_rejects_out_of_range_num_rounds(num_rounds: int) -> None:
    r = client.post("/api/v2/simulations/blank-contagion", json={"num_rounds": num_rounds})
    assert r.status_code == 422, r.text


class TestInRangeStillWorks:
    """The bounds themselves are inclusive — a value exactly at the edge must
    still be accepted, not off-by-one rejected."""

    def test_bandwagon_accepts_the_boundary_values(self) -> None:
        for num_voters in (10, 1000):
            r = client.post(
                "/api/v2/simulations/bandwagon",
                json={"num_voters": num_voters, "num_rounds": 1, "candidates": CANDS},
            )
            assert r.status_code == 200, r.text

    def test_monte_carlo_accepts_the_boundary_values(self) -> None:
        r = client.post(
            "/api/v2/simulations/monte-carlo",
            json={"num_runs": 1, "num_voters": 10, "candidates": CANDS},
        )
        assert r.status_code == 200, r.text

    def test_compare_accepts_the_boundary_values(self) -> None:
        for num_voters in (10, 1000):
            r = client.post(
                "/api/v2/simulations/compare",
                json={"num_voters": num_voters, "candidates": CANDS},
            )
            assert r.status_code == 200, r.text

    def test_multiwinner_accepts_the_boundary_values(self) -> None:
        for num_seats in (1, 1000):
            r = client.post(
                "/api/v2/simulations/multiwinner",
                json={"party_votes": {"Green": 40, "Blue": 60}, "num_seats": num_seats},
            )
            assert r.status_code == 200, r.text

    def test_blank_contagion_accepts_the_boundary_values(self) -> None:
        for num_rounds in (1, 50):
            r = client.post(
                "/api/v2/simulations/blank-contagion",
                json={"num_voters": 300, "num_rounds": num_rounds},
            )
            assert r.status_code == 200, r.text
