"""Unit tests for River (Heitzig): like Ranked Pairs, but each candidate
accepts at most ONE incoming lock, so the result is a tree rather than a
general acyclic tournament."""

from api.engine.utils.simulation_ranked_utils import (
    get_river_winner,
    get_ranked_pairs_winner,
    get_condorcet_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_river_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> Condorcet winner.
    assert get_condorcet_winner(ballots) == "A"
    assert get_river_winner(ballots) == "A"


def test_river_resolves_a_top_cycle():
    # Same 3-candidate cycle as Ranked Pairs' own test: margins B>C=7 (locked
    # first), A>B=5 (locked), C>A=1 (would close the cycle, skipped). With
    # only 3 candidates and 2 surviving edges, the "one incoming lock" rule
    # never actually has to reject anything here, so River agrees with
    # Ranked Pairs on this particular profile.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_river_winner(ballots) == "A"


def test_river_can_diverge_from_ranked_pairs_when_a_loser_would_take_two_locks():
    """Found by random search: on this 4-candidate cyclic profile, Ranked
    Pairs lets a candidate accept a SECOND incoming lock (no cycle formed),
    while River's one-lock-per-candidate rule forces that edge to be
    dropped -- reshaping the tree enough to change the root."""
    ballots = [
        ["D", "A", "C", "B"],
        ["C", "B", "A", "D"],
        ["B", "C", "D", "A"],
        ["C", "D", "A", "B"],
        ["D", "A", "B", "C"],
        ["D", "B", "C", "A"],
        ["C", "B", "A", "D"],
        ["A", "B", "D", "C"],
        ["D", "C", "A", "B"],
        ["A", "C", "B", "D"],
        ["B", "D", "C", "A"],
    ]
    assert get_condorcet_winner(ballots) is None
    assert get_ranked_pairs_winner(ballots) == "D"
    assert get_river_winner(ballots) == "C"


def test_river_single_and_empty():
    assert get_river_winner([]) is None
    assert get_river_winner([["A"]]) == "A"


def test_compare_all_methods_registers_river():
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
    assert "river" in res["methods"]
    assert res["methods"]["river"]["winner"] in names
