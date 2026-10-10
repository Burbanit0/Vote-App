"""The tie lot (api/engine/utils/tie_lot.py). voter-app/src/lib/tieLot.test.ts pins the
same values: the two engines must draw the same candidate from the same tie."""

import pytest

from api.engine.utils.simulation_score_utils import (
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_simple_score_winner,
    get_star_voting_winner,
    get_variance_based_winner,
)
from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.demographic_data import _seeded_rng_pair
from api.engine.utils.simulation_voting_utils import create_candidate, create_voter, vote_ranked
from api.engine.utils.tie_lot import _fnv1a, best, draw, ranking, tied


def test_the_hash_is_fnv1a_32():
    assert _fnv1a(b"") == 0x811C9DC5
    assert _fnv1a(b"a") == 0xE40C292C  # the published FNV-1a test vector


@pytest.mark.parametrize(
    "names, seed, drawn",
    [
        (["Ann", "Ben"], 0, "Ben"),
        (["Ann", "Ben"], 7, "Ann"),
        (["Alice", "Bob", "Carol"], 0, "Carol"),
        (["Alice", "Bob", "Carol"], 7, "Alice"),
        (["Zoé", "Émile", "Ana"], 0, "Zoé"),
        (["Zoé", "Émile", "Ana"], 7, "Ana"),
        (["C0", "C1", "C2", "C3"], 0, "C3"),
        (["C0", "C1", "C2", "C3"], 7, "C2"),
        (["Ann", "Anna"], 0, "Ann"),  # one name a prefix of the other
        (["Ann", "Anna"], 7, "Anna"),
    ],
)
def test_draw_pins_the_values_the_client_pins(names, seed, drawn):
    assert draw(names, seed) == drawn
    assert draw(list(reversed(names)), seed) == drawn  # listing order does not matter


def test_best_draws_only_among_the_tied_top():
    values = {"Ann": 3.0, "Ben": 3.0, "Cy": 1.0}
    assert best(["Cy", "Ben", "Ann"], values.__getitem__) == draw(["Ann", "Ben"])
    assert best(["Ann", "Cy"], {"Ann": 1.0, "Cy": 2.0}.__getitem__) == "Cy"


def test_float_noise_is_a_tie_and_a_real_gap_is_not():
    # Nash's logs: Python and the client's Math.log can differ in the last bits.
    assert tied(3.178053830347945, 3.1780538303479458)
    assert tied(float("-inf"), float("-inf"))
    assert not tied(1.0, 1.000001)
    assert not tied(float("inf"), 1e308)
    values = {"Bob": 3.1780538303479458, "Zed": 3.178053830347945, "Mo": 1.0}
    assert best(values, values.__getitem__) == draw(["Bob", "Zed"])


@pytest.mark.parametrize(
    "names, seed, drawn",
    [
        (["\ud800", "A"], 0, "\ud800"),
        (["\ud800", "A"], 7, "A"),
        (["\ud800", "\ufffd", "B"], 0, "B"),
        (["\ud800", "\ufffd", "B"], 7, "\ufffd"),
    ],
)
def test_a_lone_surrogate_hashes_as_the_replacement_character(names, seed, drawn):
    # JSON allows one; the client's TextEncoder writes it as U+FFFD, and so does the lot.
    assert draw(names, seed) == drawn


def test_best_ignores_nan_and_falls_back_to_the_first_when_none_ranks():
    nan = float("nan")
    assert best(["A", "B"], {"A": nan, "B": 1.0}.__getitem__) == "B"
    assert best(["A", "B"], {"A": nan, "B": nan}.__getitem__) == "A"


@pytest.mark.parametrize(
    "rule",
    [
        get_simple_score_winner,
        get_median_voting_winner,
        get_mean_median_hybrid_winner,
        get_variance_based_winner,
    ],
)
def test_the_details_list_the_drawn_winner_first_among_those_tied(rule):
    # Ann and Ben mirror each other exactly; Ann is listed first, the lot draws Ben.
    ballots = [{"Ann": 1.0, "Ben": 0.0, "Cy": 0.2}, {"Ann": 0.0, "Ben": 1.0, "Cy": 0.2}]
    result = rule(ballots)
    first = next(iter(result["details"]))
    assert result["winner"] == "Ben"
    assert (first if isinstance(first, str) else first["candidate"]) == "Ben"


def test_star_lists_its_first_finalist_first():
    ballots = [{"Ann": 1.0, "Ben": 0.0, "Cy": 0.2}, {"Ann": 0.0, "Ben": 1.0, "Cy": 0.2}]
    result = get_star_voting_winner(ballots)
    assert next(iter(result["details"]["first_round"])) == result["winner"] == "Ben"


def test_ranking_orders_a_tie_by_the_seeded_lot_not_the_listing_order():
    u = {"Ann": 1.0, "Ben": 1.0, "Cy": 2.0}
    for seed in range(8):
        r = ranking(["Ann", "Ben", "Cy"], u.__getitem__, seed)
        assert r[0] == "Cy"
        assert r == ranking(["Ben", "Cy", "Ann"], u.__getitem__, seed)
    # Seeded per voter, a tie falls both ways across voters.
    assert len({tuple(ranking(u, u.__getitem__, s)) for s in range(8)}) == 2


def test_vote_ranked_orders_twin_candidates_by_the_lot_not_the_listing_order():
    # Two candidates identical but for their name tie exactly for every voter (#662).
    rng, np_rng = _seeded_rng_pair(662)
    alice = create_candidate(DEFAULT_ISSUES, 0, "Alice", "Green", rng=rng)
    carol = create_candidate(DEFAULT_ISSUES, 2, "Carol", "Liberal", rng=rng)
    cands = [alice, {**alice, "name": "Bob"}, carol]
    for i in range(6):
        voter = create_voter(DEFAULT_ISSUES, i, rng=rng, np_rng=np_rng)
        forward = [c["name"] for c in vote_ranked(voter, cands, DEFAULT_ISSUES)]
        backward = [c["name"] for c in vote_ranked(voter, cands[::-1], DEFAULT_ISSUES)]
        assert forward == backward
