"""Unit tests for Ranked Pairs (Tideman) and Random Ballot (Gibbard, 1977)."""

from api.engine.utils.simulation_ranked_utils import (
    get_ranked_pairs_winner,
    get_random_ballot_winner,
    random_ballot_probabilities,
)
from api.engine.utils.simulation_metrics import compare_all_methods


# ── Ranked Pairs ────────────────────────────────────────────────────────────

def test_ranked_pairs_elects_condorcet_winner():
    """When a Condorcet winner exists, Ranked Pairs must elect it."""
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head → Condorcet winner.
    assert get_ranked_pairs_winner(ballots) == "A"


def test_ranked_pairs_resolves_a_cycle_by_strongest_margins():
    """In a top-cycle, Ranked Pairs locks the strongest majorities first and
    skips the one that would close the cycle.

    Margins: B>C = 7 (strongest), A>B = 5, C>A = 1 (skipped). Source = A."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    # Sanity: it really is a cycle (no Condorcet winner).
    res = compare_all_methods(
        [{"id": i} for i in range(len(ballots))],
        [{"name": c} for c in ["A", "B", "C"]],
        [],
        override_utilities={
            i: {c: float(len(b) - b.index(c)) for c in b}
            for i, b in enumerate(ballots)
        },
    )
    assert res["condorcet_winner"] is None
    assert get_ranked_pairs_winner(ballots) == "A"


def test_ranked_pairs_single_and_empty():
    assert get_ranked_pairs_winner([]) is None
    assert get_ranked_pairs_winner([["A"]]) == "A"


# ── Random ballot ───────────────────────────────────────────────────────────

def test_random_ballot_probabilities_are_first_preference_shares():
    ballots = [["A", "B"]] * 3 + [["B", "A"]] * 1
    probs = random_ballot_probabilities(ballots)
    assert probs == {"A": 0.75, "B": 0.25}
    assert abs(sum(probs.values()) - 1.0) < 1e-9


def test_random_ballot_modal_winner_and_alpha_tiebreak():
    assert get_random_ballot_winner([["A", "B"]] * 3 + [["B", "A"]]) == "A"
    # Exact tie → alphabetical.
    assert get_random_ballot_winner([["B", "A"], ["A", "B"]]) == "A"
    assert get_random_ballot_winner([]) is None


# ── Wiring into the comparison report ───────────────────────────────────────

def test_compare_all_methods_registers_new_methods():
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
    methods = res["methods"]
    assert "ranked_pairs" in methods
    assert methods["ranked_pairs"]["winner"] in names
    # Random ballot is strategyproof and carries its win-probability map.
    rb = methods["random_ballot"]
    assert rb["strategic_vulnerability"] == 0.0
    assert abs(sum(rb["rb_probabilities"].values()) - 1.0) < 1e-3
