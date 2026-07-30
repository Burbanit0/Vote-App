"""Unit tests for Split Cycle (Holliday & Pacuit, 2021): discard a majority
defeat when it is the weakest link of a majority cycle; a candidate wins iff
no surviving defeat lands on it."""

from api.engine.utils.simulation_ranked_utils import (
    get_split_cycle_winner,
    get_schulze_winner,
    get_ranked_pairs_winner,
    get_condorcet_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_split_cycle_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> no defeat lands on A.
    assert get_condorcet_winner(ballots) == "A"
    assert get_split_cycle_winner(ballots) == "A"


def test_split_cycle_resolves_a_simple_top_cycle():
    # Rock-paper-scissors cycle: margins B>C=7, A>B=5, C>A=1. The weakest
    # link (C>A) is discarded, leaving A undefeated -- same answer as
    # Schulze/Ranked Pairs on this simple 3-candidate cycle.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_split_cycle_winner(ballots) == "A"


def test_split_cycle_can_diverge_from_schulze_and_ranked_pairs():
    """Found by random search: on this 4-candidate cyclic profile, Split
    Cycle's "discard the weakest link of EVERY cycle" rule leaves a
    different candidate undefeated than Schulze's strongest-path or Ranked
    Pairs' single strongest-majorities-first lock order -- a real
    algorithmic difference, not a tie-break artefact."""
    ballots = [
        ["C", "A", "B", "D"],
        ["C", "D", "B", "A"],
        ["B", "A", "D", "C"],
        ["C", "B", "D", "A"],
        ["D", "C", "A", "B"],
        ["B", "D", "C", "A"],
        ["B", "D", "C", "A"],
        ["B", "D", "A", "C"],
        ["B", "A", "D", "C"],
        ["B", "D", "C", "A"],
        ["C", "D", "A", "B"],
        ["A", "B", "C", "D"],
        ["C", "D", "B", "A"],
        ["C", "D", "A", "B"],
        ["D", "C", "B", "A"],
    ]
    assert get_condorcet_winner(ballots) is None
    assert get_schulze_winner(ballots) == "C"
    assert get_ranked_pairs_winner(ballots) == "C"
    assert get_split_cycle_winner(ballots) == "B"


def test_split_cycle_single_and_empty():
    assert get_split_cycle_winner([]) is None
    assert get_split_cycle_winner([["A"]]) == "A"


def test_compare_all_methods_registers_split_cycle():
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
    assert "split_cycle" in res["methods"]
    assert res["methods"]["split_cycle"]["winner"] in names
