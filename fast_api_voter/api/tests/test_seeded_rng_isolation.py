"""
test_seeded_rng_isolation.py — regression coverage for the RNG-singleton-race
fix (PLAN_SOLIDITE_TECHNIQUE.md addendum, Lot 5), extended to close the
`run_bandwagon_simulation`/`run_simulation` gaps found by the mandatory
`/code-review ultra` pass that followed it.

The bug: several entry points used to "seed" the electorate by calling
`random.seed(seed)`/`np.random.seed(seed)` once, then drawing
`create_voter`/`create_candidate` values from the shared, process-wide
`random`/`np.random` singletons. "Same seed -> same result" held only if
nothing else in the process touched those singletons WHILE this call's own
sequence of draws was still in progress — false under concurrent access (a
second request, a background worker, even another seeded call racing the
same process). The fix threads a call-scoped local
`random.Random`/`np.random.RandomState` pair through `create_voter`/
`create_candidate` instead, so nothing outside the call can perturb its
draws.

Why this test injects interference *mid-call* rather than *between* two
sequential calls: every affected entry point takes its own `seed` and (fixed
or not) re-establishes its RNG state fully at call entry, so two sequential
calls with the same seed are ALWAYS identical no matter what happens
strictly *before* the second call starts — confirmed empirically: a naive
"perturb the globals, then call again" version of this test stays green even
against the pre-fix `run_bandwagon_simulation`/`run_simulation` (the reseed
at the top of the call simply overwrites whatever happened earlier). The
real race only shows up from interference DURING a call's own sequence of
per-voter/per-candidate draws — exactly what genuine concurrent access looks
like. Reproducing that without real threads/timing (flaky by construction —
the PR's own ad-hoc verification script used threads and was never
committed) means injecting the perturbation as a side effect of the Nth
`create_voter`/`create_candidate` call itself, then checking that voters/
candidates built *after* that point are unaffected.

Confirmed red against the pre-fix `run_bandwagon_simulation`/`run_simulation`
(restoring their pre-fix content reproduces the failure) and green after.
"""
import random
from unittest.mock import patch

import numpy as np

import api.domain.election._electorate as electorate_mod
import api.domain.election.election_service as election_service_mod
import api.domain.export as export_mod
import api.engine.utils.simulation_voting_utils as svu
from api.engine.constants import DEFAULT_ISSUES


def _perturb_global_rng() -> None:
    """Stand-in for "a concurrent caller touched the shared random/np.random
    singletons" — deterministic, no threads or timing needed."""
    random.seed(20260913)
    for _ in range(37):
        random.random()
    np.random.seed(20260913)
    for _ in range(41):
        np.random.random()


def _interference_after_nth_call(target_module: object, attr_name: str, n: int):
    """`mock.patch.object(...)` context manager that wraps
    `target_module.attr_name` so that, right after its Nth invocation
    returns, it also perturbs the global random/np.random singletons —
    simulating "a concurrent caller's own draws landed in between two draws
    this call was making," the actual precondition for this bug class.

    `target_module` must be the module that *calls* `attr_name` (mock's
    "patch where it's used, not where it's defined" rule) — e.g. for
    `ElectionService.simulate`, which does `from ...simulation_voting_utils
    import create_voter`, that's `election_service_mod` itself, not
    `simulation_voting_utils`.
    """
    real_fn = getattr(target_module, attr_name)
    state = {"calls": 0}

    def wrapper(*args: object, **kwargs: object) -> object:
        result = real_fn(*args, **kwargs)
        state["calls"] += 1
        if state["calls"] == n:
            _perturb_global_rng()
        return result

    return patch.object(target_module, attr_name, side_effect=wrapper)


_CAND_SPECS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob", "x": 0.5, "y": 0.2},
    {"name": "Carol", "x": 0.0, "y": 0.3},
]


class TestElectionServiceSimulateIsolatedFromMidCallInterference:
    def test_create_voter_draws_are_isolated(self) -> None:
        # build_candidate_from_xy() (election_service's own candidate
        # builder) is purely deterministic from x/y, no RNG at all — only
        # create_voter needs covering here.
        data = {"num_voters": 30, "seed": 7, "candidates": _CAND_SPECS}
        baseline, status0 = election_service_mod.ElectionService.simulate(dict(data))

        with _interference_after_nth_call(election_service_mod, "create_voter", n=10):
            interfered, status1 = election_service_mod.ElectionService.simulate(dict(data))

        assert status0 == 200
        assert status1 == 200
        assert interfered["voters_snapshot"] == baseline["voters_snapshot"]
        assert interfered["methods"] == baseline["methods"]


