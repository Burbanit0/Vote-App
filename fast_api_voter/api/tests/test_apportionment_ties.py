"""An exact quotient/remainder/score tie used to go to whichever party the
caller's dict or ballot listed first: `dhondt`, `get_dhondt_winners` and
`get_sainte_lague_winners` took the first key `max()` saw at a tied quotient,
`get_largest_remainder_winners`' stable sort kept ties in listing order,
`get_spav_result` broke ties with an explicit `-all_cands.index(c)`, and
theory/workers.py's four divisor-method apportionment functions did the same
`max()`. Quotient ties are not exotic: 100/2 equals 50/1, so any two parties in
a 2:1 vote ratio tie on a seat.

The engine allocators and `dhondt` take an optional keyword-only `rng`. Without
one they behave exactly as before -- polity imports the engine allocators and
passes none, so its seat allocation is untouched. With one, a tie is drawn by
lot among the tied names sorted, matching `_district_winner`. The theory
endpoint has no seed field, so its four functions break a tie by name instead,
as `_hamilton` in the same response always did.
"""
import random

import pytest

import api.domain.election.workers as workers_mod
import api.domain.election.workers_mechanisms as mech_mod
from api.domain.election._helpers import dhondt
from api.domain.election.workers import _coalition_worker, _districts_worker
from api.domain.election.workers_mechanisms import (
    _gerrymander_worker,
    _multiwinner_compare_worker,
    _stv_worker,
)
from api.domain.theory.workers import (
    _adams_m,
    _apportionment_worker,
    _huntington,
    _jefferson,
    _webster,
)
from api.engine.utils.simulation_multiwinner_utils import (
    break_tie,
    get_dhondt_winners,
    get_largest_remainder_winners,
    get_sainte_lague_winners,
    get_spav_result,
)


class TestBreakTie:
    def test_default_is_max_and_keeps_the_first_listed_key(self):
        assert break_tie({"A": 1.0, "B": 1.0, "C": 0.5}) == "A"
        assert break_tie({"B": 1.0, "A": 1.0, "C": 0.5}) == "B"

    def test_default_never_raises_on_a_nan_score(self):
        """`max()` shrugs NaN off; an `==` scan for the top would find no key."""
        assert break_tie({"A": float("nan")}) == "A"
        assert dhondt({"A": float("nan")}, 3) == {"A": 3}

    def test_with_rng_draws_from_the_tied_set_only(self):
        for seed in range(30):
            assert break_tie({"A": 1.0, "B": 1.0, "C": 0.5}, random.Random(seed)) in ("A", "B")

    def test_a_lone_winner_ignores_rng(self):
        assert break_tie({"A": 2.0, "B": 1.0}, random.Random(0)) == "A"

    def test_float_noise_is_still_a_tie_when_drawing(self):
        """0.3/3 is 0.09999999999999999, not 0.1: mathematically tied, but an
        `==` scan would never consult the rng and let the noise pick."""
        assert 0.3 / 3 != 0.1
        picked = {break_tie({"A": 0.3 / 3, "B": 0.1}, random.Random(s)) for s in range(30)}
        assert picked == {"A", "B"}


def _order_independent(fn, votes, *args, seeds=range(20)):
    """`fn(votes, *args, rng=...)` must not depend on `votes`' key order, for
    any seed. Returns the distinct outcomes seen, so callers can also assert
    the tie was real (more than one outcome across seeds)."""
    reversed_votes = dict(reversed(list(votes.items())))
    outcomes = set()
    for seed in seeds:
        r1 = fn(votes, *args, rng=random.Random(seed))
        r2 = fn(reversed_votes, *args, rng=random.Random(seed))
        assert r1 == r2, (seed, r1, r2)
        outcomes.add(tuple(sorted(r1.items())))
    return outcomes


class TestDhondt:
    """A=100, B=50 over 2 seats: round 1 goes to A (100 > 50); round 2 ties
    at 50 (A's second quotient, 100/2, equals B's first, 50/1) -- and it's
    the last seat, so the tie decides the whole result."""

    VOTES = {"A": 100.0, "B": 50.0}
    BOTH = {(("A", 1), ("B", 1)), (("A", 2), ("B", 0))}

    def test_default_keeps_the_first_listed_party(self):
        assert dhondt(self.VOTES, 2) == {"A": 2, "B": 0}
        assert get_dhondt_winners(self.VOTES, 2) == {"A": 2, "B": 0}
        assert get_dhondt_winners(dict(reversed(list(self.VOTES.items()))), 2) == {"B": 1, "A": 1}

    def test_rng_draws_among_the_tied_party_and_is_order_independent(self):
        assert _order_independent(dhondt, self.VOTES, 2) == self.BOTH
        assert _order_independent(get_dhondt_winners, self.VOTES, 2) == self.BOTH

    def test_fractional_shares_tie_too(self):
        """3:1 as shares ties on the third seat: A's 0.3/3 against B's 0.1/1.
        0.3/3 != 0.1 in floats, so this was a tie that `==` could not see."""
        outcomes = _order_independent(get_dhondt_winners, {"A": 0.3, "B": 0.1}, 3)
        assert outcomes == {(("A", 2), ("B", 1)), (("A", 3), ("B", 0))}


