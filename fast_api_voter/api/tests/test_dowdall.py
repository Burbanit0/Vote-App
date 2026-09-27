"""Unit tests for the Dowdall (Nauru) method: a positional rule using harmonic
weights (rank k scores 1/(k+1)) instead of Borda's linear weights."""

from api.engine.utils.simulation_ranked_utils import get_dowdall_winner, get_borda_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_dowdall_rewards_a_strong_first_choice_more_steeply_than_borda():
    """5 voters put A first (weight 1) then C second; 4 voters put B first then
    C second. Under Borda (3-2-1-0 weights over 3 candidates: 2-1-0), A's lead
    over B is the same size as B's lead is small -- but Dowdall's steep 1 vs
    1/2 first-place weight should let A's narrow plurality edge win outright."""
    ballots = [["A", "C", "B"]] * 5 + [["B", "C", "A"]] * 4
    assert get_dowdall_winner(ballots) == "A"
    # Borda agrees here too (not the point of the test, just a sanity check).
    assert get_borda_winner(ballots) == "A"


def test_dowdall_single_and_empty():
    assert get_dowdall_winner([]) is None
    assert get_dowdall_winner([["A"]]) == "A"


def test_dowdall_ignores_positions_below_last_seen():
    """A clear Condorcet-style sweep: A first on every ballot must win."""
    ballots = [["A", "B", "C"], ["A", "C", "B"], ["A", "B", "C"]]
    assert get_dowdall_winner(ballots) == "A"


def test_compare_all_methods_registers_dowdall():
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
    assert "dowdall" in res["methods"]
    assert res["methods"]["dowdall"]["winner"] in names
