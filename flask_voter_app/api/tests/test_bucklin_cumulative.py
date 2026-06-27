"""Regression test for the Bucklin winner — it must be CUMULATIVE.

Surfaced by the client⇄backend engine-parity harness
(voter-app/src/lib/playgroundVoting.parity.test.ts): the old implementation reset
its counter each round and tallied only the rank-r choice, instead of the running
top-r membership. This pins the corrected, standard behaviour.
"""

from api.engine.utils.simulation_ranked_utils import get_bucklin_winner


def test_bucklin_is_cumulative():
    # 5 voters, no first-round majority. Cumulative top-2 membership: A=3, B=4, C=3
    # → B (the highest over the 2.5 majority). The old reset-per-round logic counted
    # only second choices (B=2, C=2, A=1), reached no majority, and fell through to
    # an arbitrary fallback — i.e. it could NOT return B here.
    profile = [["A", "B", "C"], ["A", "B", "C"], ["B", "C", "A"], ["B", "C", "A"], ["C", "A", "B"]]
    assert get_bucklin_winner(profile) == "B"


def test_bucklin_first_round_majority():
    # An outright first-choice majority still wins immediately.
    profile = [["A", "B", "C"], ["A", "C", "B"], ["A", "B", "C"], ["B", "A", "C"]]
    assert get_bucklin_winner(profile) == "A"


def test_bucklin_empty():
    assert get_bucklin_winner([]) is None