class TestSainteLague:
    """A=150, B=50 over 2 seats: round 1 to A; round 2 ties at 50 (A's
    150/3, B's 50/1) for the last seat."""

    VOTES = {"A": 150.0, "B": 50.0}

    def test_default_keeps_the_first_listed_party(self):
        assert get_sainte_lague_winners(self.VOTES, 2) == {"A": 2, "B": 0}

    def test_rng_draws_among_the_tied_party_and_is_order_independent(self):
        outcomes = _order_independent(get_sainte_lague_winners, self.VOTES, 2)
        assert outcomes == {(("A", 1), ("B", 1)), (("A", 2), ("B", 0))}


class TestLargestRemainder:
    """Hare quota 250/2 = 125: nobody gets an automatic seat, so both seats go
    by remainder -- A's is 0.8, B's, C's and D's are an equal 0.4. A is safe;
    the other seat is a three-way tie, more tied parties than seats."""

    VOTES = {"A": 100.0, "B": 50.0, "C": 50.0, "D": 50.0}

    def test_default_keeps_listing_order_at_the_cutoff(self):
        assert get_largest_remainder_winners(self.VOTES, 2) == {"A": 1, "B": 1, "C": 0, "D": 0}

    def test_rng_draws_among_the_cutoff_tied_group(self):
        winners = set()
        for seed in range(30):
            r = get_largest_remainder_winners(self.VOTES, 2, rng=random.Random(seed))
            assert r["A"] == 1  # never tied
            assert r["B"] + r["C"] + r["D"] == 1  # exactly one of the tied trio
            winners |= {p for p in "BCD" if r[p]}
        assert winners == {"B", "C", "D"}

    def test_order_independence(self):
        _order_independent(get_largest_remainder_winners, self.VOTES, 2)

    def test_float_noise_in_a_remainder_is_still_a_tie(self):
        """Three exactly equal 1/3 remainders, but A's is 0.33333333333333326
        in floats, so an exact comparison would never let A win the seat."""
        votes = {"A": 4.0, "B": 1.0, "C": 1.0}
        winners = {
            p for s in range(60)
            for p, n in get_largest_remainder_winners(votes, 2, rng=random.Random(s)).items()
            if n == 1 and p != "A"
        }
        assert winners == {"B", "C"}
        assert any(
            get_largest_remainder_winners(votes, 2, rng=random.Random(s))["A"] == 1
            for s in range(60)
        )

    def test_no_boundary_tie_is_unaffected_by_rng(self):
        assert get_largest_remainder_winners({"A": 100.0, "B": 1.0}, 1) == \
               get_largest_remainder_winners({"A": 100.0, "B": 1.0}, 1, rng=random.Random(0)) == \
               {"A": 1, "B": 0}


class TestSpav:
    """Two ballots approving {A, B} and nothing else: both start round 1
    tied at score 2."""

    BALLOTS = [["A", "B"], ["A", "B"]]

    def test_default_keeps_the_first_listed_candidate(self):
        assert get_spav_result(self.BALLOTS, 1)["elected"] == ["A"]

    def test_rng_draws_among_the_tied_candidates_and_is_order_independent(self):
        reversed_ballots = [list(reversed(b)) for b in self.BALLOTS]
        outcomes = set()
        for seed in range(20):
            r1 = get_spav_result(self.BALLOTS, 1, rng=random.Random(seed))["elected"]
            r2 = get_spav_result(reversed_ballots, 1, rng=random.Random(seed))["elected"]
            assert r1 == r2, seed
            outcomes.add(tuple(r1))
        assert outcomes == {("A",), ("B",)}

    def test_accumulated_weight_noise_is_still_a_tie(self):
        """Round-3 scores of A and B are exactly 11/6, but summed in ballot
        order the floats are 1.833333333333333 and 1.8333333333333333 -- and
        summed in reverse ballot order they are equal. The lot must not depend
        on which."""
        ballots = [["B", "D"], ["A", "B", "C", "E"], ["C", "D"], ["A", "C", "D", "E"],
                   ["B", "D", "E"], ["A", "C", "D"], ["A", "C", "D", "E"], ["C", "D"],
                   ["A", "B", "C", "D"]]
        picks = {}
        for name, bs in (("forward", ballots), ("reversed", ballots[::-1])):
            picks[name] = {
                tuple(get_spav_result(bs, 3, rng=random.Random(s))["elected"]) for s in range(60)
            }
        assert picks["forward"] == picks["reversed"] == {("D", "C", "A"), ("D", "C", "B")}


