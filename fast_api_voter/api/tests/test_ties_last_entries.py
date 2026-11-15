"""The last #926 entries (LISTING_ORDER_TIES.md): two orders that were not ties but followed the
listing, now fixed, and one tie that is by design.

- Hotelling moved its candidates one after another in listing order, each answering the moves
  before it, so reversing the listing changed where the candidates ended up (12 of 12 seeds).
  The order is now drawn by the seeded lot over the names, a new one each round.
- Identity voting bound its three default groups to the first, second and third listed candidates.
  Each now backs the candidate nearest its centre; an exact tie is drawn by the lot.
- The theory page's apportionment comparison breaks a quotient tie by name ON PURPOSE (test_
  apportionment_ties.py pins it, listed both ways), so it is recorded as by design, not changed.
"""
import pytest

from api.domain.election.workers_dynamics import _hotelling_worker, _move_order
from api.domain.theory.workers import _identity_voting_worker, _nearest_candidate
from api.engine.utils import tie_lot

CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob", "x": 0.5, "y": 0.2},
    {"name": "Carol", "x": 0.0, "y": 0.3},
]
LEFT_TO_RIGHT = [
    {"name": "Alice", "x": -0.5, "y": 0.0},
    {"name": "Bob", "x": 0.0, "y": 0.0},
    {"name": "Carol", "x": 0.5, "y": 0.0},
]


# ── Hotelling ───────────────────────────────────────────────────────────────────────────────


def _final_positions(candidates, seed, method="plurality"):
    body, status = _hotelling_worker({
        "candidates": candidates, "seed": seed, "num_voters": 200,
        "method": method, "num_iterations": 10,
    })
    assert status == 200
    return {c["name"]: (c["x"], c["y"]) for c in body["final_positions"]}


@pytest.mark.parametrize("method", ["plurality", "borda", "approval"])
@pytest.mark.parametrize("seed", range(6))
def test_hotelling_ends_in_the_same_place_whatever_order_the_candidates_are_listed_in(seed, method):
    expected = _final_positions(CANDS, seed, method)
    assert _final_positions(CANDS[::-1], seed, method) == expected
    assert _final_positions(CANDS[1:] + CANDS[:1], seed, method) == expected


# Two candidates on the very same point tie for every voter. Plurality draws that tie per voter
# (#665) and approval has none, so both are listing-independent. Borda is not: its ranking is an
# `argsort`, which breaks the tie by column index (an Open entry in LISTING_ORDER_TIES.md).
TWINS = [
    {"name": "Alice", "x": 0.0, "y": 0.0},
    {"name": "Bob", "x": 0.0, "y": 0.0},
    {"name": "Carol", "x": 0.6, "y": 0.3},
]


@pytest.mark.parametrize("method", ["plurality", "approval"])
@pytest.mark.parametrize("seed", range(6))
def test_hotelling_with_two_candidates_on_one_point_does_not_follow_the_listing(seed, method):
    assert _final_positions(TWINS[::-1], seed, method) == _final_positions(TWINS, seed, method)


def test_the_move_order_is_a_lot_over_the_names_not_the_listing():
    names = ["Alice", "Bob", "Carol", "Dana", "Eve"]
    for seed in range(8):
        order = [names[i] for i in _move_order(names, seed)]
        assert sorted(order) == sorted(names)  # everyone moves, once
        shuffled = ["Eve", "Carol", "Alice", "Dana", "Bob"]
        assert [shuffled[i] for i in _move_order(shuffled, seed)] == order
    # It is a lot, not the sorted names: it is not the same order for every seed.
    assert len({tuple(_move_order(names, seed)) for seed in range(16)}) > 1


def test_the_move_order_is_new_each_round():
    names = ["Alice", "Bob", "Carol", "Dana"]
    assert len({tuple(_move_order(names, f"7:{step}")) for step in range(10)}) > 1


def test_the_worker_asks_for_a_new_order_each_round_seeded_with_the_requests_seed(monkeypatch):
    from api.domain.election import workers_dynamics

    asked = []

    def spy(names, seed):
        asked.append(seed)
        return _move_order(names, seed)

    monkeypatch.setattr(workers_dynamics, "_move_order", spy)
    body, _ = _hotelling_worker({"candidates": CANDS, "seed": 9, "num_voters": 200,
                                 "method": "plurality", "num_iterations": 4})
    assert 0 < len(asked) <= 4  # one call per round actually run (at most num_iterations)
    assert asked == [f"9:{step}" for step in range(len(asked))]
    assert body["iterations"]


def test_two_candidates_sharing_a_name_still_each_move_once():
    names = ["Ann", "Bea", "Ann"]
    assert sorted(_move_order(names, 0)) == [0, 1, 2]


# ── Identity voting ─────────────────────────────────────────────────────────────────────────


def _affiliations(candidates, seed=3):
    body, status = _identity_voting_worker({"candidates": candidates, "seed": seed, "num_voters": 300})
    assert status == 200
    return {g["group_name"]: g["affiliation"] for g in body["group_results"]}


def test_each_default_group_backs_the_candidate_nearest_its_centre():
    """Centres -0.3, 0.1, 0.4 against candidates at -0.5, 0, 0.5."""
    assert _affiliations(LEFT_TO_RIGHT) == {"Groupe A": "Alice", "Groupe B": "Bob", "Groupe C": "Carol"}


def test_the_default_groups_do_not_follow_the_listing():
    expected = _affiliations(LEFT_TO_RIGHT)
    assert _affiliations(LEFT_TO_RIGHT[::-1]) == expected
    assert _affiliations(LEFT_TO_RIGHT[1:] + LEFT_TO_RIGHT[:1]) == expected


@pytest.mark.parametrize("seed", range(6))
def test_a_candidate_equally_near_two_candidates_is_drawn_by_lot_not_by_listing(seed):
    """-0.5 and -0.1 are both 0.2 from the first group's centre (-0.3)."""
    pair = [{"name": "Alice", "x": -0.5, "y": 0.0}, {"name": "Bob", "x": -0.1, "y": 0.0}]
    drawn = tie_lot.draw(["Alice", "Bob"], seed)
    assert _nearest_candidate(pair, -0.3, seed) == drawn
    assert _nearest_candidate(pair[::-1], -0.3, seed) == drawn


def test_a_nearer_candidate_is_not_drawn():
    pair = [{"name": "Alice", "x": -0.5, "y": 0.0}, {"name": "Bob", "x": -0.1, "y": 0.0}]
    assert {_nearest_candidate(pair, -0.4, s) for s in range(16)} == {"Alice"}


def test_two_candidates_are_enough_for_the_default_groups():
    """The defaults used to read the third listed candidate, so two candidates raised. (The
    endpoint's schema still asks for three, a contract question: this is the worker.)"""
    assert set(_affiliations(LEFT_TO_RIGHT[:2]).values()) <= {"Alice", "Bob"}
