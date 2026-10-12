"""Request bodies that every /api/v2 route accepts: one per route that rejects `{}` or is
slow on its defaults (BODIES), and fallbacks tried in order for the others. Then what else
the engine in the browser is asked: refusals, a GET, and the routes no seed fixes.

Plain data, with no pytest import: test_no_global_rng.py and test_browser_engine.py use it,
and so does scripts/browser_engine_answers.py, which the e2e job runs with the runtime
dependencies only (voter-app/tests/e2e/static.setup.ts).
"""

from typing import Any

# A spatial trio: Alice left-ish, Bob right-ish, Carol near the centre.
CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.1},
]

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
BODIES: dict[str, dict[str, Any]] = {
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
FALLBACKS: tuple[dict[str, Any], ...] = ({}, {"candidates": CANDS}, {"candidates": CANDS, "num_voters": 60},
             {"parties": PARTIES})

#: Refused as the server refuses: Pydantic's 422, a worker's own 400 (as many seats as
#: candidates), and a route that does not exist.
REFUSALS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("/api/v2/election/stv", {"candidates": "nobody"}),
    ("/api/v2/election/stv", {"candidates": CANDS[:3], "num_seats": 3, "num_voters": 60}),
    ("/api/v2/election/no-such-route", {}),
)

#: A GET with a query string: the path, then the query.
GET = ("/api/v2/simulations/manipulability",
       "num_candidates=3&num_voters=50&num_trials=5&methods=plurality")

#: Unseeded by design (each one's docstring): only the status and the shape can match.
UNSEEDED = {"/api/v2/simulations/monte-carlo", "/api/v2/simulations/manipulability"}
