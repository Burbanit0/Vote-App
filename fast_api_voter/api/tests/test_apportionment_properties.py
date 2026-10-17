"""Property-based tests — party-list apportionment.

The oracle is apportionment theory (Balinski & Young; THEORY.md §3.6), not
hand-picked examples:

- every allocator hands out exactly the house size when anyone has votes;
- divisor methods (D'Hondt, Sainte-Laguë) are house monotone: one more seat
  never costs a party a seat (the Alabama paradox cannot happen to them) --
  true by construction of today's greedy loop, kept as a guard on any rewrite;
- D'Hondt satisfies lower quota: a party never gets fewer than the integer part
  of its exact quota, votes × seats / total;
- Hamilton (largest remainder, Hare quota) satisfies quota: a party gets the
  integer part of its exact quota or one more.

Each property holds with and without a tie-break generator (`rng`), since polity
always passes one. Quotas are computed in integers, so the oracle itself
carries no float noise. The election domain keeps its own D'Hondt
(`_helpers.dhondt`: it lists zero-vote parties, and still allocates on NaN or
all-zero votes, where the engine drops or raises); the last test holds it to
the engine's on real counts.
"""
import random
from typing import Optional

from hypothesis import given, strategies as st

from api.domain.election._helpers import dhondt
from api.engine.utils.simulation_multiwinner_utils import (
    get_dhondt_winners,
    get_largest_remainder_winners,
    get_sainte_lague_winners,
)

_PARTIES = ["A", "B", "C", "D", "E", "F"]
_votes = st.lists(st.integers(min_value=0, max_value=100_000), min_size=2, max_size=len(_PARTIES)).filter(
    lambda counts: sum(counts) > 0
).map(lambda counts: dict(zip(_PARTIES, counts)))
_seats = st.integers(min_value=1, max_value=60)
_rng_seeds = st.none() | st.integers(min_value=0, max_value=2**32)


def _rng(seed: Optional[int]) -> Optional[random.Random]:
    return None if seed is None else random.Random(seed)


def _quota_floor(votes: dict[str, int], party: str, seats: int) -> int:
    return votes[party] * seats // sum(votes.values())


@given(_votes, _seats, _rng_seeds)
def test_every_allocator_hands_out_the_whole_house(votes: dict[str, int], seats: int, seed: Optional[int]) -> None:
    for allocate in (get_dhondt_winners, get_sainte_lague_winners, get_largest_remainder_winners):
        assert sum(allocate(votes, seats, rng=_rng(seed)).values()) == seats, allocate.__name__


@given(_votes, _seats)
def test_divisor_methods_are_house_monotone(votes: dict[str, int], seats: int) -> None:
    for allocate in (get_dhondt_winners, get_sainte_lague_winners):
        smaller, larger = allocate(votes, seats), allocate(votes, seats + 1)
        assert all(larger.get(p, 0) >= won for p, won in smaller.items()), allocate.__name__


@given(_votes, _seats, _rng_seeds)
def test_dhondt_satisfies_lower_quota(votes: dict[str, int], seats: int, seed: Optional[int]) -> None:
    won = get_dhondt_winners(votes, seats, rng=_rng(seed))
    assert all(won.get(p, 0) >= _quota_floor(votes, p, seats) for p in votes)


@given(_votes, _seats, _rng_seeds)
def test_hamilton_satisfies_quota(votes: dict[str, int], seats: int, seed: Optional[int]) -> None:
    won = get_largest_remainder_winners(votes, seats, rng=_rng(seed))
    for party in votes:
        assert won.get(party, 0) - _quota_floor(votes, party, seats) in (0, 1), party


@given(_votes, _seats, _rng_seeds)
def test_the_election_domain_dhondt_matches_the_engine(votes: dict[str, int], seats: int, seed: Optional[int]) -> None:
    engine = get_dhondt_winners(votes, seats, rng=_rng(seed))
    domain = dhondt(votes, seats, rng=_rng(seed))
    assert domain == {p: engine.get(p, 0) for p in votes}  # the domain copy also lists zero-vote parties
