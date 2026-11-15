"""The workers' own tallies (a winner read off a count of ballots) draw an exact tie by the
request's seeded lot, as the engine's rules do (tie_lot.py): never by name, never by listing
order. They used to write `min(tally, key=lambda c: (-tally[c], c))`, which hands every tie to
whoever sorts first (#926).

Two kinds of test. The rule-level helpers are pinned on a real tie, listed both ways, with a
pair the lot draws the alphabetically *second* name for (so a name tie-break, and a
first-listed one in one of the two listings, both fail). The workers' nested tallies are
pinned by wiring: the lot is replaced by one that elects the *lowest* tally, and the worker's
reported winner must be that candidate, drawn with the request's seed."""
from typing import Any

import numpy as np
import pytest

from api.domain import tech
from api.domain.election import workers_advanced, workers_behavioral, workers_mechanisms
from api.domain.election.workers import _primary_worker, _run_primary, _runner_up
from api.domain.simulations import compare
from api.domain.theory.workers import _epistocracy_worker, _identity_plurality, _tally_winner_index
from api.engine.utils import quadratic_voting, simulation_metrics, simulation_score_utils, tie_lot
from api.engine.utils.quadratic_voting import apply_quadratic_voting
from api.engine.utils.simulation_multiwinner_utils import get_equal_shares_result
from api.engine.utils.simulation_score_utils import get_evaluative_winner

# At seed 0 the lot draws Cat between Ann and Cat, at seed 1 it draws Ann.
PAIR = ("Ann", "Cat")
DRAWN = {0: "Cat", 1: "Ann", 2: "Cat", 3: "Ann"}


def test_the_pair_is_one_the_lot_draws_both_ways():
    assert {s: tie_lot.draw(sorted(PAIR), s) for s in DRAWN} == DRAWN


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_identity_plurality_draws_a_tie(listed, seed):
    votes = [listed[0], listed[1]]
    assert _identity_plurality(votes, list(listed), seed) == DRAWN[seed]


def test_identity_plurality_with_no_votes_is_the_first_listed():
    assert _identity_plurality([], ["Cat", "Ann"], 0) == "Cat"


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_evaluative_voting_draws_a_tie_for_the_top_net_score(listed, seed):
    ballots = [{listed[0]: 1.0, listed[1]: 1.0}]
    assert get_evaluative_winner(ballots, seed=seed)["winner"] == DRAWN[seed]


def test_evaluative_voting_with_nobody_approved_elects_nobody():
    assert get_evaluative_winner([{"Ann": 0.5, "Cat": 0.5}])["winner"] is None


@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_quadratic_voting_gives_a_voters_odd_vote_by_lot_not_by_name(listed):
    """One voter who rates both equally has 30 credits to spend on 2 votes each (8 credits) and
    22 left: the extra vote is the voter's own tie, drawn by the lot seeded with the request
    and the voter, so it follows the seed and not the names or their order."""
    voter = {listed[0]: 0.5, listed[1]: 0.5}
    winners = {s: apply_quadratic_voting([voter], budget=30, seed=s)["winner"] for s in DRAWN}
    assert set(winners.values()) == set(PAIR)
    other = PAIR[::-1] if listed == PAIR else PAIR
    assert winners == {
        s: apply_quadratic_voting([{other[0]: 0.5, other[1]: 0.5}], budget=30, seed=s)["winner"]
        for s in DRAWN
    }


def test_quadratic_voting_aggregate_tie_is_drawn_by_the_seed():
    """Two voters who each want a different candidate, with the same intensity, tie 3-3."""
    voters = [{"Ann": 0.9, "Cat": 0.1}, {"Ann": 0.1, "Cat": 0.9}]
    for seed in DRAWN:
        assert apply_quadratic_voting(voters, budget=30, seed=seed)["winner"] == DRAWN[seed]
        assert apply_quadratic_voting(voters[::-1], budget=30, seed=seed)["winner"] == DRAWN[seed]


def test_liquid_democracy_tally_draws_a_tie():
    tied = {1: {"Ann": 1.0, "Cat": 0.0}, 2: {"Ann": 0.0, "Cat": 1.0}}
    for seed in DRAWN:
        _, winner = workers_behavioral._ld_tally([(1, 1), (2, 1)], tied, "Ann", seed=seed)
        assert winner == DRAWN[seed]
    _, nobody = workers_behavioral._ld_tally([], tied, "Ann", seed=1)
    assert nobody == "Ann"