class TestBuildBaseElectorateIsolatedFromMidCallInterference:
    def test_create_voter_draws_are_isolated(self) -> None:
        args = (_CAND_SPECS, 30, "random", 7, DEFAULT_ISSUES)
        baseline = electorate_mod._build_base_electorate(*args)

        with _interference_after_nth_call(electorate_mod, "create_voter", n=10):
            interfered = electorate_mod._build_base_electorate(*args)

        assert interfered == baseline


class TestRunBandwagonSimulationIsolatedFromMidCallInterference:
    """MUST FIX per the code-review-ultra pass: this function used to
    `random.seed(seed); np.random.seed(seed)` and then call
    `create_voter`/`create_candidate` with no `rng`/`np_rng`, reachable live
    via POST /simulations/bandwagon (`_bandwagon_worker` forwards a
    user-supplied seed straight through).

    `num_rounds=0` throughout: round 0 (the sincere baseline, computed
    directly from the freshly-built electorate) is what create_voter/
    create_candidate feed. Rounds 1+ additionally call
    `apply_social_influence()`, which draws from the bare global
    `random.uniform()` with no rng parameter of its own — a separate,
    narrower, already-disclosed gap (same family as `calculate_utility`'s
    turnout gate, see PLAN_SOLIDITE_TECHNIQUE.md), not the
    create_voter/create_candidate threading this test locks in.
    """

    def test_create_voter_draws_are_isolated(self) -> None:
        kwargs = dict(num_voters=30, num_rounds=0, seed=7)
        baseline = svu.run_bandwagon_simulation(**kwargs)

        with _interference_after_nth_call(svu, "create_voter", n=10):
            interfered = svu.run_bandwagon_simulation(**kwargs)

        assert interfered["rounds"][0] == baseline["rounds"][0]

    def test_create_candidate_draws_are_isolated(self) -> None:
        """`candidates=None` (the default) is the branch that calls
        create_candidate internally — interfere after the 2nd of 3."""
        kwargs = dict(num_voters=10, num_rounds=0, seed=7)
        baseline = svu.run_bandwagon_simulation(**kwargs)

        with _interference_after_nth_call(svu, "create_candidate", n=2):
            interfered = svu.run_bandwagon_simulation(**kwargs)

        assert interfered["rounds"][0] == baseline["rounds"][0]


class TestRunSimulationIsolatedFromMidCallInterference:
    """MUST FIX per the code-review-ultra pass: same unfixed
    `random.seed(seed)`/`np.random.seed(seed)` pattern as
    run_bandwagon_simulation, in the same file. Only reachable today from
    test_compare_all_methods_snapshot.py, not a live HTTP endpoint, but the
    same defect class in the same file that was supposed to be fully
    migrated.

    Compares `voter` (built by create_voter) and `utilities` (a pure
    function of voter+candidate, no RNG of its own), but deliberately not
    `vote`: `simulate_vote()` itself draws `random.random()` against the
    bare global singleton with no rng parameter, unconditionally, before it
    even looks at the method — a separate, narrower, already-disclosed gap
    (same family as `calculate_utility`'s turnout gate), not what this test
    locks in.
    """

    def test_create_voter_draws_are_isolated(self) -> None:
        kwargs = dict(num_voters=30, num_candidates=3, method="plurality", seed=7)
        baseline = svu.run_simulation(**kwargs)

        with _interference_after_nth_call(svu, "create_voter", n=10):
            interfered = svu.run_simulation(**kwargs)

        assert [r["voter"] for r in interfered] == [r["voter"] for r in baseline]
        assert [r["utilities"] for r in interfered] == [r["utilities"] for r in baseline]

    def test_create_candidate_draws_are_isolated(self) -> None:
        """Voters are built before candidates in run_simulation, so a
        create_candidate interference point can never affect `voter` dicts
        (already fully constructed by then) — only `utilities` (computed
        against every candidate) can show it."""
        kwargs = dict(num_voters=5, num_candidates=4, method="plurality", seed=7)
        baseline = svu.run_simulation(**kwargs)

        with _interference_after_nth_call(svu, "create_candidate", n=2):
            interfered = svu.run_simulation(**kwargs)

        assert [r["utilities"] for r in interfered] == [r["utilities"] for r in baseline]


class TestGenerateRowsIsolatedFromMidCallInterference:
    def test_create_voter_draws_are_isolated(self) -> None:
        kwargs = dict(num_scenarios=1, num_candidates=3, num_voters=30, seed=7)
        baseline = export_mod._generate_rows(**kwargs)

        with _interference_after_nth_call(export_mod, "create_voter", n=10):
            interfered = export_mod._generate_rows(**kwargs)

        assert interfered == baseline

    def test_create_candidate_draws_are_isolated(self) -> None:
        kwargs = dict(num_scenarios=1, num_candidates=6, num_voters=10, seed=7)
        baseline = export_mod._generate_rows(**kwargs)

        with _interference_after_nth_call(export_mod, "create_candidate", n=2):
            interfered = export_mod._generate_rows(**kwargs)

        assert interfered == baseline
