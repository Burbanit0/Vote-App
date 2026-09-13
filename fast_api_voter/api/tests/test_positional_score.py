"""Unit tests for `get_positional_score_winner` (aliased as `get_score_winner`):
a positional rule that, unlike Borda, normalises each ballot's weights to a
fixed [0, 1] range (1 - position / (num_candidates - 1)) instead of raw
integer counts. This lets ballots of different lengths (partial rankings)
contribute comparably, at the cost of also changing outcomes relative to
Borda when ballot lengths vary within the same profile.

No dedicated test file existed before -- CODE_AUDIT.md §7 item 6. This
function is live production code (used by
`api/domain/simulations/base.py`'s "score_winner",
`api/engine/utils/gibbard_satterthwaite.py`, and
`api/engine/utils/arrow_criteria.py`), not dead code, and is currently absent
from `test_voting_criteria_matrix.py`'s METHODS registry -- unlike the other
21 "locked" ordinal methods, it (like `approval` and `random_ballot`) was
never axiomatically classified there. See CODE_AUDIT.md's 2026-09-12 "(bis)"
update for the full re-derivation of this file's test-coverage gap."""

from api.engine.utils.simulation_ranked_utils import (
    get_borda_winner,
    get_positional_score_winner,
    get_score_winner,
)


def test_score_winner_is_the_positional_score_winner_alias():
    ballots = [["A", "B", "C"], ["A", "C", "B"]]
    assert get_score_winner is get_positional_score_winner
    assert get_score_winner(ballots) == get_positional_score_winner(ballots)


def test_positional_score_elects_the_unanimous_first_choice():
    ballots = [["A", "B", "C"], ["A", "C", "B"], ["A", "B", "C"]]
    assert get_positional_score_winner(ballots) == "A"


def test_positional_score_diverges_from_borda_on_mixed_ballot_lengths():
    """Borda's raw linear weights give a full ranking's top choice more raw
    points than a short ranking's top choice (n-1 vs a smaller n-1), so mixing
    ballot lengths lets a candidate who wins fewer but "denser" (full-length)
    ballots out-score one who wins more, shorter ballots outright. Positional
    score normalises every ballot's top choice to exactly 1 regardless of
    length, which flips the outcome here.

    4 full-length ballots A>B>C (n=3): Borda gives A +2, B +1 each.
    3 short ballots B>A (n=2): Borda gives B +1 each.
    Borda totals: A = 4*2 = 8, B = 4*1 + 3*1 = 7 -> Borda winner A.

    Positional-score totals (top choice always +1.0, middle of a 3-way ballot
    +0.5): A = 4*1.0 = 4.0, B = 4*0.5 + 3*1.0 = 5.0 -> positional-score
    winner B.
    """
    ballots = [["A", "B", "C"]] * 4 + [["B", "A"]] * 3
    assert get_borda_winner(ballots) == "A"
    assert get_positional_score_winner(ballots) == "B"


def test_positional_score_exact_tie_breaks_alphabetically():
    ballots = [["A", "B"], ["B", "A"]]
    assert get_positional_score_winner(ballots) == "A"


def test_positional_score_single_and_empty():
    assert get_positional_score_winner([]) is None
    assert get_positional_score_winner([["A"]]) == "A"


def test_positional_score_ballots_with_no_ranked_candidates():
    # Non-empty ballot list, but every ranking is itself empty -> no scores
    # ever get recorded, distinct from the get_positional_score_winner([])
    # case above.
    assert get_positional_score_winner([[], []]) is None
