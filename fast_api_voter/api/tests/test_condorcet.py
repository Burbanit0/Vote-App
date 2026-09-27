"""Unit tests for get_condorcet_winner directly. Previously exercised only
indirectly as a helper inside other methods (Black, Benham, Split Cycle,
River...) — mutation testing on this file (PR #157) found this left many of
its own internal mutants undetected, since no test asserted on it in
isolation."""

from api.engine.utils.simulation_ranked_utils import get_condorcet_winner


def test_condorcet_winner_beats_every_other_candidate_head_to_head():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head.
    assert get_condorcet_winner(ballots) == "A"


def test_condorcet_winner_is_none_on_a_top_cycle():
    """Rock-paper-scissors: A>B, B>C, C>A all hold — no candidate beats
    everyone, by construction."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None


def test_condorcet_single_and_empty():
    assert get_condorcet_winner([]) is None
    assert get_condorcet_winner([["A"]]) == "A"
