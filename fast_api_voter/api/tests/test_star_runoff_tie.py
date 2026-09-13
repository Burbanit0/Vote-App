"""STAR voting: first-round averaging, runoff vote-counting, and the tie-break.

Originally just the tie-break fixture (a tied automatic runoff is broken by
SCORE: the higher-scored finalist wins — the old code used `>` instead of
`>=` and gave it to the lower-scored one). Expanded after mutmut found this
was the least-tested cardinal rule by a wide margin (57 surviving mutants,
more than any other single function in either engine file) — every prior
fixture here used exactly two candidates whose first-round average never
had to be exact for the right one to reach the runoff, always let the
higher-average candidate also win the head-to-head, and never had a ballot
that omitted a finalist or a second tied ballot. None of that is
hypothetical paranoia: each gap below is a specific mutation that survived
specifically because of it (see the fix commit for the exact mutant IDs).
`get_median_voting_winner`/`get_mean_median_hybrid_winner`/
`get_variance_based_winner` in test_cardinal_orphans.py already pin their
own arithmetic this precisely; STAR voting was the one cardinal rule that
never got the same treatment.

Not every survivor here is fixable: `data["count"] > 0` mutated to
`(data["count"] > 0) or True` (or `>= 0`) is a genuine equivalent mutant —
every candidate in `candidate_scores` was necessarily added by at least one
ballot, so its count can never be 0 or negative when the branch runs. No
test can distinguish "always true" from "true for a reason that always
holds"; left alone rather than chased.
"""

from api.engine.utils.simulation_score_utils import get_star_voting_winner


def test_star_runoff_tie_goes_to_higher_score():
    # A is the higher-total finalist (8 vs 5). The runoff is tied 1–1 (one ballot
    # prefers each, one is equal) → STAR awards the tie to A on score.
    ballots = [{"A": 5, "B": 0}, {"A": 0, "B": 2}, {"A": 3, "B": 3}]
    out = get_star_voting_winner(ballots)
    assert out["winner"] == "A"
    assert out["method"] == "STAR Voting"


def test_star_first_round_averages_pin_the_accumulator_arithmetic():
    """Three candidates with fully distinct averages, so the correct one must
    be excluded from the runoff for the right reason: B's true average (2.0)
    is lowest and it's the one dropped. A defaultdict seeded at 1 instead of
    0, or `+=` mutated to `=` (only the last ballot's score survives), would
    both shift every average and could easily let the wrong candidate reach
    the runoff — asserting the winner alone wouldn't necessarily catch it,
    asserting the exact averages does."""
    ballots = [
        {"A": 2, "B": 1, "C": 7},
        {"A": 4, "B": 2, "C": 8},
        {"A": 6, "B": 3, "C": 9},
    ]
    out = get_star_voting_winner(ballots)

    assert out["details"]["first_round"] == {"A": 4.0, "B": 2.0, "C": 8.0}
    assert out["details"]["runoff"]["candidate1"] == "C"
    assert out["details"]["runoff"]["candidate2"] == "A"
    assert out["winner"] == "C"


def test_star_runoff_counts_each_ballot_once_on_the_correct_side():
    """A clear-cut (non-tied) runoff: 3 ballots prefer A, 1 prefers B, 0 tied.
    Pins votes1/votes2/tied individually rather than just their net effect on
    the winner -- a counter that increments the wrong side, or double-counts
    a ballot, can still happen to pick the same winner while reporting the
    wrong tally."""
    ballots = [
        {"A": 5, "B": 3},
        {"A": 5, "B": 3},
        {"A": 1, "B": 3},
        {"A": 5, "B": 3},
    ]
    out = get_star_voting_winner(ballots)

    assert out["details"]["runoff"] == {
        "candidate1": "A",
        "candidate2": "B",
        "votes1": 3,
        "votes2": 1,
        "tied": 0,
        "total_voters": 4,
    }
    assert out["winner"] == "A"


def test_star_single_candidate_wins_without_a_runoff():
    out = get_star_voting_winner([{"A": 5}, {"A": 3}])

    assert out["winner"] == "A"
    assert out["method"] == "STAR Voting"
    assert out["details"]["first_round"] == {"A": 4.0}
    assert out["details"]["runoff"] is None


