"""Tests for the six cardinal rules that no test file covered.

simulation_score_utils.py exports 11 rules. Before this file, six of them had no
dedicated test and were absent from the engine-parity harness (which locks only
score, star, cumulative, maximin and nash). Widening mutmut's test selection from
14 to 25 files moved the ordinal module from 440 to 337 survivors and left the
cardinal module at 284 — not one mutant died, because every file added tested an
ordinal rule. That isolated the gap to exactly these six functions.

These assert on the NUMBERS, not just the winner. A test that only checks who won
leaves every arithmetic mutant alive: 0.5*mean + 0.5*median survives becoming
0.5*mean - 0.5*median as long as the ordering happens to hold. Boundary cases get
their own tests for the same reason — the `<` / `<=` seams are where the mutation
operators aim.
"""

import pytest

from api.engine.utils.simulation_score_utils import (
    _mj_majority_gauge,
    _mj_median_grade,
    _utility_to_grade,
    get_evaluative_winner,
    get_majority_judgment_winner,
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_score_distribution_analysis,
    get_variance_based_winner,
)


# ---------------------------------------------------------------- median voting


def test_median_voting_picks_highest_median_not_highest_mean():
    """The whole point of a median rule: one extreme ballot must not decide.

    A has scores 5,0,0 (mean 1.67, median 0); B has 1,1,1 (mean 1.0, median 1).
    A wins on mean, B wins on median. If this test ever reports A, the rule has
    silently become a mean.
    """
    votes = [{"A": 5, "B": 1}, {"A": 0, "B": 1}, {"A": 0, "B": 1}]
    out = get_median_voting_winner(votes)

    assert out["winner"] == "B"
    assert out["method"] == "Median Voting"
    assert out["details"] == {"A": 0, "B": 1}


def test_median_voting_even_count_averages_the_two_middles():
    """statistics.median on an even sample returns the midpoint, not a member."""
    votes = [{"A": 1}, {"A": 2}, {"A": 3}, {"A": 10}]
    out = get_median_voting_winner(votes)

    assert out["details"]["A"] == 2.5


def test_median_voting_empty_ballots_have_no_winner():
    out = get_median_voting_winner([])

    assert out["winner"] is None
    assert out["details"] == {}


# ------------------------------------------------------------ mean/median hybrid


def test_mean_median_hybrid_weights_both_halves_equally():
    """A: 4,4,4,0 → mean 3.0, median 4.0, combined 3.5.
    B: 3,3,3,3 → mean 3.0, median 3.0, combined 3.0.

    Equal means, so only the median half can separate them — which pins the
    0.5/0.5 weighting rather than merely the ordering.
    """
    votes = [
        {"A": 4, "B": 3},
        {"A": 4, "B": 3},
        {"A": 4, "B": 3},
        {"A": 0, "B": 3},
    ]
    out = get_mean_median_hybrid_winner(votes)

    assert out["winner"] == "A"
    by_name = {r["candidate"]: r for r in out["details"]}
    assert by_name["A"]["mean"] == 3.0
    assert by_name["A"]["median"] == 4.0
    assert by_name["A"]["combined"] == 3.5
    assert by_name["B"]["combined"] == 3.0


def test_mean_median_hybrid_orders_details_best_first():
    votes = [{"A": 1, "B": 5}, {"A": 1, "B": 5}]
    out = get_mean_median_hybrid_winner(votes)

    assert [r["candidate"] for r in out["details"]] == ["B", "A"]


def test_mean_median_hybrid_empty_ballots_have_no_winner():
    out = get_mean_median_hybrid_winner([])

    assert out["winner"] is None
    assert out["details"] == []


# ------------------------------------------------------------------- variance


def test_variance_based_prefers_the_consistent_candidate_at_equal_mean():
    """A: 5,5,1,1 → mean 3.0, variance 4.0, std 2.0, weighted 3.0 - 1.0 = 2.0.
    B: 3,3,3,3 → mean 3.0, variance 0.0, std 0.0, weighted 3.0.

    Same mean; B wins purely on consistency. Pins the -0.5*std penalty: flip the
    sign and A wins, drop the term and the two tie.
    """
    votes = [
        {"A": 5, "B": 3},
        {"A": 5, "B": 3},
        {"A": 1, "B": 3},
        {"A": 1, "B": 3},
    ]
    out = get_variance_based_winner(votes)

    assert out["winner"] == "B"
    by_name = {r["candidate"]: r for r in out["details"]}
    assert by_name["A"]["mean"] == 3.0
    assert by_name["A"]["variance"] == pytest.approx(4.0)
    assert by_name["A"]["std_dev"] == pytest.approx(2.0)
    assert by_name["A"]["weighted_score"] == pytest.approx(2.0)
    assert by_name["B"]["variance"] == pytest.approx(0.0)
    assert by_name["B"]["weighted_score"] == pytest.approx(3.0)


