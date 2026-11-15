"""What the BACKEND does with a truncated ballot and with equal ranks, today.

This pins a state of affairs; it is not a convention (docs/spec/truncated-ballots.md, PLAN_GLOBAL_
2026-11.md Phase 3, work order P3-5). The client's side is pinned in voter-app/src/lib/
truncatedBallots.test.ts against the same fixture, and the table in the spec is checked there too.
That the fixture is the backend's current answer is test_truncated_ballots_fixture.py's job (it runs
the generator in a subprocess, so it stays out of mutmut's selection).

A rule is handed a ranking that lists only some of the candidates: nothing in the API forbids it,
`project_ballot`'s "rank_truncated" ballot makes them, and the rules do not crash. What each one
makes of the candidates a ballot leaves out is below, one reading at a time.
"""
import json
from pathlib import Path

import pytest

from api.engine.utils.method_registry import RANKED_RULES, SCORE_RULES, winner_from_utilities
from api.engine.utils.profile_engine import project_ballot
from api.engine.utils.simulation_ranked_utils import _pairwise_wins

BACKEND = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (BACKEND.parent / "voter-app" / "src" / "lib" / "__fixtures__" / "truncatedBallots.json").read_text()
)
#: client rule id -> the registry's key (the client's "condorcet" is Copeland's method).
ORDINAL = {
    **{r: r for r in FIXTURE["truncated"]["backend"]},
    "condorcet": "copeland",
    "kemeny": "kemeny_young",
}


# ── the 21 ordinal rules take a short ballot ────────────────────────────────────────────────────


@pytest.mark.parametrize("rule", sorted(FIXTURE["truncated"]["backend"]))
def test_every_ordinal_rule_elects_someone_from_short_ballots(rule):
    """No rule raises, and none elects nobody, on any of the 60 profiles of 1-to-4-place ballots."""
    winners = FIXTURE["truncated"]["backend"][rule]
    assert len(winners) == len(FIXTURE["truncated"]["profiles"]) == 60
    for profile, winner in zip(FIXTURE["truncated"]["profiles"], winners):
        ranked = {c for ballot in profile for c in ballot}
        assert winner in ranked, (rule, profile, winner)


# ── the readings ────────────────────────────────────────────────────────────────────────────────


def test_in_a_duel_an_unranked_candidate_is_below_every_ranked_one_and_two_unranked_do_not_duel():
    """The shared pairwise count (copeland, minimax, schulze, ranked pairs, river, Kemeny, Black,
    Raynaud, Benham, Smith-IRV, split cycle all read it). Ballot 1 ranks A then B and leaves C out;
    ballot 2 ranks only C."""
    pw = _pairwise_wins([["A", "B"], ["C"]])
    assert pw == {
        "A": {"A": 0, "B": 1, "C": 1},  # A over B (ballot 1) and over the unranked C (ballot 1)
        "B": {"A": 0, "B": 0, "C": 1},  # B over the unranked C; nothing against A from ballot 2
        "C": {"A": 1, "B": 1, "C": 0},  # C over the unranked A and B (ballot 2)
    }
    # A and B in ballot 2 are both unranked: that ballot casts no vote in their duel.
    assert pw["A"]["B"] + pw["B"]["A"] == 1


def test_borda_scores_a_ballot_by_its_own_length():
    """The points are length - 1 - position: a bullet vote [A] gives A zero points, where on a
    four-candidate field the same ballot, ranked in full, would give A three."""
    assert RANKED_RULES["borda"]([["A"], ["B", "C"]]) == "B"  # A: 0, B: 1, C: 0
    assert RANKED_RULES["borda"]([["A"], ["B", "C"], ["A"]]) == "B"  # still: two bullet votes, 0 each
    assert RANKED_RULES["dowdall"]([["A"], ["B", "C"], ["A"]]) == "A"  # 1/(k+1): A is first twice


