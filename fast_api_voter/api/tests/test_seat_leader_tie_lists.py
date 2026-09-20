"""A party tied on seats is not the leader, and a tie has no leader at all.

/districts returned one `fptp_winner` and one `proportional_winner`, each
`max()` over a seat dict keyed in candidate order — so a tie went to the
first-listed party. The client compares the two to claim "same voters, different
parliament", which turned two arbitrary picks into a finding about electoral
systems. /gerrymander was worse: its headline index is computed *from* the
leading party's own vote share, so a seat tie moved the number itself.
"""
from api.domain.election.workers import _districts_worker
from api.domain.election.workers_mechanisms import _gerrymander_worker

#: Two candidates close enough to split the districts. Bob at -0.38 sits just
#: inside the band where the seat count flips, which is where ties live.
CLOSE_PAIR = [{"name": "Alice", "x": -0.4, "y": 0.0}, {"name": "Bob", "x": -0.38, "y": 0.0}]

DISTRICTS = {"voters_per_district": 50, "num_districts": 6, "district_ideology_variance": 0.6}


def test_a_tied_proportional_parliament_is_not_a_divergence():
    """FPTP gives Bob 4-2 while PR ties 3-3. PR reported "Alice" — the
    first-listed party — so the panel claimed the two systems disagreed."""
    body, status = _districts_worker({"candidates": CLOSE_PAIR, "seed": 3, **DISTRICTS})

    assert status == 200
    assert body["parliament_fptp"] == {"Alice": 2, "Bob": 4}
    assert body["parliament_proportional"] == {"Alice": 3, "Bob": 3}
    assert body["fptp_winner"] == ["Bob"]
    assert body["proportional_winner"] == ["Alice", "Bob"]


def test_both_sides_tied_lists_every_tied_party():
    body, status = _districts_worker({"candidates": CLOSE_PAIR, "seed": 1, **DISTRICTS})

    assert status == 200
    assert body["parliament_fptp"] == {"Alice": 3, "Bob": 3}
    assert body["fptp_winner"] == ["Alice", "Bob"] == body["proportional_winner"]


def test_each_leader_list_is_the_argmax_set_of_its_own_seat_dict():
    """The invariant that replaces "one name": whatever the seats are, the
    reported leaders are exactly the parties holding the most of them.

    Note what cannot be asserted here. Reordering the candidate array is not a
    relabelling on this endpoint: `build_candidate_from_xy` assigns each
    candidate a party by list index, and party feeds a loyalty bonus in voter
    utility, so the same two positions listed the other way round draw a
    different vote share (0.45/0.55 vs 0.43/0.57 at seed 3) and legitimately a
    different parliament.
    """
    for seed in range(6):
        body, status = _districts_worker({"candidates": CLOSE_PAIR, "seed": seed, **DISTRICTS})
        assert status == 200
        for seats_key, leaders_key in (("parliament_fptp", "fptp_winner"),
                                       ("parliament_proportional", "proportional_winner")):
            seats = body[seats_key]
            top = max(seats.values())
            assert body[leaders_key] == sorted(p for p, n in seats.items() if n == top), \
                (seed, seats_key)


def _gerrymander(candidates):
    """Two districts split at x = 0, so each candidate carries their own side."""
    return _gerrymander_worker({
        "candidates": candidates, "num_voters": 60, "seed": 42,
        "districts": [
            {"id": 0, "bounds": {"x_min": -1.0, "x_max": 0.0, "y_min": -1.0, "y_max": 1.0}},
            {"id": 1, "bounds": {"x_min": 0.0, "x_max": 1.0, "y_min": -1.0, "y_max": 1.0}},
        ],
    })


def test_a_seat_tie_has_no_leading_party_and_so_no_index():
    """The index is "how far from proportional is the leading party". With one
    seat each there is no such party, and computing it for the first-listed one
    made the headline number depend on the array order."""
    body, status = _gerrymander([{"name": "Alice", "x": -0.5, "y": 0.0},
                                 {"name": "Bob", "x": 0.5, "y": 0.0}])
    assert status == 200
    assert body["parliament_gerrymander"] == {"Alice": 1, "Bob": 1}
    assert body["winner"] == ["Alice", "Bob"]
    assert body["gerrymander_index"] is None


def test_one_leading_party_still_gets_its_index():
    body, status = _gerrymander([{"name": "Alice", "x": -0.1, "y": 0.0},
                                 {"name": "Bob", "x": 0.9, "y": 0.9}])
    assert status == 200
    assert len(body["winner"]) == 1
    assert isinstance(body["gerrymander_index"], float)
