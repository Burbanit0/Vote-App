"""Unit tests for the anti-plurality (veto) method: each ballot vetoes its
last-ranked candidate; the candidate vetoed the fewest times wins."""

from api.engine.utils.simulation_ranked_utils import get_anti_plurality_winner
from api.engine.utils.simulation_metrics import compare_all_methods


def test_anti_plurality_elects_the_least_vetoed_candidate():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # last place: C x4, C x3, B x2 → A is never vetoed.
    assert get_anti_plurality_winner(ballots) == "A"


def test_anti_plurality_never_ranked_last_beats_a_narrow_favourite():
    """A polarising candidate can top plurality yet be everyone else's last
    choice — anti-plurality should reject them in favour of a consensus pick."""
    ballots = (
        [["A", "B", "C"]] * 5  # A's base ranks A first, C last
        + [["B", "C", "A"]] * 4  # the rest rank A last
    )
    # A: 5 first-place votes (plurality winner) but vetoed 4 times.
    # B: never vetoed.
    assert get_anti_plurality_winner(ballots) == "B"


def test_anti_plurality_single_and_empty():
    assert get_anti_plurality_winner([]) is None
    assert get_anti_plurality_winner([["A"]]) == "A"


def test_compare_all_methods_registers_anti_plurality():
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
    assert "anti_plurality" in res["methods"]
    assert res["methods"]["anti_plurality"]["winner"] in names
