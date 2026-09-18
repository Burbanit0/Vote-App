"""Unit tests for Kemeny-Young: the exact algorithm (<= 6 candidates)
enumerates every candidate ordering and picks the one maximizing agreement
with the electorate's pairwise preferences; its first-place candidate wins.
No dedicated test file existed before (PR #157's mutation-testing baseline
found 21 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import (
    get_kemeny_young_winner, get_condorcet_winner, kemeny_used_approximation,
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
