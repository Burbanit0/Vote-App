"""No worker may draw from, or reseed, the process-wide `random` /
`numpy.random` generators.

Workers run in FastAPI's thread pool, so one request reseeding the shared
generators moves another request's stream mid-run: "same seed, same answer"
then holds only while nothing else runs. Each worker seeds its own pair from
the request's seed (`_seeded_rng_pair`); the workers with no seed take a fresh
`unseeded_rng_pair()`.

Three checks, because each catches what the others miss:
  * the per-route guard below fails if a route touches the singletons at all;
  * `test_answer_survives_interference_mid_call` fails if a route's answer
    depends on them, which the guard cannot see once a route is clean;
  * `ruff`'s NPY002 (pyproject.toml) catches the numpy half statically, in code
    no route reaches.

`test_seeded_rng_isolation.py` covers the same property for the engine-level
entry points (`run_simulation`, `_build_base_electorate`, `simulate`).
"""
import random

import numpy as np
import pytest

from api.main import fastapi_app
from api.tests.conftest import CANDS

PARTIES = [{"name": "Gauche", "x": -0.6, "y": 0.0}, {"name": "Centre", "x": 0.0, "y": 0.1},
           {"name": "Vert", "x": -0.2, "y": 0.5}]
PRIMARY_PARTIES = [
    {"name": "L", "ideology_center": -0.5, "primary_voters_pct": 0.3,
     "primary_candidates": [{"name": "L1", "ideology_position": -0.6},
                            {"name": "L2", "ideology_position": -0.3}]},
    {"name": "R", "ideology_center": 0.5, "primary_voters_pct": 0.3,
     "primary_candidates": [{"name": "R1", "ideology_position": 0.6},
                            {"name": "R2", "ideology_position": 0.3}]},
]

#: Routes that reject `{}`, plus small bodies for the four whose defaults made
#: this file 6s slower (the clamp floors keep every loop running).
BODIES = {
    "/api/v1/compare": {"candidates": ["Alice", "Bob", "Carol"], "num_voters": 60},
    "/api/v1/simulate": {"num_voters": 50, "num_candidates": 3},
    "/api/v2/election/affective-polarization": {"candidates": CANDS, "num_voters": 60,
                                                "num_simulations": 5},
    "/api/v2/election/conviction-voting": {
        "proposals": [{"name": "P1", "x": -0.4}, {"name": "P2", "x": 0.4}], "num_voters": 20},
    "/api/v2/election/gerrymander": {
        "candidates": CANDS, "num_voters": 50,
        "districts": [{"id": 0, "bounds": {"x_min": -1.0, "x_max": 0.0, "y_min": -1.0, "y_max": 1.0}},
                      {"id": 1, "bounds": {"x_min": 0.0, "x_max": 1.0, "y_min": -1.0, "y_max": 1.0}}]},
    "/api/v2/election/interpret": {
        "methods": {"plurality": {"winner": "Alice"}, "borda": {"winner": "Bob"}}},
    "/api/v2/election/multiwinner_compare": {"candidates": CANDS, "num_voters": 60, "num_seats": 2},
    "/api/v2/election/polarization": {"candidates": CANDS, "num_voters": 50, "num_simulations": 5},
    "/api/v2/election/power-indices": {
        "parties": [{"name": "A", "seats": 40}, {"name": "B", "seats": 35}, {"name": "C", "seats": 25}]},
    "/api/v2/election/primary": {"parties": PRIMARY_PARTIES, "general_num_voters": 60},
    "/api/v2/election/stv": {"candidates": CANDS, "num_seats": 2, "num_voters": 60},
    "/api/v2/simulations/monte-carlo": {"candidates": CANDS, "num_voters": 50, "num_runs": 5},
    "/api/v2/theory/apportionment": {
        "parties": [{"name": "A", "votes": 100}, {"name": "B", "votes": 80}], "num_seats": 10},
}

