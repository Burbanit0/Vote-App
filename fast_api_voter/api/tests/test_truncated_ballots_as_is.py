"""What the BACKEND does with a truncated ballot, today, one reading at a time.

This pins a state of affairs; it is not a convention (docs/spec/truncated-ballots.md, PLAN_GLOBAL_
2026-11.md Phase 3, work order P3-5). A rule is handed a ranking that lists only some of the
candidates: nothing in the API forbids it, `project_ballot`'s "rank_truncated" ballot makes them, and
the rules do not crash. What each one makes of the candidates a ballot leaves out is below.

Every ballot here is a literal, so this file reads nothing outside fast_api_voter/ (it is in mutmut's
selection). The measurements over 60 profiles, the equal ranks and the score ballots are in
test_truncated_ballots_fixture.py, against the fixture the client's test reads too.
"""
import pytest

from api.engine.utils.method_registry import RANKED_RULES
from api.engine.utils.profile_engine import project_ballot
from api.engine.utils.simulation_ranked_utils import _pairwise_wins

#: The 21 ordinal rules the engines share, by the registry's key.
ORDINAL = tuple(sorted(set(RANKED_RULES) - {"approval"}))

def test_there_are_21_ordinal_rules():
    """A rule added to the registry is a rule the tables must say something about."""
    assert len(ORDINAL) == 21


SHORT = [["A"], ["B", "C"], ["C", "A", "B"], ["B"], ["A", "C"]]


@pytest.mark.parametrize("rule", ORDINAL)
@pytest.mark.parametrize("seed", [0, 7])
def test_every_ordinal_rule_elects_a_ranked_candidate_from_short_ballots(rule, seed):
    """No rule raises, and none elects nobody or someone no ballot names."""
    assert RANKED_RULES[rule]([list(b) for b in SHORT], seed=seed) in {"A", "B", "C"}


def test_in_a_duel_an_unranked_candidate_is_below_every_ranked_one_and_two_unranked_do_not_duel():
    """The shared pairwise count `_pairwise_wins` (Copeland, Kemeny-Young, Raynaud, ranked pairs,
    river, Smith-IRV and split cycle read it; minimax and Schulze count duels themselves, Black
    and Benham go through `get_condorcet_winner`). Ballot 1 ranks A then B and leaves C out;
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
    ballots = [["A"], ["A"], ["B", "C"]]  # A: 0 + 0 + 0, B: 1, C: 0
    for seed in range(12):
        assert RANKED_RULES["borda"](ballots, seed=seed) == "B"
        assert RANKED_RULES["plurality"](ballots, seed=seed) == "A"
    assert RANKED_RULES["dowdall"]([["A"], ["B", "C"], ["A"]]) == "A"  # 1/(k+1): A is first twice


def test_the_last_ranked_candidate_is_the_one_a_ballot_vetoes():
    """Anti-plurality (and Coombs' round) read `ranking[-1]`: the last RANKED candidate. On
    these ballots B is vetoed once, C twice, and A never."""
    assert RANKED_RULES["anti_plurality"]([["A", "B"], ["B", "C"], ["C"]]) == "A"


def test_a_candidate_no_ballot_ranks_is_not_in_the_field():
    """The candidates are read off the ballots. Nobody ranks A: the backend never considers it,
    where a field of four would give a never-vetoed A zero vetoes and the win."""
    ballots = [["D", "B"], ["C", "D"], ["B", "C"]]
    for rule in ("anti_plurality", "coombs"):
        assert {RANKED_RULES[rule]([list(b) for b in ballots], seed=s) for s in range(12)} <= {
            "B", "C", "D",
        }


def test_project_ballot_rank_truncated_gives_the_ranked_places_their_share_and_the_rest_zero():
    """First place 1.0, second 0.5 (at 2 places), every other candidate 0."""
    utilities = {0: {"A": 0.9, "B": 0.2, "C": 0.6, "D": 0.1}}
    assert project_ballot(utilities, ["A", "B", "C", "D"], "rank_truncated", truncate_at=2) == {
        0: {"A": 1.0, "B": 0.0, "C": 0.5, "D": 0.0}
    }