def test_the_choice_overload_approval_tally_draws_a_tie():
    voters = [{"id": 1}, {"id": 2}]
    utils = {1: {"Ann": 1.0, "Cat": 0.0}, 2: {"Ann": 0.0, "Cat": 1.0}}
    for seed in DRAWN:
        assert workers_behavioral._co_winner(
            "approval", voters, [["Ann", "Cat"], ["Cat", "Ann"]], utils, {1: "Ann", 2: "Cat"},
            {1: False, 2: False}, ["Ann", "Cat"], seed,
        ) == DRAWN[seed]


# ── wiring: each nested tally goes through the lot, with the request's seed ───────────────


@pytest.fixture
def lowest_by_lot(monkeypatch):
    """`install()` replaces the lot with one that elects the LOWEST value and returns the log of
    its calls (pool, pick, seed)."""
    calls: list[tuple[list[Any], Any, Any]] = []

    def lowest(candidates, value, seed=0):
        pool = list(candidates)
        pick = min(pool, key=value)
        calls.append((pool, pick, seed))
        return pick

    def install():
        for target in (
            tie_lot, workers_advanced, workers_behavioral, workers_mechanisms, compare,
            simulation_metrics, quadratic_voting, simulation_score_utils,
        ):
            if hasattr(target, "best"):
                monkeypatch.setattr(target, "best", lowest)
        return calls

    return install


CANDS = [
    {"name": "Ann", "x": -0.6, "y": 0.0},
    {"name": "Bea", "x": 0.1, "y": 0.1},
    {"name": "Cat", "x": 0.6, "y": -0.1},
]
SEED = 7
BASE = {"num_voters": 100, "seed": SEED, "candidates": CANDS}


WIRED = [
    ("cascade", workers_behavioral._cascade_worker, BASE, lambda b: b["cascade_winner"]),
    ("shy voter", workers_behavioral._shy_voter_worker, {**BASE, "shy_candidate_idx": 0},
     lambda b: b["real_winner"]),
    ("shy voter's poll", workers_behavioral._shy_voter_worker, {**BASE, "shy_candidate_idx": 0},
     lambda b: b["poll_winner"]),
    ("nota", workers_behavioral._nota_worker, BASE, lambda b: b["winner"]),
    ("liquid democracy", workers_behavioral._liquid_democracy_worker, BASE,
     lambda b: b["weighted_results"].get("winner") or b["comparison"].get("direct_winner")),
    ("abstention", workers_mechanisms._abstention_worker, BASE, lambda b: b["sincere_winner"]),
    ("compulsory voting", workers_advanced._compulsory_voting_worker, BASE,
     lambda b: b["voluntary"]["winner"]),
    ("biases: approval", workers_behavioral._behavioral_biases_worker, {**BASE, "method": "plurality"},
     lambda b: b["method_sensitivity"]["approval"]["sincere"]),
    ("polis", tech._polis_with_candidates_worker, {"candidates": CANDS, "seed": SEED, "num_participants": 100},
     lambda b: b["election_winner"]),
    ("gerrymander", workers_mechanisms._gerrymander_worker,
     {**BASE, "districts": [{"id": 0, "bounds": {"x_min": -1.0, "x_max": 1.0, "y_min": -1.0, "y_max": 1.0}}]},
     lambda b: b["districts"][0]["winner"]),
    ("vote steps: approval", compare._vote_steps_worker,
     {"method": "approval", "num_voters": 60, "seed": SEED, "candidates": CANDS},
     lambda b: b["winner"]),
]


@pytest.mark.parametrize("name,worker,data,field", WIRED, ids=[w[0] for w in WIRED])
def test_a_workers_tally_is_drawn_by_the_lot_with_the_requests_seed(
    name, worker, data, field, lowest_by_lot
):
    # The real lot elects the top tally (these electorates are not tied); the stand-in elects
    # the bottom one. A site that still ranks by name keeps the top one, and fails.
    top = field(worker(data)[0])
    calls = lowest_by_lot()
    drawn = field(worker(data)[0])
    assert SEED in {seed for _, _, seed in calls}, name
    assert drawn in {pick for _, pick, seed in calls if seed == SEED}, name
    assert drawn != top, name


