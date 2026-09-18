"""Unit tests for Kemeny-Young: the exact algorithm (<= 6 candidates)
enumerates every candidate ordering and picks the one maximizing agreement
with the electorate's pairwise preferences; its first-place candidate wins.
No dedicated test file existed before (PR #157's mutation-testing baseline
found 21 surviving mutants here)."""

import random

from api.engine.utils.simulation_ranked_utils import (
    get_kemeny_young_winner, get_condorcet_winner, kemeny_used_approximation,
    _build_pairwise, _kwik_sort,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_kemeny_young_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head.
    assert get_condorcet_winner(ballots) == "A"
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_resolves_a_top_cycle_via_the_best_agreeing_ranking():
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_uses_the_exact_path_under_the_candidate_cap():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )
    assert kemeny_used_approximation(ballots) is False


def test_kemeny_young_uses_the_approximation_path_over_the_candidate_cap():
    ballots = [list("ABCDEFG")] * 3 + [list("GFEDCBA")] * 2  # 7 candidates > cap
    assert kemeny_used_approximation(ballots) is True


def test_kemeny_young_single_and_empty():
    assert get_kemeny_young_winner([]) is None
    assert get_kemeny_young_winner([["A"]]) == "A"


def test_kemeny_young_approximation_path_actually_runs_kwiksort():
    """kemeny_used_approximation() only checks the candidate-count predicate --
    it never calls get_kemeny_young_winner, so it doesn't exercise _kwik_sort
    itself. This test drives the real approximation path (> 6 candidates,
    the >_KY_EXACT_CAP branch in get_kemeny_young_winner) end to end, which a
    coordinated seven-way sweep found had zero coverage in the non-benchmark
    suite despite the predicate having its own test above."""
    ballots = [list("ABCDEFG")] * 3 + [list("GFEDCBA")] * 2  # 7 candidates > cap
    assert kemeny_used_approximation(ballots) is True

    # 3 ballots A>...>G against 2 ballots G>...>A: A wins every pairwise duel
    # 3-2, so it is the Condorcet winner and Kemeny-Young, being
    # Condorcet-consistent, must elect it. `assert winner in "ABCDEFG"` used to
    # stand here -- a substring test that passes for any single letter, which is
    # how _kwik_sort shipped returning the ranking upside down (this profile
    # returned "G", the unanimous last place).
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_approximation_is_condorcet_consistent_and_deterministic():
    """Above the exact cap the winner still has to be the Condorcet winner when
    one exists (a theorem, not a heuristic), and it must not move between
    identical calls -- _kwik_sort used to pick its pivot from the global
    `random` module, so a seeded caller got different answers."""
    ballots = [list("ABCDEFGH")] * 5 + [list("BACDEFGH")] * 4  # A beats all, 9 ballots
    assert kemeny_used_approximation(ballots) is True
    assert {get_kemeny_young_winner(ballots) for _ in range(25)} == {"A"}


def test_compare_all_methods_registers_kemeny_young():
    names = ["A", "B", "C"]
    matrix = {
        i: {n: float(u) for n, u in zip(names, utils)}
        for i, utils in enumerate(
            [(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3 + [(0.5, 0.0, 1.0)] * 2
        )
    }
    res = compare_all_methods(
        [{"id": vid} for vid in matrix],
        [{"name": n} for n in names],
        [],
        override_utilities=matrix,
    )
    assert "kemeny_young" in res["methods"]
    assert res["methods"]["kemeny_young"]["winner"] in names


def test_the_documented_hash_order_regression():
    """The pinned counterexample for the PYTHONHASHSEED bug, per the repo's
    "a discovered violation gets pinned, not left to the random search" rule.

    These 9 ballots over 7 candidates (> _KY_EXACT_CAP, so KwikSort decides)
    returned four different winners -- C, A, D and G -- across orderings of the
    same candidate list, because the list was `list(cand_set)` and KwikSort's
    pivot is `candidates[len(candidates) // 2]`. Sorted order answers C.

    The literal "C" is deliberate: computing the expectation with _kwik_sort
    would move with any change to _kwik_sort itself, and this profile is the one
    place the >cap path's ranking logic is pinned to a value.
    """
    votes = [
        list(b) for b in (
            "ECGDBFA", "EAFDGBC", "DGAECBF", "FCEDGBA", "GACDEFB",
            "FGCDBEA", "ADCBEGF", "ABCFEGD", "DGABFCE",
        )
    ]
    assert kemeny_used_approximation(votes) is True
    assert get_kemeny_young_winner(votes) == "C"


def test_the_winner_never_depends_on_candidate_discovery_order():
    """Guards the fix itself, at every hash seed.

    One profile cannot do that: whether `list(cand_set)` disagrees with sorted
    order on any given profile depends on the interpreter's hash seed, and on
    ~1 seed in 3 the two agree on the profile above -- including seed 0, the one
    this repo's own tooling pins. So the first version of this test passed with
    the bug restored. Nothing pins PYTHONHASHSEED for pytest, so a single-profile
    assertion is a coin flip, not a guard.

    Sweeping 200 profiles removes the luck: measured against the reverted code,
    52 of these 200 disagree. It also rejects orders that are merely
    deterministic -- reverse-sorted fails 11, first-seen-ballot order fails 54 --
    so what is pinned is `sorted`, not just "some fixed order".
    """
    rng = random.Random(11)
    names = list("ABCDEFG")
    for _ in range(200):
        votes = [rng.sample(names, len(names)) for _ in range(9)]
        candidates = sorted({c for ballot in votes for c in ballot})
        pairwise = _build_pairwise(candidates, votes, False)
        assert get_kemeny_young_winner(votes) == _kwik_sort(candidates, pairwise)[0]