def test_variance_based_never_takes_the_root_of_a_negative():
    """variance is computed as E[x²] - E[x]², which floating-point error can push
    a hair below zero when every score is identical. max(variance, 0.0) guards
    the sqrt; without it this raises ValueError."""
    votes = [{"A": 0.1} for _ in range(50)]
    out = get_variance_based_winner(votes)

    assert out["details"][0]["std_dev"] >= 0.0


def test_variance_based_empty_ballots_have_no_winner():
    out = get_variance_based_winner([])

    assert out["winner"] is None


# ------------------------------------------------------- distribution analysis


def test_distribution_bins_scores_by_half_point():
    """Bins are [0,0.5), [0.5,1.0), … — a score lands in exactly one."""
    votes = [{"A": 0.0}, {"A": 0.4}, {"A": 0.5}, {"A": 2.7}]
    out = get_score_distribution_analysis(votes)

    dist = out["details"][0]["distribution"]
    assert dist[0] == 2  # 0.0 and 0.4 → [0, 0.5)
    assert dist[1] == 1  # 0.5        → [0.5, 1.0)
    assert dist[5] == 1  # 2.7        → [2.5, 3.0)
    assert sum(dist) == 4


def test_distribution_keeps_a_perfect_score_of_five():
    """Regression: every bin is half-open [lo, hi), so a score of exactly 5.0 —
    the top of the scale and a perfectly ordinary ballot — matched no bin and was
    dropped from the very distribution it belongs to. The final bin is closed on
    the right so the top of the scale is counted."""
    votes = [{"A": 5.0}, {"A": 5.0}, {"A": 4.9}]
    out = get_score_distribution_analysis(votes)

    row = out["details"][0]
    assert row["total"] == 3, "a maximum score must not vanish from the analysis"
    assert row["distribution"][9] == 3  # [4.5, 5.0] — all three
    assert row["mode_range"] == "4.5-5.0"


def test_distribution_percentages_sum_to_one_and_mode_is_the_fullest_bin():
    votes = [{"A": 1.0}, {"A": 1.2}, {"A": 4.0}]
    out = get_score_distribution_analysis(votes)

    row = out["details"][0]
    assert sum(row["percentages"]) == pytest.approx(1.0)
    assert row["percentages"][2] == pytest.approx(2 / 3)  # [1.0, 1.5)
    assert row["mode_range"] == "1.0-1.5"


def test_distribution_orders_candidates_by_ballot_count():
    votes = [{"A": 1, "B": 1}, {"B": 2}, {"B": 3}]
    out = get_score_distribution_analysis(votes)

    assert [r["candidate"] for r in out["details"]] == ["B", "A"]
    assert out["method"] == "Score Distribution Analysis"


# ------------------------------------------------------------ majority judgment


@pytest.mark.parametrize(
    "utility, grade",
    [
        (0.0, 0), (0.16, 0),
        (0.17, 1), (0.32, 1),
        (0.33, 2), (0.49, 2),
        (0.50, 3), (0.66, 3),
        (0.67, 4), (0.82, 4),
        (0.83, 5), (1.0, 5),
    ],
)
def test_utility_to_grade_boundaries_are_inclusive_lower_bounds(utility, grade):
    """Each threshold is the LOWER bound of its grade. Both sides of every
    boundary are pinned, so shifting any threshold — or flipping >= to > —
    changes at least one of these."""
    assert _utility_to_grade(utility) == grade


def test_mj_median_takes_the_lower_middle_on_an_even_count():
    """MJ's median must stay a real grade, never an average of two — so an even
    count uses the lower of the two middles."""
    assert _mj_median_grade([0, 1, 4, 5]) == 1
    assert _mj_median_grade([0, 2, 4]) == 2
    assert _mj_median_grade([]) == 0


def test_mj_majority_gauge_counts_strictly_above_and_below():
    """Voters AT the median count in neither p nor q."""
    p, q = _mj_majority_gauge([0, 1, 3, 3, 5], median=3)

    assert p == pytest.approx(1 / 5)  # one grade of 5
    assert q == pytest.approx(2 / 5)  # grades 0 and 1


def test_majority_judgment_highest_median_wins_over_higher_mean():
    """A is graded Excellent by a minority and À Rejeter by the rest; B is
    solidly Bien throughout. MJ elects B — the resistance to enthusiastic
    minorities is the reason the method exists."""
    votes = (
        [{"A": 1.0, "B": 0.55}] * 2
        + [{"A": 0.0, "B": 0.55}] * 3
    )
    out = get_majority_judgment_winner(votes)

    assert out["winner"] == "B"
    assert out["medians"]["B"] == "Bien"
    assert out["medians"]["A"] == "À Rejeter"