def test_random_ballots_most_probable_winner_is_drawn_by_the_lot(lowest_by_lot):
    """Random ballot reports its most probable winner (the biggest first-preference share)."""
    from api.engine.constants import DEFAULT_ISSUES
    from api.engine.utils.demographic_data import _seeded_rng_pair
    from api.engine.utils.simulation_voting_utils import create_candidate, create_voter

    rng, np_rng = _seeded_rng_pair(2)
    candidates = [create_candidate(DEFAULT_ISSUES, i, n, p, rng=rng)
                  for i, (n, p) in enumerate([("Alice", "Green"), ("Bob", "Conservative"), ("Carol", "Liberal")])]
    voters = [create_voter(DEFAULT_ISSUES, i, rng=rng, np_rng=np_rng) for i in range(60)]

    def winner():
        report = simulation_metrics.compare_all_methods(voters, candidates, DEFAULT_ISSUES, seed=SEED)
        return report["methods"]["random_ballot"]["winner"]

    top = winner()
    calls = lowest_by_lot()
    assert winner() != top
    assert SEED in {seed for _, _, seed in calls}


# ── the last #926 aggregates: the epistocracy tally, the Equal Shares completion, runners-up ──


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_the_epistocracy_tally_draws_a_tie_by_lot_not_by_listing(listed, seed):
    """The theory worker read its winner off `tally.index(max(tally))`: the first-listed on a tie."""
    names = [listed[0], listed[1], "Zed"]
    winner = _tally_winner_index([2.0, 2.0, 1.0], names, seed)
    assert names[winner] == DRAWN[seed]


def test_the_epistocracy_tally_does_not_draw_a_unique_maximum():
    assert _tally_winner_index([1.0, 3.0, 2.0], ["Ann", "Bea", "Cat"], 0) == 1


def test_the_epistocracy_tally_keeps_the_best_of_two_candidates_sharing_a_name():
    """Names come from the request and are not unique: the old index-based argmax coped."""
    assert _tally_winner_index([5.0, 1.0, 3.0], ["Ann", "Ann", "Bea"], 0) == 0
    assert _tally_winner_index([1.0, 5.0, 3.0], ["Ann", "Ann", "Bea"], 0) == 1


def test_the_epistocracy_worker_draws_each_trials_tie_with_that_trials_seed(lowest_by_lot):
    """Wired: the real lot elects the top tally (the centrist is right nearly always); a stand-in
    that elects the LOWEST must change the reported rate. Every trial has its own seed, derived
    from the request's (`seed * 1000 + trial`, 40 trials), so a tie that recurs is not settled
    the same way in all of them."""
    data = {"candidates": CANDS, "seed": SEED, "num_voters": 100}
    top = _epistocracy_worker(data)[0]["results"]["equal"]["correct_choice_pct"]
    calls = lowest_by_lot()
    drawn = _epistocracy_worker(data)[0]["results"]["equal"]["correct_choice_pct"]
    assert drawn != top
    assert {seed for _, _, seed in calls} >= {SEED * 1000 + t for t in range(40)}
    # Every call is a draw among the candidates' own names.
    assert all(set(pool) <= {c["name"] for c in CANDS} for pool, _, _ in calls)


def test_the_epistocracy_tally_reads_float_noise_as_a_tie():
    """Competence-weighted tallies are sums of floats: equal up to rounding is a tie, as everywhere."""
    names = ["Ann", "Cat"]
    assert names[_tally_winner_index([0.3 + 0.6, 0.9], names, 0)] == DRAWN[0]


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_the_equal_shares_completion_draws_a_tie_by_lot_when_it_has_no_rng(listed, seed):
    """Two voters, each approving a different candidate, one seat: nobody is affordable, so the
    committee is completed by approval, and the two are tied. Without an rng that went by name."""
    ballots = [[listed[0]], [listed[1]]]
    assert get_equal_shares_result(ballots, 1, seed=seed)["elected"] == [DRAWN[seed]]


def test_the_equal_shares_completion_draws_each_place_in_turn():
    """Three tied candidates, two seats: the first place is drawn among all three, the second
    among the two left, each by the same lot, and the listing order does not reach either."""
    names = ["Ann", "Cat", "Eve"]
    for seed in range(8):
        first = tie_lot.draw(names, seed)
        second = tie_lot.draw([n for n in names if n != first], seed)
        for listed in (names, names[::-1]):
            elected = get_equal_shares_result([[n] for n in listed], 2, seed=seed)["elected"]
            assert elected == [first, second]


