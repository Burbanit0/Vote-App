"""Snapshot test for compare_all_methods' rich output (Lot 5,
PLAN_SOLIDITE_TECHNIQUE.md).

`compare_all_methods` returns a deeply nested comparison report (one entry
per voting method, each with a winner, regret, satisfaction figures, etc.).
Asserting on it field by field is either incomplete (only check the fields
someone thought to name) or extremely verbose (name every field, every
method, by hand). A snapshot captures the WHOLE structure once, reviewed by
a human at commit time (the diff on any future change is exactly what
changed, not a wall of new assertions to write).

Determinism: create_voter/create_candidate draw from Python's `random` and
numpy's global RNG with no seed parameter of their own, so both are seeded
here before construction -- the same seed always produces the same
electorate, and therefore the same report, which is the whole precondition
for a snapshot being meaningful rather than flaky.
"""
import random

import numpy as np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_voting_utils import (
    apply_social_influence,
    create_candidate,
    create_voter,
    run_simulation,
)


def test_compare_all_methods_snapshot(snapshot):
    random.seed(20260911)
    np.random.seed(20260911)
    issues = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, 0, "Alice", "Green"),
        create_candidate(issues, 1, "Bob", "Conservative"),
        create_candidate(issues, 2, "Carol", "Liberal"),
    ]
    voters = [create_voter(issues, i) for i in range(15)]

    report = compare_all_methods(voters, candidates, issues)

    assert report == snapshot


# ── apply_social_influence / run_simulation (pure functions, no HTTP route) ──

def test_apply_social_influence_is_a_no_op_without_poll_standings_or_candidates():
    """No poll leader can be identified without poll_standings, and no
    candidate position to drift toward without candidates -- both guard
    clauses short-circuit to an (unmutated) copy of the input voters."""
    issues = DEFAULT_ISSUES
    voters = [create_voter(issues, i) for i in range(5)]
    candidate = create_candidate(issues, 0, "Alice", "Green")

    no_poll = apply_social_influence(voters, {}, [candidate])
    no_candidates = apply_social_influence(voters, {"Alice": 1.0}, [])

    for result in (no_poll, no_candidates):
        assert result == voters
        assert result is not voters  # a copy, per the docstring's contract


def test_run_simulation_returns_one_ballot_record_per_voter():
    """run_simulation (the plain single-shot engine helper, distinct from the
    polity run_simulation) builds a fixed party cycle for its candidates and
    returns one {voter, vote, utilities} record per voter, utilities keyed
    by every candidate name."""
    results = run_simulation(num_voters=20, num_candidates=3, method="plurality", seed=42)

    assert len(results) == 20
    expected_candidates = {"Candidate 1", "Candidate 2", "Candidate 3"}
    for record in results:
        assert set(record.keys()) == {"voter", "vote", "utilities"}
        assert set(record["utilities"]) == expected_candidates
