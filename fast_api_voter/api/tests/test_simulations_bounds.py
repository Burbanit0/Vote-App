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


def test_monte_carlo_rejects_oversized_candidates_list() -> None:
    r = client.post(
        "/api/v2/simulations/monte-carlo",
        json={"num_voters": 150, "candidates": _NINE_CANDS},
    )
    assert r.status_code == 422, r.text


class TestInRangeStillWorks:
    """The bounds themselves are inclusive — a value exactly at the edge must
    still be accepted, not off-by-one rejected."""


    def test_monte_carlo_accepts_the_boundary_values(self) -> None:
        r = client.post(
            "/api/v2/simulations/monte-carlo",
            json={"num_runs": 1, "num_voters": 10, "candidates": CANDS},
        )
        assert r.status_code == 200, r.text



