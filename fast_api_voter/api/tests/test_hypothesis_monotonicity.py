"""Property-based test — monotonicity.

Monotonicity: improving a winning candidate's position on a ballot (raising
them relative to their neighbour, changing nothing else) must never make them
lose.

Method choice: the prompt that requested this suite named "Plurality,
Approval" as candidates and asked to confirm the set against THEORY.md first.
THEORY.md explicitly confirms monotonicity for Ranked Pairs only (§4bis:
"Méthode de Condorcet, monotone, indépendante des clones") and explicitly
flags Two-Round, IRV, and Coombs as violating it (§2.1) — it does not make an
explicit claim either way for Plurality or Approval. Both are still included
here because their monotonicity is a direct, uncontroversial consequence of
how get_plurality_winner/get_approval_winner are implemented (plain vote
counts that can only go up when a ballot's top-N changes in the candidate's
favour) — not because THEORY.md asserts it. Ranked Pairs is included because
THEORY.md asserts it outright.
"""
from typing import Callable, Optional

from hypothesis import assume, given, settings, strategies as st

from api.engine.utils.simulation_ranked_utils import (
    get_approval_winner,
    get_plurality_winner,
    get_ranked_pairs_winner,
)

_CANDIDATES = ["A", "B", "C", "D"]
_profiles = st.lists(st.permutations(_CANDIDATES), min_size=3, max_size=12)

Rule = Callable[[list[list[str]]], Optional[str]]


def _promote_by_one(votes: list[list[str]], candidate: str) -> Optional[list[list[str]]]:
    """Return `votes` with `candidate` swapped one slot up on the first ballot
    where they aren't already first — nothing else changes. None if no such
    ballot exists (candidate is already first everywhere)."""
    for i, ballot in enumerate(votes):
        pos = ballot.index(candidate)
        if pos > 0:
            promoted = list(ballot)
            promoted[pos - 1], promoted[pos] = promoted[pos], promoted[pos - 1]
            return votes[:i] + [promoted] + votes[i + 1:]
    return None


def _check_monotone(votes: list[list[str]], rule: Rule) -> None:
    winner = rule(votes)
    assume(winner is not None)
    promoted_votes = _promote_by_one(votes, winner)  # type: ignore[arg-type]
    assume(promoted_votes is not None)
    assert rule(promoted_votes) == winner  # type: ignore[arg-type]


@settings(max_examples=200, deadline=None)
@given(_profiles)
def test_plurality_is_monotonic(votes: list[list[str]]) -> None:
    _check_monotone(votes, get_plurality_winner)


@settings(max_examples=200, deadline=None)
@given(_profiles)
def test_approval_is_monotonic(votes: list[list[str]]) -> None:
    _check_monotone(votes, get_approval_winner)


@settings(max_examples=200, deadline=None)
@given(_profiles)
def test_ranked_pairs_is_monotonic(votes: list[list[str]]) -> None:
    _check_monotone(votes, get_ranked_pairs_winner)
