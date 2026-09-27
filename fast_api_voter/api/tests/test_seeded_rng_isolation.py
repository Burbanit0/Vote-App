"""
test_seeded_rng_isolation.py — regression coverage for the RNG-singleton-race
fix (PLAN_SOLIDITE_TECHNIQUE.md addendum, Lot 5), extended to close the
`run_simulation` gaps found by the mandatory `/code-review ultra` pass that
followed it, and extended again (2026-09-12)
to close `simulate_vote()`'s live-path gap, found by a second
`/code-review ultra` pass on that same follow-up.

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
against the pre-fix `run_simulation` (the reseed at the top of the call
simply overwrites whatever happened earlier). The
real race only shows up from interference DURING a call's own sequence of
per-voter/per-candidate draws — exactly what genuine concurrent access looks
like. Reproducing that without real threads/timing (flaky by construction —
the PR's own ad-hoc verification script used threads and was never
committed) means injecting the perturbation as a side effect of the Nth
`create_voter`/`create_candidate` call itself, then checking that voters/
candidates built *after* that point are unaffected.

Confirmed red against the pre-fix `run_simulation` (restoring its pre-fix
content reproduces the failure) and green after.

`TestRunSimulationVoteReproducibility` below is a different shape on
purpose: it calls the SAME seed twice in a row with no interference at all.
That would be a weak test for the create_voter/create_candidate bug above
(a fully-fixed-or-not-at-all reseed at call entry makes plain sequential
calls trivially identical either way — see the previous paragraph) but it is
exactly the right test for `simulate_vote()`: it never reseeds anything
itself, so even two back-to-back calls with zero concurrency and zero
interference exposed the bug directly — no thread, no mid-call patch needed.
"""
import random
from unittest.mock import patch

import numpy as np

import api.domain.election._electorate as electorate_mod
import api.domain.election.election_service as election_service_mod
import api.engine.utils.simulation_voting_utils as svu
from api.engine.constants import DEFAULT_ISSUES


def _perturb_global_rng() -> None:
    """Stand-in for "a concurrent caller touched the shared random/np.random
    singletons" — deterministic, no threads or timing needed.

    Deliberately no save/restore of prior global state (`random.getstate()`/
    `setstate()`, `np.random.get_state()`/`set_state()`): checked (2026-09-12,
    third `/code-review ultra` pass) whether that could leak perturbation
    into a later test. It can't, here — `pytest-randomly` (requirements-dev.txt)
    unconditionally reseeds both `random` and `np.random` in its own
    `pytest_runtest_setup`/`pytest_runtest_call` hooks before every single
    test, function-scoped, with no opt-out configured in this repo (no
    `--randomly-dont-reset-seed`, no `-p no:randomly`). Whatever this leaves
    the globals as is therefore always overwritten before the next test ever
    runs. Restoring state here would be inert, not incorrect — left out to
    avoid implying a real leak risk that isn't there."""
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
    `simulate`, which does `from ...simulation_voting_utils
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


class TestSimulateIsolatedFromMidCallInterference:
    def test_create_voter_draws_are_isolated(self) -> None:
        # build_candidate_from_xy() (election_service's own candidate
        # builder) is purely deterministic from x/y, no RNG at all — only
        # create_voter needs covering here.
        data = {"num_voters": 30, "seed": 7, "candidates": _CAND_SPECS}
        baseline, status0 = election_service_mod.simulate(dict(data))

        with _interference_after_nth_call(election_service_mod, "create_voter", n=10):
            interfered, status1 = election_service_mod.simulate(dict(data))

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


class TestRunSimulationIsolatedFromMidCallInterference:
    """MUST FIX per the code-review-ultra pass: the same unfixed
    `random.seed(seed)`/`np.random.seed(seed)` pattern documented in the
    module docstring above. Only reachable today from
    test_compare_all_methods_snapshot.py, not a live HTTP endpoint, but the
    same defect class in the same file that was supposed to be fully
    migrated.

    Compares `voter` (built by create_voter) and `utilities` (a pure
    function of voter+candidate, no RNG of its own), but deliberately not
    `vote`: `simulate_vote()` used to draw `random.random()` against the bare
    global singleton with no rng parameter, unconditionally, before it even
    looks at the method — that gap (found by a second, later
    `/code-review ultra` pass) is now fixed and covered separately by
    `TestRunSimulationVoteReproducibility` below, which is why this class
    stays scoped to `voter`/`utilities` rather than being widened.
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


class TestRunSimulationVoteReproducibility:
    """Complement (2026-09-12, second `/code-review ultra` pass): plain
    sequential reproducibility check for the `vote` field, which the class
    above deliberately excludes (see its docstring) because `vote` is
    produced by `simulate_vote()`, a separate un-threaded bare-global draw
    that create_voter/create_candidate interference can't exercise.

    Confirmed red against the pre-fix `simulate_vote()` (no `rng` parameter,
    `random.random() > voter["likelihood_to_vote"]` against the bare global):
    two sequential calls with the same seed produced different `vote` values
    for the same voters every time. Green after threading `rng` through
    `simulate_vote()` and `run_simulation()`.
    """

    def test_vote_field_identical_across_two_sequential_calls(self) -> None:
        kwargs = dict(num_voters=30, num_candidates=3, method="plurality", seed=7)
        first = svu.run_simulation(**kwargs)
        second = svu.run_simulation(**kwargs)

        assert [r["vote"] for r in second] == [r["vote"] for r in first]