#: Tried in order for a route with no entry above: most take defaults once given
#: candidates.
FALLBACKS = ({}, {"candidates": CANDS}, {"candidates": CANDS, "num_voters": 60},
             {"parties": PARTIES})

#: A body per branch of the switches that draw: the default body only ever
#: reaches one arm, so the others would go unguarded.
VARIANTS = [
    ("/api/v2/election/party-dynamics", {"num_voters": 100, "ideology": i}) for i in
    ("polarized", "normal", "random")
] + [
    ("/api/v2/tech/polis", {"candidates": CANDS, "num_participants": 40, "ideology": i}) for i in
    ("polarized", "centrist", "random")
] + [
    ("/api/v2/election/conviction-voting",
     {"proposals": [{"name": "P1", "x": -0.4}, {"name": "P2", "x": 0.4}], "num_voters": 20,
      "conviction_distribution": d})
    for d in ("uniform", "skewed", "whale", "zero_lock")
] + [
    ("/api/v2/election/demographic-turnout", {"candidates": CANDS, "num_voters": 50,
                                              "method": m}) for m in ("plurality", "schulze")
]

#: Frozen so a renamed or added route has to be answered for here, not silently
#: skipped: `>=` would miss both a rename and nine deletions.
EXPECTED_POST_PATHS = frozenset({
    "/api/v1/compare", "/api/v1/simulate",
    "/api/v2/election/abstention", "/api/v2/election/adaptive",
    "/api/v2/election/affective-polarization", "/api/v2/election/assembly",
    "/api/v2/election/assembly-scorecard", "/api/v2/election/ballot-complexity",
    "/api/v2/election/behavioral-biases", "/api/v2/election/campaign-sensitivity",
    "/api/v2/election/cascade", "/api/v2/election/choice-overload",
    "/api/v2/election/coalition", "/api/v2/election/combined-effects",
    "/api/v2/election/compulsory-voting", "/api/v2/election/conviction-voting",
    "/api/v2/election/deliberation", "/api/v2/election/demographic-turnout",
    "/api/v2/election/districts", "/api/v2/election/divergence",
    "/api/v2/election/electoral-fatigue", "/api/v2/election/gerrymander",
    "/api/v2/election/historical-replay", "/api/v2/election/hotelling",
    "/api/v2/election/interpret", "/api/v2/election/issue-voting",
    "/api/v2/election/jury", "/api/v2/election/liquid-democracy",
    "/api/v2/election/multiwinner_compare", "/api/v2/election/nota",
    "/api/v2/election/party-dynamics", "/api/v2/election/polarization",
    "/api/v2/election/power-indices", "/api/v2/election/primary",
    "/api/v2/election/profile-simulate", "/api/v2/election/shy-voter",
    "/api/v2/election/simulate", "/api/v2/election/simulate-pipeline",
    "/api/v2/election/sortition", "/api/v2/election/structural-fairness",
    "/api/v2/election/stv", "/api/v2/simulations/monte-carlo",
    "/api/v2/simulations/vote-steps", "/api/v2/tech/polis",
    "/api/v2/theory/agenda-manipulation", "/api/v2/theory/apportionment",
    "/api/v2/theory/arrow", "/api/v2/theory/assumption-testing",
    "/api/v2/theory/collective-will", "/api/v2/theory/democratic-backsliding",
    "/api/v2/theory/epistocracy", "/api/v2/theory/identity-voting",
    "/api/v2/theory/iia-rate", "/api/v2/theory/intergenerational",
    "/api/v2/theory/judgment-aggregation", "/api/v2/theory/majority-tyranny",
    "/api/v2/theory/manipulation-analysis", "/api/v2/theory/sen-paradox",
})

#: /simulations/manipulability is the only GET that computes; it is also the sole
#: caller of compute_manipulability_index's `rng`.
GET_PATHS = ["/api/v2/simulations/manipulability"]

PATHS = sorted(EXPECTED_POST_PATHS)

