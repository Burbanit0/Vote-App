"""Named, sourced counterexamples from the social choice literature (Lot 4.5,
PLAN_SOLIDITE_TECHNIQUE.md).

Lots 4.1/4.2/4.3/4.4 discovered classification facts empirically (fuzzing,
third-party oracles, exhaustive search, property testing) and verified them
by hand afterwards. This file works the other direction: each test starts
from a *named, citable* result already established in the literature, and
checks that this engine reproduces it — a different kind of confidence
(these are facts the field has scrutinized for decades, not facts this
project discovered), and directly reusable as teaching material (THEORY.md
links back to these tests; see PLAN_SOLIDITE_TECHNIQUE.md § 4.5 for the
citation key each fixture uses, all recorded in
docs/research/bibliography.bib).

**Scope.** Four examples, chosen for being both classic and small enough to
verify completely by hand: Condorcet's paradox, a Saari-style demonstration
that positional rules can disagree completely, the motivating clone-
independence failure behind Tideman's Ranked Pairs, and the no-show paradox
(closing a small, concrete piece of the participation criterion Lot 4.1
deferred in full — one named example, not the broader fuzzing sweep that
was, and remains, out of scope there).
"""
from __future__ import annotations

from api.engine.utils.simulation_ranked_utils import (
    get_anti_plurality_winner,
    get_borda_winner,
    get_condorcet_winner,
    get_copeland_winner,
    get_irv_winner,
    get_plurality_winner,
    get_ranked_pairs_winner,
)


def test_condorcet_paradox():
    """Condorcet (1785) [condorcet1785, docs/research/bibliography.bib]: the
    original demonstration that majority rule can be cyclic. Three voters,
    three candidates, each candidate beats exactly one other and loses to
    exactly one other -- no Condorcet winner exists, the founding
    counterexample to "majority preference is transitive"."""
    rankings = [
        ["A", "B", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
    ]
    # Every pairwise contest is a bare 2-1 majority, and they form a cycle:
    # A>B, B>C, C>A.
    assert get_condorcet_winner(rankings) is None


def test_saari_positional_rules_disagree():
    """Saari (1995) [saari1995, docs/research/bibliography.bib], *Basic
    Geometry of Voting*: positional scoring rules are a one-parameter family
    (the weight given to 2nd place, between last-place's 0 and first-place's
    1), and generic profiles can make DIFFERENT points in that family elect
    DIFFERENT winners -- Saari's geometric account of why this isn't a rare
    fluke but close to the norm. This is the smallest profile found (a
    4-ballot search over all profiles up to 17 ballots) where plurality
    (weight 0), Borda (weight 1/2) and anti-plurality (weight 1) each elect
    a different candidate from the exact same preferences."""
    rankings = [
        ["B", "A", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
        ["C", "A", "B"],
    ]
    assert get_plurality_winner(rankings) == "B"  # most first-place votes
    assert get_borda_winner(rankings) == "C"  # most total positional points
    assert get_anti_plurality_winner(rankings) == "A"  # fewest last-place votes


def test_tideman_ranked_pairs_motivation():
    """Tideman (1987) [tideman1987, docs/research/bibliography.bib],
    "Independence of Clones as a Criterion for Voting Rules": introduces
    Ranked Pairs specifically to fix a real flaw in naive Condorcet-
    completion methods like Copeland's (win-minus-loss score) -- cloning a
    candidate can change a Copeland winner by shifting the net-score
    balance. This profile (found empirically in Lot 4.4,
    PLAN_SOLIDITE_TECHNIQUE.md, while property-testing the client engine)
    shows the failure concretely, and that Ranked Pairs is unaffected by
    the exact same clone on the exact same profile -- Tideman's motivating
    problem, and his fix, both reproduced."""
    rankings = [
        ["B", "E", "C", "A", "D"],
        ["E", "D", "C", "B", "A"],
        ["C", "D", "B", "A", "E"],
    ]
    assert get_copeland_winner(rankings) == "C"
    assert get_ranked_pairs_winner(rankings) == "C"

    cloned = [
        ["B", "E", "F", "C", "A", "D"],  # E cloned as F, inserted right after E
        ["E", "F", "D", "C", "B", "A"],
        ["C", "D", "B", "A", "E", "F"],
    ]
    assert get_copeland_winner(cloned) == "E"  # a non-winner's clone flips it
    assert get_ranked_pairs_winner(cloned) == "C"  # unaffected


def test_no_show_paradox():
    """Fishburn & Brams (1983) [fishburn_brams1983,
    docs/research/bibliography.bib], "Paradoxes of Preferential Voting":
    names the no-show paradox -- a voter can get a WORSE outcome (by their
    own sincere ranking) by turning out than by staying home, under IRV.
    Moulin (1988) later proved every Condorcet-consistent rule is
    susceptible to some form of this; IRV's own version doesn't even need
    Condorcet-consistency, just its round-by-round elimination order to
    shift.

    One concrete voter in this 8-ballot profile: their sincere ballot ranks
    B first and A last. Casting it elects A -- their LAST choice. Staying
    home elects D -- their 2nd choice. They would rather not have voted at
    all than vote sincerely for their own favorite. Hand-traced round by
    round before trusting it (see PLAN_SOLIDITE_TECHNIQUE.md § 4.5): with
    everyone voting, the first elimination round cuts C alone (fewest
    first-preferences), the second cuts D alone, leaving A with a majority
    over B. Remove that one B-D-C-A ballot and C and B now tie for fewest
    first-preferences and are eliminated TOGETHER instead of one at a time,
    which changes who reaches the final round entirely -- D ends up with a
    majority over A instead."""
    rankings = [
        ["A", "D", "B", "C"],
        ["A", "D", "B", "C"],
        ["D", "C", "A", "B"],
        ["D", "C", "A", "B"],
        ["C", "B", "D", "A"],
        ["B", "D", "C", "A"],
        ["B", "D", "C", "A"],
        ["A", "C", "D", "B"],
    ]
    assert get_irv_winner(rankings) == "A"

    voter = rankings[5]
    assert voter == ["B", "D", "C", "A"]
    abstained = rankings[:5] + rankings[6:]
    new_winner = get_irv_winner(abstained)
    assert new_winner == "D"
    # D is ranked ABOVE A on this voter's own sincere ballot -- staying home
    # got them a candidate they prefer to the one their vote helped elect.
    assert voter.index(new_winner) < voter.index("A")
