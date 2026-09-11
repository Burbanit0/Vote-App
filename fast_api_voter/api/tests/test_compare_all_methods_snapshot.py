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
from api.engine.utils.simulation_voting_utils import create_candidate, create_voter


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
