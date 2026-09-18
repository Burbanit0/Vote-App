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
from math import factorial
import random

import numpy as np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_voting_utils import (
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

    # Explicit opt-in: strategic_vulnerability is off by default now (it cost
    # 99.4% of a request and only two surfaces publish it), and this snapshot
    # exists to pin the FULL report, so it asks for the full report.
    report = compare_all_methods(voters, candidates, issues, compute_strategic=True)

    assert report == snapshot


def test_the_default_report_omits_strategic_vulnerability():
    """The shape every caller that does not opt in now gets. Nothing pinned it
    before, so a site silently losing (or regaining) the 30-second metric was
    invisible to the suite."""
    random.seed(20260911)
    np.random.seed(20260911)
    issues = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, 0, "Alice", "Green"),
        create_candidate(issues, 1, "Bob", "Conservative"),
        create_candidate(issues, 2, "Carol", "Liberal"),
    ]
    voters = [create_voter(issues, i) for i in range(15)]

    off = compare_all_methods(voters, candidates, issues)
    on = compare_all_methods(voters, candidates, issues, compute_strategic=True)

    assert off["methods"], "the default must still run every method"
    assert set(off["methods"]) == set(on["methods"])
    # Winners are unaffected -- the flag governs one metric, not the outcome.
    assert {m: d.get("winner") for m, d in off["methods"].items()} == \
           {m: d.get("winner") for m, d in on["methods"].items()}
    # random_ballot hardcodes its own 0.0 outside the gate, so it is excluded.
    gated = [m for m in off["methods"] if m != "random_ballot"]
    assert all(off["methods"][m].get("strategic_vulnerability") is None for m in gated)
    assert any(on["methods"][m].get("strategic_vulnerability") is not None for m in gated)


def test_strategic_vulnerability_samples_above_the_permutation_cap():
    """Both branches of the permutation budget.

    With 4 candidates 4! = 24 <= the cap, so every permutation is tried
    exhaustively; with 6, 720 > 100 and it samples. The sampled branch is the
    one that used to call `list(permutations(...))` and build 40,320 tuples at
    8 candidates just to keep 100 of them."""
    issues = DEFAULT_ISSUES
    for n_cands, exhaustive in ((4, True), (6, False)):
        random.seed(7)
        np.random.seed(7)
        candidates = [
            create_candidate(issues, i, f"C{i}", "Party") for i in range(n_cands)
        ]
        voters = [create_voter(issues, i) for i in range(20)]
        report = compare_all_methods(voters, candidates, issues, compute_strategic=True)

        assert factorial(n_cands) <= 100 if exhaustive else factorial(n_cands) > 100
        svs = [
            md["strategic_vulnerability"]
            for m, md in report["methods"].items()
            if m != "random_ballot" and md.get("strategic_vulnerability") is not None
        ]
        assert svs, f"no method reported a vulnerability at {n_cands} candidates"
        assert all(0.0 <= v <= 1.0 for v in svs), svs


# ── run_simulation (pure function, no HTTP route) ──



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
