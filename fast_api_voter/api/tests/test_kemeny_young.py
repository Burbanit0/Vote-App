"""Unit tests for Kemeny-Young: the exact algorithm (<= 6 candidates)
enumerates every candidate ordering and picks the one maximizing agreement
with the electorate's pairwise preferences; its first-place candidate wins.
No dedicated test file existed before (PR #157's mutation-testing baseline
found 21 surviving mutants here)."""

from api.engine.utils.simulation_ranked_utils import get_kemeny_young_winner, get_condorcet_winner
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
    get_kemeny_young_winner(ballots)
    assert get_kemeny_young_winner.was_approx is False


def test_kemeny_young_single_and_empty():
    assert get_kemeny_young_winner([]) is None
    assert get_kemeny_young_winner([["A"]]) == "A"


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
