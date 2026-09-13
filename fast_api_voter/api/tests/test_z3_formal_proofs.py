"""Formal (SMT) proofs over symbolic vote counts, not sampled ones (Lot 4.6,
PLAN_SOLIDITE_TECHNIQUE.md — an explicitly risk-accepted experiment: "may
well fail, and a documented failure is excellent material").

Lots 4.1-4.4 established axiom compliance by fuzzing, third-party oracle
cross-check, exhaustive enumeration of small profiles, and property testing
on a wider domain -- all of them checking FINITELY MANY concrete profiles,
however many. This file proves two of those same facts a different way: by
asking Z3 to search for a counterexample among ALL non-negative integer
vote-count vectors for n candidates (an infinite domain) and confirming
UNSAT -- literally every possible electorate at that candidate count, not a
sample of them, however large.

**What worked**: minimax and Schulze's Condorcet winner criterion, encoded
directly as linear arithmetic (margins) plus, for Schulze, an unrolled
Floyd-Warshall widest-path computation over a FIXED small n. Both are
UNSAT (no counterexample exists) up to n=7 candidates in well under a
minute, confirmed reproducible.

**What very much did NOT work on the first attempt, and why it matters
more than the successes**: an IRV encoding of the same style initially
returned a false UNSAT for "can IRV elect a Condorcet loser?" -- a question
already answered YES by hand-verified counterexamples elsewhere in this
suite (`test_condorcet_loser_irv_can_be_violated`,
test_voting_criteria_matrix.py). The encoding silently omitted this
codebase's own tie-breaking convention (eliminate ALL candidates tied for
fewest first-preferences, not just a unique minimum) -- a real algorithmic
detail, easy to leave out, that made the "proof" describe a DIFFERENT,
subtly wrong voting rule instead of the real `get_irv_winner`. Once fixed
(cross-checked against that known counterexample before trusting it
again), Z3 also found a NEW, PROVABLY MINIMAL 7-ballot counterexample via
optimization -- a genuine capability sampling can't offer (a minimality
*proof*, not just a smaller example than the ones found by chance). That
IRV encoding is NOT committed here: it is genuinely more fragile (more
case-splitting, more ways to silently misencode a real behaviour) than the
arithmetic-only methods below, for a payoff Lots 4.1-4.4 already delivered
by other means. Full account, including the false-UNSAT episode and the
minimal counterexample it found:
docs/exploration/EXP-002-z3-formal-voting-proofs.md.

**Scope decision, not oversight**: only the Condorcet winner criterion, only
minimax and Schulze. This is the experiment's genuinely load-bearing result
(clean, general, fast, reproducible); broadening to other criteria or
other Condorcet-completion methods (ranked pairs, black, kemeny) is real
follow-up work, not attempted here given the encoding-faithfulness risk
the IRV episode demonstrated firsthand.
"""
from __future__ import annotations

import itertools
from typing import Callable

from z3 import And, If, Int, Not, Or, Solver, unsat

MAX_CANDIDATES_TO_CHECK = 6  # see docs/exploration/EXP-002 for the n=7 timing

Margin = Callable[[int, int], object]


def _pairwise_margin_fn(perms: list[tuple[int, ...]], c: list[Int]) -> Margin:
    """margin(i, j) as a Z3 linear expression over the symbolic per-ballot-type
    vote counts `c` -- positive means i is preferred to j by more voters than
    the reverse. Ballot-type membership (does permutation k rank i before j?)
    is a static fact, so every coefficient is a fixed +1/-1, not itself a
    variable: this stays linear arithmetic regardless of n."""

    def margin(i: int, j: int) -> object:
        total = 0
        for k, perm in enumerate(perms):
            total = total + (c[k] if perm.index(i) < perm.index(j) else -c[k])
        return total

    return margin


def _is_condorcet_winner(cands: list[int], margin: Margin, x: int) -> object:
    return And([margin(x, y) > 0 for y in cands if y != x])


def _minimax_score(cands: list[int], margin: Margin, x: int) -> object:
    vals = [margin(x, y) for y in cands if y != x]
    score = vals[0]
    for v in vals[1:]:
        score = If(v < score, v, score)
    return score


def _minimax_is_winner(cands: list[int], margin: Margin, x: int) -> object:
    score = _minimax_score(cands, margin, x)
    return And([score >= _minimax_score(cands, margin, y) for y in cands if y != x])


def _schulze_path_strengths(cands: list[int], margin: Margin) -> dict[tuple[int, int], object]:
    """Widest-path (beat-path) strengths via an unrolled Floyd-Warshall --
    a fixed sequence of expressions for fixed n, no recursion or quantifiers
    needed."""
    p: dict[tuple[int, int], object] = {}
    for i in cands:
        for j in cands:
            if i != j:
                m = margin(i, j)
                p[(i, j)] = If(m > 0, m, 0)
    for k in cands:
        for i in cands:
            if i == k:
                continue
            for j in cands:
                if j == k or j == i:
                    continue
                alt = If(p[(i, k)] < p[(k, j)], p[(i, k)], p[(k, j)])
                p[(i, j)] = If(alt > p[(i, j)], alt, p[(i, j)])
    return p


def _schulze_is_winner(cands: list[int], margin: Margin, x: int) -> object:
    p = _schulze_path_strengths(cands, margin)
    return And([p[(x, y)] >= p[(y, x)] for y in cands if y != x])


def _no_condorcet_winner_counterexample(n: int, is_winner_fn: Callable[[list[int], Margin, int], object]) -> bool:
    """True iff Z3 PROVES no counterexample exists: for every non-negative
    integer vote-count vector over the n! ballot types, whenever a Condorcet
    winner exists, is_winner_fn agrees with it."""
    cands = list(range(n))
    perms = list(itertools.permutations(cands))
    c = [Int(f"c{i}") for i in range(len(perms))]
    margin = _pairwise_margin_fn(perms, c)

    s = Solver()
    s.add([ci >= 0 for ci in c])
    clauses = [
        And(_is_condorcet_winner(cands, margin, x), Not(is_winner_fn(cands, margin, x)))
        for x in cands
    ]
    s.add(Or(clauses))
    return s.check() == unsat


def test_minimax_satisfies_condorcet_winner_criterion_for_all_electorates():
    """UNSAT for every n up to MAX_CANDIDATES_TO_CHECK: no non-negative
    integer vote-count vector over the n! ballot types makes a Condorcet
    winner exist without minimax electing them. Not a sample -- literally
    every possible electorate at that candidate count."""
    for n in range(3, MAX_CANDIDATES_TO_CHECK + 1):
        assert _no_condorcet_winner_counterexample(n, _minimax_is_winner), (
            f"Z3 found a vote-count vector at n={n} where a Condorcet winner "
            f"exists but minimax doesn't elect them"
        )


def test_schulze_satisfies_condorcet_winner_criterion_for_all_electorates():
    for n in range(3, MAX_CANDIDATES_TO_CHECK + 1):
        assert _no_condorcet_winner_counterexample(n, _schulze_is_winner), (
            f"Z3 found a vote-count vector at n={n} where a Condorcet winner "
            f"exists but Schulze doesn't elect them"
        )
