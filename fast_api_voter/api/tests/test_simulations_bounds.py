"""Property-based test — the /api/v2/simulations request-schema bounds.

BandwagonRequest, MonteCarloRequest and RealElectionRequest are the only
simulation requests carrying the NumVoters/NumRounds/NumRuns Annotated bounds
(api/schemas/simulations.py) — before that PR they were the only three with no
protection at all against an oversized request on a CPU-bound, unauthenticated
endpoint. This fuzzes values just outside each bound and asserts FastAPI
rejects them with 422 *before* the worker ever runs (not a slow 200) — the
test that would have caught the original gap.

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
