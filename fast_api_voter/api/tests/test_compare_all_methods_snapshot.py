"""Snapshot test for compare_all_methods' rich output (Lot 5,
PLAN_SOLIDITE_TECHNIQUE.md).

`compare_all_methods` returns a deeply nested comparison report (one entry
per voting method, each with a winner, regret, satisfaction figures, etc.).
Asserting on it field by field is either incomplete (only check the fields
someone thought to name) or extremely verbose (name every field, every
method, by hand). A snapshot captures the WHOLE structure once, reviewed by
a human at commit time (the diff on any future change is exactly what
changed, not a wall of new assertions to write).

Determinism: create_voter/create_candidate take a call-scoped RNG pair, so
each test below builds one from a fixed seed via `_seeded_rng_pair` before
construction -- the same seed always produces the same electorate, and
therefore the same report, which is the whole precondition for a snapshot
being meaningful rather than flaky.
"""
from math import factorial
import random

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.demographic_data import _seeded_rng_pair
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.simulation_voting_utils import (
    create_candidate,
    create_voter,
    run_simulation,
)


def test_compare_all_methods_snapshot(snapshot):
    rng, np_rng = _seeded_rng_pair(20260911)
    issues = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, 0, "Alice", "Green", rng=rng),
        create_candidate(issues, 1, "Bob", "Conservative", rng=rng),
        create_candidate(issues, 2, "Carol", "Liberal", rng=rng),
    ]
    voters = [create_voter(issues, i, rng=rng, np_rng=np_rng) for i in range(15)]

    # Explicit opt-in: strategic_vulnerability is off by default now (it cost
    # 99.4% of a request and only two surfaces publish it), and this snapshot
    # exists to pin the FULL report, so it asks for the full report.
    report = compare_all_methods(voters, candidates, issues, compute_strategic=True)

    assert report == snapshot


def test_the_default_report_omits_strategic_vulnerability():
    """The shape every caller that does not opt in now gets. Nothing pinned it
    before, so a site silently losing (or regaining) the 30-second metric was
    invisible to the suite."""
    rng, np_rng = _seeded_rng_pair(20260911)
    issues = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, 0, "Alice", "Green", rng=rng),
        create_candidate(issues, 1, "Bob", "Conservative", rng=rng),
        create_candidate(issues, 2, "Carol", "Liberal", rng=rng),
    ]
    voters = [create_voter(issues, i, rng=rng, np_rng=np_rng) for i in range(15)]

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
        rng, np_rng = _seeded_rng_pair(7)
        candidates = [
            create_candidate(issues, i, f"C{i}", "Party", rng=rng) for i in range(n_cands)
        ]
        voters = [create_voter(issues, i, rng=rng, np_rng=np_rng) for i in range(20)]
        report = compare_all_methods(voters, candidates, issues, compute_strategic=True)

        assert factorial(n_cands) <= 100 if exhaustive else factorial(n_cands) > 100
        svs = [
            md["strategic_vulnerability"]
            for m, md in report["methods"].items()
            if m != "random_ballot" and md.get("strategic_vulnerability") is not None
        ]
        assert svs, f"no method reported a vulnerability at {n_cands} candidates"
        assert all(0.0 <= v <= 1.0 for v in svs), svs


def test_majority_judgment_and_evaluative_can_be_manipulated():
    """Both used to report strategic_vulnerability 0.0 on every electorate: the
    metric re-runs a rule on manipulated ballots, and these two were handed a
    stub returning their sincere winner whatever it was given. The playground's
    Stratégie panel then ranked them the most resistant methods of all.

    The witnesses are counted here with the rules themselves, not through the
    metric: a sampled voter who, bullet-grading one candidate (1.0, everyone
    else 0.0) instead of reporting their utilities, changes the winner to
    someone they prefer. The metric is that count over the sample -- exactly,
    so feeding it the wrong ballots, the wrong rule or a double vote fails."""
    from api.engine.utils.simulation_metrics import _STRATEGIC_SAMPLE
    from api.engine.utils.simulation_score_utils import (
        get_evaluative_winner, get_majority_judgment_winner,
    )

    rng = random.Random(2)
    names = ["C0", "C1", "C2", "C3", "C4"]
    util = {i: {n: round(rng.random(), 3) for n in names} for i in range(21)}
    report = compare_all_methods(
        [{"id": v} for v in util], [{"name": n} for n in names], [],
        override_utilities=util, compute_strategic=True,
    )
    ballots = [util[v].copy() for v in util]

    for rule, method in ((get_majority_judgment_winner, "majority_judgment"),
                         (get_evaluative_winner, "evaluative")):
        sincere = rule(ballots)["winner"]
        manipulators = sum(
            any(
                (w := rule(ballots[:i] + [{n: float(n == pick) for n in names}]
                           + ballots[i + 1:])["winner"])
                and w != sincere and util[i][w] > util[i][sincere]
                for pick in names
            )
            for i in range(_STRATEGIC_SAMPLE)
        )
        assert manipulators, f"{method}: this profile has no manipulation to find"
        assert report["methods"][method]["strategic_vulnerability"] == round(
            manipulators / _STRATEGIC_SAMPLE, 4
        ), method


def test_strategic_vulnerability_does_not_depend_on_the_global_rng():
    """Above 5! permutations the ranked metric samples manipulations. It drew
    them from the process-wide `random`, so the same electorate measured
    differently per process -- Black read 0.8 in one run and 0.7333 in the
    next, same input. Two different global states must now agree."""
    rng = random.Random(8)
    names = [f"C{i}" for i in range(5)]           # 5! = 120 > the 100 cap
    util = {i: {n: round(rng.random(), 3) for n in names} for i in range(21)}

    def run(global_seed):
        random.seed(global_seed)
        report = compare_all_methods(
            [{"id": v} for v in util], [{"name": n} for n in names], [],
            override_utilities=util, compute_strategic=True,
        )
        return {m: md["strategic_vulnerability"] for m, md in report["methods"].items()}

    assert run(1) == run(2)


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