def test_the_equal_shares_completion_keeps_the_callers_rng_when_it_has_one():
    import random

    ballots = [["Ann"], ["Cat"]]
    elected = {tuple(get_equal_shares_result(ballots, 1, rng=random.Random(s))["elected"])
               for s in range(16)}
    assert elected == {("Ann",), ("Cat",)}  # drawn by the rng it was given, whatever the seed


def _primary(names, firsts, seed):
    """A primary whose voters' first choices are `firsts` (a list of names, one per voter)."""
    voters = [{"id": i} for i in range(len(firsts))]
    utilities = {i: {n: (1.0 if n == f else 0.0) for n in names} for i, f in enumerate(firsts)}
    return _run_primary([{"name": n} for n in names], voters, utilities, "plurality",
                        np.random.default_rng(0), seed)


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_a_primarys_runner_up_is_drawn_when_two_tie_for_second(listed, seed):
    """Zed wins with 4 first preferences; Ann and Cat have 2 each. The runner-up used to be the
    first-listed of the two."""
    names = [listed[0], "Zed", listed[1]]
    result = _primary(names, ["Zed"] * 4 + [PAIR[0]] * 2 + [PAIR[1]] * 2, seed)
    assert result["winner"] == "Zed"
    assert result["runner_up"] == DRAWN[seed]


@pytest.mark.parametrize("seed", sorted(DRAWN))
@pytest.mark.parametrize("listed", [PAIR, PAIR[::-1]])
def test_the_runner_up_of_any_election_is_drawn_when_two_tie_for_second(listed, seed):
    """The general election's runner-up goes through the same function as a primary's; a tie for
    second place there cannot be made to happen by sampling, so it is pinned here. Listed both
    ways, with the winner listed first, last and between."""
    counts = {"Zed": 4, PAIR[0]: 2, PAIR[1]: 2}
    for names in ([*listed, "Zed"], ["Zed", *listed], [listed[0], "Zed", listed[1]]):
        assert _runner_up(names, counts, "Zed", seed) == DRAWN[seed]


def test_there_is_no_runner_up_without_another_candidate_and_a_win():
    assert _runner_up(["Zed"], {"Zed": 3}, "Zed", 0) is None
    assert _runner_up(["Ann", "Cat"], {"Ann": 1}, None, 0) == "Ann"  # nobody won: best of both


def test_a_primarys_runner_up_is_the_runner_up_when_there_is_one():
    result = _primary(["Zed", "Ann", "Cat"], ["Zed"] * 4 + ["Cat"] * 3 + ["Ann"], 0)
    assert (result["winner"], result["runner_up"]) == ("Zed", "Cat")


def test_a_primarys_runner_up_counts_first_preferences_not_their_rounded_shares():
    """The shares are rounded to 4 places, and 10001 and 10000 voters out of 70001 round to the
    same one: they are not tied. The lot draws Cat at seed 0, so a tie would give the wrong one."""
    firsts = ["Zed"] * 50000 + ["Ann"] * 10001 + ["Cat"] * 10000
    result = _primary(["Zed", "Ann", "Cat"], firsts, 0)
    assert result["vote_shares"]["Ann"] == result["vote_shares"]["Cat"]  # the premise
    assert result["runner_up"] == "Ann"


def test_a_primary_with_one_candidate_has_no_runner_up():
    assert _primary(["Zed"], ["Zed"] * 3, 0)["runner_up"] is None


def _districts_data():
    def party(name, centre, a, b):
        return {"name": name, "ideology_center": centre, "primary_voters_pct": 0.3,
                "primary_candidates": [{"name": a, "ideology_position": centre - 0.1},
                                       {"name": b, "ideology_position": centre + 0.1}]}
    return {"parties": [party("Left", -0.7, "L1", "L2"), party("Centre", 0.0, "C1", "C2"),
                        party("Right", 0.7, "R1", "R2")],
            "general_num_voters": 301, "seed": SEED, "general_method": "plurality"}


def test_the_general_runner_up_is_drawn_by_the_lot_with_the_requests_seed(lowest_by_lot):
    """Wired like the tallies above: the real lot elects the runner-up (the second most first
    preferences); a stand-in that elects the LOWEST one must change the reported runner-up, and
    be asked with the request's seed. A site that still sorts by share keeps the real one."""
    top = _primary_worker(_districts_data())[0]["general_runner_up"]
    calls = lowest_by_lot()
    drawn = _primary_worker(_districts_data())[0]["general_runner_up"]
    assert SEED in {seed for _, _, seed in calls}
    assert drawn in {pick for _, pick, seed in calls if seed == SEED}
    assert drawn != top
