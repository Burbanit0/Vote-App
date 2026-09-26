"""Ballots come from each voter's exact utility. calculate_utility used to round
it to 4 places, which made a voter hold two candidates equal that they don't
(0.5919434 vs 0.5919369 both read 0.5919), and the ballot then settled that
invented tie by listing order: against the voter's real preference, and
differently when the candidates were listed in another order."""
from api.domain.election._electorate import _build_base_electorate
from api.domain.election.workers_mechanisms import _stv_worker
from api.engine.constants import DEFAULT_ISSUES

DEFAULTS = [
    {"name": "Alice", "x": -0.5, "y": -0.2}, {"name": "Bob", "x": 0.5, "y": 0.2},
    {"name": "Carol", "x": 0.0, "y": 0.3}, {"name": "Dave", "x": -0.2, "y": 0.5},
]


def test_a_voter_keeps_a_preference_rounding_would_have_erased():
    """Seed 59, voter 20: Carol 0.5919434 over Alice 0.5919369."""
    _, voters, utils, _ = _build_base_electorate(DEFAULTS, 300, "random", 59, DEFAULT_ISSUES)
    u = utils[voters[20]["id"]]
    assert round(u["Carol"], 4) == round(u["Alice"], 4)
    assert u["Carol"] > u["Alice"] == max(v for k, v in u.items() if k != "Carol")


def test_the_same_voters_count_the_same_whatever_the_listing():
    req = {"num_voters": 300, "num_seats": 3, "seed": 59}
    forward = _stv_worker({**req, "candidates": DEFAULTS})[0]
    reverse = _stv_worker({**req, "candidates": DEFAULTS[::-1]})[0]
    assert forward["vote_shares"] == reverse["vote_shares"]
    # Voter 20 counted for Carol, their real favourite: rounded, they went to
    # the first-listed Alice (0.7233 / 0.2367 listed forward).
    assert (forward["vote_shares"]["Alice"], forward["vote_shares"]["Carol"]) == (0.72, 0.24)


def test_districts_do_not_depend_on_the_listing():
    """CLOSE_PAIR used to draw a different vote share reversed (0.45/0.55 vs
    0.4267/0.5733 at seed 3): the rounding, not a party label."""
    from api.domain.election.workers import _districts_worker
    from api.tests.test_seat_leader_tie_lists import CLOSE_PAIR, DISTRICTS

    for seed in range(6):
        a = _districts_worker({"candidates": CLOSE_PAIR, "seed": seed, **DISTRICTS})[0]
        b = _districts_worker({"candidates": CLOSE_PAIR[::-1], "seed": seed, **DISTRICTS})[0]
        assert a["national_vote_share"] == b["national_vote_share"], seed


def test_a_counted_manipulator_never_reports_a_zero_gain():
    """Voter 79 gains 8.3e-6 by compromising. Kept to 4 places the gain read
    0.0 on a voter counted as a manipulator; it is chosen on the exact value
    and shown to 4 significant figures."""
    from api.domain.theory.workers import _manipulation_analysis_worker

    pts = [(-0.91, -0.47), (0.04, -0.74), (0.57, -0.75), (1.0, 0.13), (0.46, 0.38), (0.09, -0.69)]
    body, status = _manipulation_analysis_worker({
        "candidates": [{"name": f"C{i}", "x": x, "y": y} for i, (x, y) in enumerate(pts)],
        "num_voters": 88, "ideology": "polarized", "seed": 265174, "method": "two_round"})
    assert status == 200 and body["manipulable"]
    assert all(m["utility_gain"] > 0 for m in body["manipulators"])
    assert body["key_manipulator"]["gain"] > 0