def test_star_no_ballots_has_no_winner():
    out = get_star_voting_winner([])

    assert out["winner"] is None
    assert out["details"] == {"first_round": {}, "runoff": None}


def test_star_the_runoff_can_overturn_the_first_round_leader():
    """The entire point of STAR's automatic runoff: a candidate can lead in
    first-round average and still lose head-to-head. A has the higher
    average (4.0 vs 3.0) purely from one high score (10), but B is
    preferred on 2 of the 3 ballots -- B must win. `votes1 >= votes2`
    mutated to something always-true (e.g. `(votes1 >= votes2) or True`)
    would make candidate1 win unconditionally; every other fixture in this
    file happens to have candidate1 win for real too, so only a case where
    the underdog genuinely wins can catch that."""
    ballots = [{"A": 10, "B": 3}, {"A": 1, "B": 3}, {"A": 1, "B": 3}]
    out = get_star_voting_winner(ballots)

    assert out["details"]["first_round"] == {"A": 4.0, "B": 3.0}
    assert out["details"]["runoff"]["candidate1"] == "A"
    assert out["details"]["runoff"]["votes1"] == 1
    assert out["details"]["runoff"]["votes2"] == 2
    assert out["winner"] == "B"


def test_star_a_ballot_that_skips_a_finalist_counts_as_a_zero():
    """A voter who doesn't rate a finalist at all (the key is simply absent,
    not scored 0) must be treated the same as scoring them 0 -- `vote.get(
    candidate, 0)`'s default. Exercises the default on BOTH sides: ballot 2
    omits A, ballot 3 omits B."""
    ballots = [{"A": 5, "B": 4}, {"B": 6}, {"A": 5}]
    out = get_star_voting_winner(ballots)

    assert out["details"]["first_round"] == {"A": 5.0, "B": 5.0}
    assert out["details"]["runoff"] == {
        "candidate1": "A",
        "candidate2": "B",
        "votes1": 2,
        "votes2": 1,
        "tied": 0,
        "total_voters": 3,
    }
    assert out["winner"] == "A"


def test_star_multiple_tied_ballots_all_count():
    """Two tied ballots, not one: `tied += 1` mutated to `tied = 1` would
    still read 1 after a SINGLE tied ballot (the pre-existing tie-break
    fixture only ever had one), so distinguishing accumulation from a hard
    reset needs at least two."""
    ballots = [{"A": 5, "B": 3}, {"A": 2, "B": 2}, {"A": 4, "B": 4}]
    out = get_star_voting_winner(ballots)

    assert out["details"]["runoff"]["tied"] == 2
    assert out["details"]["runoff"]["votes1"] == 1
    assert out["details"]["runoff"]["votes2"] == 0


def test_star_a_candidate_scored_by_only_one_ballot_averages_to_that_score():
    """`data["count"] > 0` mutated to `> 1` only shows up when a candidate's
    count is exactly 1 -- every other fixture here scores every candidate on
    2+ ballots. A is scored by a single ballot (7) and must average to
    exactly 7.0, not silently fall through to the `else 0` branch."""
    ballots = [{"A": 7, "B": 2}, {"B": 3}, {"B": 4}]
    out = get_star_voting_winner(ballots)

    assert out["details"]["first_round"] == {"A": 7.0, "B": 3.0}


def test_star_an_omitted_finalist_scores_exactly_zero_not_one():
    """The `vote.get(candidate, 0)` default has to be exactly 0 -- not just
    "small" -- for both finalists. A and B tie in the first round (3.0
    each); ballot 2 omits B, ballot 3 omits A. If either default silently
    became 1, the omitted side would tie 1-1 with the other's real score of
    1 instead of losing 0-1, flipping that ballot from a clear win to a
    tie and changing votes1/votes2/tied all at once."""
    ballots = [{"A": 5, "B": 5}, {"A": 1}, {"B": 1}]
    out = get_star_voting_winner(ballots)

    assert out["details"]["runoff"] == {
        "candidate1": "A",
        "candidate2": "B",
        "votes1": 1,
        "votes2": 1,
        "tied": 1,
        "total_voters": 3,
    }
    assert out["winner"] == "A"