class TestTheoryDivisorMethods:
    """The four divisor loops break an exact tie by name, whatever order the
    request listed the parties in. Each fixture below is a real, decisive
    tie: the winner of the tied quotient changes the final seat count."""

    CASES = (
        (_jefferson,  {"A": 100, "B": 50}, 2),   # round 2: 100/2 == 50/1
        (_webster,    {"A": 3, "B": 1},    2),   # round 2: 3/3 == 1/1
        (_adams_m,    {"A": 1, "B": 1},    1),   # round 1: equal votes
        (_huntington, {"A": 1, "B": 1},    3),   # last seat: equal votes
    )

    @pytest.mark.parametrize("fn,votes,n", CASES)
    def test_a_tie_goes_to_the_alphabetically_first_party_in_either_order(self, fn, votes, n):
        forward = fn(votes, n)
        backward = fn(dict(reversed(list(votes.items()))), n)
        assert forward == backward
        assert forward["A"] >= forward["B"]
        assert forward["A"] > forward["B"] or votes["A"] == votes["B"] and n % 2 == 1

    def test_the_endpoint_answers_the_same_in_either_party_order(self):
        """Through the worker, including the paradox flags: a tie decided by
        request order used to flip `quota_violation` on 60/30/10 over 5 seats
        (A,B,C gave {A:4,B:1,C:0}, C,B,A gave {A:3,B:2,C:0})."""
        parties = [{"name": "A", "votes": 6000}, {"name": "B", "votes": 3000},
                   {"name": "C", "votes": 1000}]

        def run(ps):
            body, status = _apportionment_worker({"parties": ps, "num_seats": 5})
            assert status == 200
            return {m: (r["seats"], r["quota_violation"], r["alabama_paradox"],
                        r["population_paradox"]) for m, r in body["results"].items()}

        assert run(parties) == run(parties[::-1])


def _spy(monkeypatch, module, name):
    """Record the `rng` each call to `module.name` receives."""
    calls = []
    real = getattr(module, name)

    def wrapper(*args, **kwargs):
        calls.append(kwargs.get("rng"))
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls


def _all_seeded(calls):
    return bool(calls) and all(isinstance(r, random.Random) for r in calls)


class TestWorkersHandTheirAllocatorALot:
    """Every worker that allocates seats must pass a generator -- the default
    is the old first-listed behaviour, which is invisible to mypy and to a
    test that only checks a result. Dropping an `rng=` fails one of these."""

    def test_stv_dhondt_row(self, monkeypatch):
        calls = _spy(monkeypatch, mech_mod, "get_dhondt_winners")
        assert _stv_worker({"num_voters": 60, "num_seats": 2})[1] == 200
        assert _all_seeded(calls)

    def test_multiwinner_compare_dhondt_and_spav(self, monkeypatch):
        dh = _spy(monkeypatch, mech_mod, "get_dhondt_winners")
        sp = _spy(monkeypatch, mech_mod, "get_spav_result")
        assert _multiwinner_compare_worker({"num_voters": 60, "num_seats": 2})[1] == 200
        assert _all_seeded(dh) and _all_seeded(sp)

    def test_gerrymander_national_proportional(self, monkeypatch):
        calls = _spy(monkeypatch, mech_mod, "_dhondt")
        body, status = _gerrymander_worker({
            "num_voters": 60,
            "districts": [
                {"id": 0, "bounds": {"x_min": -1.0, "x_max": 0.0, "y_min": -1.0, "y_max": 1.0}},
                {"id": 1, "bounds": {"x_min": 0.0, "x_max": 1.0, "y_min": -1.0, "y_max": 1.0}},
            ],
        })
        assert status == 200 and _all_seeded(calls)

    def test_districts_proportional_parliament(self, monkeypatch):
        calls = _spy(monkeypatch, workers_mod, "_dhondt")
        assert _districts_worker({})[1] == 200
        assert _all_seeded(calls)

    def test_coalition_seat_allocation(self, monkeypatch):
        calls = _spy(monkeypatch, workers_mod, "_dhondt")
        assert _coalition_worker({"num_voters": 60})[1] == 200
        assert _all_seeded(calls)

    def test_the_lot_is_not_the_draw_that_built_the_electorate(self, monkeypatch):
        """`seed` builds the electorate, so a lot drawn from `Random(seed)`
        replays the first voter's first draw. /stv, /gerrymander and
        /multiwinner_compare use seed + 1, as /adaptive does."""
        calls = _spy(monkeypatch, mech_mod, "get_dhondt_winners")
        _stv_worker({"num_voters": 60, "seed": 5, "num_seats": 2})
        assert calls and calls[0].random() == random.Random(6).random()


def _by_party(body):
    """The D'Hondt row lists only parties with a vote; the reference lists all."""
    row = body["methods"]["dhondt"]["seats"]
    return {c: row.get(c, 0) for c in body["proportional_reference"]}


class TestMultiwinnerCompare:
    def test_the_proportional_reference_is_the_dhondt_row(self):
        """The reference used to be a second D'Hondt run that drew its own lot,
        so at seed 119 the panel printed {Alice:1, Carol:1} beside a reference
        of {Alice:2} for the very same votes."""
        body, status = _multiwinner_compare_worker(
            {"num_voters": 50, "seed": 119, "num_seats": 2}
        )
        assert status == 200
        assert _by_party(body) == body["proportional_reference"]

    @pytest.mark.parametrize("seed", range(40))
    def test_row_and_reference_agree_across_seeds(self, seed):
        body, _ = _multiwinner_compare_worker({"num_voters": 50, "seed": seed, "num_seats": 2})
        assert _by_party(body) == body["proportional_reference"]
