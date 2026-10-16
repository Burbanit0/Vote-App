"""Property-based tests — party-list apportionment.

The oracle is apportionment theory (Balinski & Young; THEORY.md §3.6), not
hand-picked examples:

- every allocator hands out exactly the house size when anyone has votes;
- divisor methods (D'Hondt, Sainte-Laguë) are house monotone: one more seat
  never costs a party a seat (the Alabama paradox cannot happen to them);
- D'Hondt satisfies lower quota: a party never gets fewer than the integer part
  of its exact quota, votes × seats / total;
- Hamilton (largest remainder, Hare quota) satisfies quota: a party gets the
  integer part of its exact quota or one more.

Quotas are computed in integers, so the oracle itself carries no float noise.
The election domain keeps its own D'Hondt (`_helpers.dhondt`); the last test
holds it to the engine's.
"""
import random

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


def _quota_floor(votes: dict[str, int], party: str, seats: int) -> int:
    return votes[party] * seats // sum(votes.values())


@given(_votes, _seats)
def test_every_allocator_hands_out_the_whole_house(votes: dict[str, int], seats: int) -> None:
    for allocate in (get_dhondt_winners, get_sainte_lague_winners, get_largest_remainder_winners):
        assert sum(allocate(dict(votes), seats).values()) == seats, allocate.__name__


@given(_votes, _seats)
def test_divisor_methods_are_house_monotone(votes: dict[str, int], seats: int) -> None:
    for allocate in (get_dhondt_winners, get_sainte_lague_winners):
        smaller, larger = allocate(dict(votes), seats), allocate(dict(votes), seats + 1)
        assert all(larger.get(p, 0) >= won for p, won in smaller.items()), allocate.__name__


@given(_votes, _seats)
def test_dhondt_satisfies_lower_quota(votes: dict[str, int], seats: int) -> None:
    won = get_dhondt_winners(dict(votes), seats)
    assert all(won.get(p, 0) >= _quota_floor(votes, p, seats) for p in votes)


@given(_votes, _seats)
def test_hamilton_satisfies_quota(votes: dict[str, int], seats: int) -> None:
    won = get_largest_remainder_winners(dict(votes), seats, quota="hare")
    for party in votes:
        assert won.get(party, 0) - _quota_floor(votes, party, seats) in (0, 1), party


@given(_votes, _seats, st.integers(min_value=0, max_value=2**32))
def test_the_election_domain_dhondt_matches_the_engine(votes: dict[str, int], seats: int, seed: int) -> None:
    engine = get_dhondt_winners(dict(votes), seats, rng=random.Random(seed))
    domain = dhondt(dict(votes), seats, rng=random.Random(seed))
    assert domain == {p: engine.get(p, 0) for p in votes}  # the domain copy also lists zero-vote parties