#: Seeded routes this change rewired that build their electorate through
#: `create_voter`, which is where the interference below is injected.
#: /party-dynamics, /tech/polis and /theory/agenda-manipulation draw their voters
#: as numpy arrays instead, so only the guard above covers them.
REWIRED = [
    "/api/v2/election/abstention", "/api/v2/election/adaptive",
    "/api/v2/election/behavioral-biases", "/api/v2/election/cascade",
    "/api/v2/election/conviction-voting", "/api/v2/election/demographic-turnout",
    "/api/v2/election/historical-replay", "/api/v2/election/nota",
    "/api/v2/election/shy-voter", "/api/v2/simulations/vote-steps",
    "/api/v2/theory/manipulation-analysis",
]


def _post(client, path, body=None):
    """POST `path`, trying the fallbacks when it has no body of its own."""
    for candidate in (body,) if body is not None else (BODIES[path],) if path in BODIES else FALLBACKS:
        response = client.post(path, json=candidate)
        if response.status_code == 200:
            return response
    return response


def _rng_snapshot():
    random.seed(12345)
    np.random.seed(12345)
    # [1:3] is the MT key AND pos: comparing the key alone goes blind to any
    # draw that does not twist it.
    return random.getstate(), np.random.get_state()[1:3]


def _assert_untouched(path, before):
    py_before, np_before = before
    assert random.getstate() == py_before, f"{path} drew from or reseeded random"
    now = np.random.get_state()[1:3]
    assert (now[0] == np_before[0]).all() and now[1] == np_before[1], \
        f"{path} drew from or reseeded np.random"


def test_the_route_inventory_is_frozen():
    live = {p for p, ops in fastapi_app.openapi()["paths"].items() if "post" in ops and "{" not in p}
    assert live == EXPECTED_POST_PATHS
    assert set(BODIES) <= EXPECTED_POST_PATHS


@pytest.mark.parametrize("path", PATHS)
def test_endpoint_leaves_the_process_wide_rngs_alone(client, path):
    before = _rng_snapshot()
    response = _post(client, path)
    assert response.status_code == 200, response.text
    _assert_untouched(path, before)


@pytest.mark.parametrize("path,body", VARIANTS)
def test_each_branch_of_a_drawing_switch_leaves_them_alone(client, path, body):
    before = _rng_snapshot()
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    _assert_untouched(f"{path} {body}", before)


@pytest.mark.parametrize("path", GET_PATHS)
def test_get_endpoint_leaves_the_process_wide_rngs_alone(client, path):
    before = _rng_snapshot()
    response = client.get(path)
    assert response.status_code == 200, response.text
    _assert_untouched(path, before)


@pytest.mark.parametrize("path", REWIRED)
def test_answer_survives_interference_mid_call(client, monkeypatch, path):
    """The real race: something else draws while this request is mid-run.

    Two sequential calls with one seed always match, even against the old code,
    because each call re-established its state at entry -- see
    test_seeded_rng_isolation.py's own note. So the interference is injected as
    a side effect of the third voter built inside the call.
    """
    import api.domain.election._electorate as electorate
    import api.domain.election.workers_advanced as advanced
    import api.domain.election.workers_behavioral as behavioral
    import api.domain.public as public
    import api.domain.simulations.compare as compare

    clean = _post(client, path)
    assert clean.status_code == 200, clean.text

    calls = {"n": 0}

    def noisy_factory(real):
        def noisy(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 3:                      # a concurrent request, in effect
                random.seed(999)
                np.random.seed(999)
                random.random()
                np.random.random()
            return real(*args, **kwargs)
        return noisy

    for module in (electorate, advanced, behavioral, public, compare):
        if hasattr(module, "create_voter"):
            monkeypatch.setattr(module, "create_voter", noisy_factory(module.create_voter))

    noisy_response = _post(client, path)
    assert noisy_response.status_code == 200, noisy_response.text
    assert calls["n"] > 3, f"{path} built fewer than 3 voters; interference never fired"
    assert noisy_response.json() == clean.json(), f"{path} answer moved when something else drew"