def test_majority_judgment_breaks_an_equal_median_by_the_gauge():
    """Both candidates sit at the same median grade, so the majority gauge (p−q)
    decides: the one with more grades ABOVE the median wins."""
    votes = [
        {"A": 0.90, "B": 0.55},  # A Excellent, B Bien
        {"A": 0.55, "B": 0.55},  # both Bien
        {"A": 0.55, "B": 0.20},  # A Bien,      B Passable
    ]
    out = get_majority_judgment_winner(votes)

    assert out["medians"]["A"] == out["medians"]["B"] == "Bien"
    assert out["winner"] == "A"


def test_majority_judgment_reports_a_full_grade_distribution():
    votes = [{"A": 1.0}, {"A": 1.0}, {"A": 0.0}]
    out = get_majority_judgment_winner(votes)

    assert out["grade_distributions"]["A"] == [1, 0, 0, 0, 0, 2]
    assert out["grades"]["A"]["Excellent"] == 2
    assert out["grades"]["A"]["À Rejeter"] == 1


def test_majority_judgment_empty_ballots_have_no_winner():
    out = get_majority_judgment_winner([])

    assert out["winner"] is None
    assert out["grades"] == {}
    assert out["medians"] == {}


# ---------------------------------------------------------------- evaluative


def test_evaluative_nets_approvals_against_rejections():
    """+1 at or above 0.67, −1 at or below 0.33, 0 between.
    A: +1,+1,−1 → net 1.  B: 0,0,0 → net 0.  C: −1,−1,−1 → net −3.
    """
    votes = [
        {"A": 0.9, "B": 0.5, "C": 0.1},
        {"A": 0.7, "B": 0.5, "C": 0.2},
        {"A": 0.2, "B": 0.5, "C": 0.3},
    ]
    out = get_evaluative_winner(votes)

    assert out["winner"] == "A"
    assert out["scores"] == {"A": 1, "B": 0, "C": -3}
    assert out["distribution"]["A"] == {"+1": 2, "0": 0, "-1": 1}
    assert out["distribution"]["B"] == {"+1": 0, "0": 3, "-1": 0}


@pytest.mark.parametrize(
    "utility, bucket",
    [(0.67, "+1"), (0.66, "0"), (0.34, "0"), (0.33, "-1")],
)
def test_evaluative_thresholds_are_inclusive_on_both_sides(utility, bucket):
    """Both defaults are inclusive: >= approve, <= reject. Each pair straddles a
    boundary, so relaxing or tightening either comparison flips a case."""
    out = get_evaluative_winner([{"A": utility}])

    assert out["distribution"]["A"][bucket] == 1


def test_evaluative_thresholds_are_configurable():
    votes = [{"A": 0.5, "B": 0.4}]
    out = get_evaluative_winner(votes, threshold_approve=0.5, threshold_reject=0.4)

    assert out["scores"] == {"A": 1, "B": -1}


def test_evaluative_missing_candidate_counts_as_a_rejection():
    """A ballot that omits a candidate is read as utility 0.0, which is below the
    rejection threshold — silence is not neutrality here."""
    votes = [{"A": 0.9, "B": 0.9}, {"A": 0.9}]
    out = get_evaluative_winner(votes)

    assert out["scores"] == {"A": 2, "B": 0}
    assert out["distribution"]["B"] == {"+1": 1, "0": 0, "-1": 1}


def test_evaluative_returns_no_winner_when_every_net_is_zero():
    """Pins CURRENT behaviour, which is worth flagging rather than changing here.

    The guard reads `if not any(net.values())` and its comment says "no
    approvals" — but those are different things. Here every voter approves one
    candidate and rejects the other, so there are four approvals, and the nets
    merely cancel. The documented alphabetical tie-break would elect A.

    Whether an all-square result should elect the alphabetical first or elect
    nobody is a question about the voting rule, not about the code, so it is left
    to a deliberate decision rather than silently altered by a test author.
    """
    votes = [{"A": 0.9, "B": 0.1}, {"A": 0.1, "B": 0.9}]
    out = get_evaluative_winner(votes)

    assert out["scores"] == {"A": 0, "B": 0}
    assert out["distribution"]["A"] == {"+1": 1, "0": 0, "-1": 1}
    assert out["winner"] is None


def test_evaluative_breaks_a_real_tie_alphabetically():
    votes = [{"B": 0.9, "A": 0.9}]
    out = get_evaluative_winner(votes)

    assert out["scores"] == {"A": 1, "B": 1}
    assert out["winner"] == "A"


def test_evaluative_empty_ballots_have_no_winner():
    assert get_evaluative_winner([])["winner"] is None
    assert get_evaluative_winner([{}])["winner"] is None
