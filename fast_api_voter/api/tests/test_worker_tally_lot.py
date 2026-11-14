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

import pytest

from api.domain import tech
from api.domain.election import workers_advanced, workers_behavioral, workers_mechanisms
from api.domain.simulations import compare
from api.domain.theory.workers import _identity_plurality
from api.engine.utils import quadratic_voting, simulation_metrics, simulation_score_utils, tie_lot
from api.engine.utils.quadratic_voting import apply_quadratic_voting
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