def test_the_last_ranked_candidate_is_the_one_a_ballot_vetoes():
    """Anti-plurality (and Coombs' round) read `ranking[-1]`: the last RANKED candidate."""
    assert RANKED_RULES["anti_plurality"]([["A", "B"], ["B", "C"], ["C"]]) == "A"  # B and C vetoed once


def test_a_candidate_no_ballot_ranks_is_not_in_the_field():
    """The candidates are read off the ballots. Nobody ranks A: the backend never considers it,
    where a field of four would give a never-vetoed A zero vetoes and the win."""
    ballots = [["D"], ["B"], ["C", "B"], ["D", "C", "B"], ["D"]]  # profile 8 of the fixture
    assert RANKED_RULES["anti_plurality"](ballots) == "C"
    assert FIXTURE["truncated"]["backend"]["anti_plurality"][8] == "C"
    assert "A" not in {c for b in ballots for c in b}


# ── equal ranks ─────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rule", sorted(FIXTURE["truncated"]["backend"]))
def test_equal_ranks_do_not_follow_the_listing_order(rule):
    """Voters exactly as near to two candidates as to each other: the backend orders each voter's own
    tie by a lot seeded with the voter (#662), so listing the candidates the other way round moves
    nothing."""
    backend = FIXTURE["equalRanks"]["backend"]
    assert backend["listed"][rule] == backend["reversed"][rule]


# ── a truncated SCORE ballot ────────────────────────────────────────────────────────────────────


def test_a_truncated_score_ballot_gives_the_ranked_places_their_share_and_the_rest_zero():
    """`project_ballot` "rank_truncated" at 2: first place 1.0, second 0.5, every other 0."""
    utilities = {0: {"A": 0.9, "B": 0.2, "C": 0.6, "D": 0.1}}
    assert project_ballot(utilities, ["A", "B", "C", "D"], "rank_truncated", truncate_at=2) == {
        0: {"A": 1.0, "B": 0.0, "C": 0.5, "D": 0.0}
    }


@pytest.mark.parametrize("rule,key", [("score", "simple_score"), ("star", "star_voting"),
                                      ("cumulative", "cumulative"), ("maximin", "maximin"), ("nash", "nash")])
def test_the_score_rules_count_the_zeros_of_a_truncated_ballot(rule, key):
    names = FIXTURE["candidates"]
    result = SCORE_RULES[key]([dict(zip(names, row)) for row in FIXTURE["scores"]["ballots"]])
    winner = result["winner"] if isinstance(result, dict) else result
    assert winner == FIXTURE["scores"]["backend"][rule]


@pytest.mark.parametrize("rule", ["approval", "majority_judgment"])
@pytest.mark.parametrize("truncate_at,elected", [(1, "A"), (2, "C"), (3, "C")])
def test_approval_and_majority_judgment_read_the_projected_utilities_of_a_truncated_ballot(
    rule, truncate_at, elected
):
    """Neither takes a ballot's zeros as they are: approval approves what is above the voter's own
    mean, majority judgment grades the projected utility. On six voters whose full-information
    winner is C, a one-place ballot (the top choice 1.0, the rest 0) elects A under both. The client
    derives both from utility in its own way and has no truncation, so there is nothing beside them."""
    names = FIXTURE["candidates"]
    matrix = {i: dict(zip(names, row)) for i, row in enumerate([
        [0.9, 0.2, 0.6, 0.1], [0.1, 0.8, 0.7, 0.3], [0.5, 0.4, 0.9, 0.2],
        [0.3, 0.9, 0.2, 0.6], [0.8, 0.1, 0.3, 0.7], [0.2, 0.3, 0.8, 0.9],
    ])}
    voters = [{"id": i} for i in matrix]
    assert winner_from_utilities(rule, matrix, voters, seed=0) == "C"
    projected = project_ballot(matrix, names, "rank_truncated", truncate_at=truncate_at)
    assert winner_from_utilities(rule, projected, voters, seed=0) == elected
