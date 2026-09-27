"""Unit tests for Split Cycle (Holliday & Pacuit, 2021): discard a majority
defeat when it is the weakest link of a majority cycle; a candidate wins iff
no surviving defeat lands on it."""

from api.engine.utils.simulation_ranked_utils import (
    get_split_cycle_winner,
    get_schulze_winner,
    get_ranked_pairs_winner,
    get_condorcet_winner,
)
from api.engine.utils.simulation_metrics import compare_all_methods


def test_split_cycle_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head -> no defeat lands on A.
    assert get_condorcet_winner(ballots) == "A"
    assert get_split_cycle_winner(ballots) == "A"


def test_split_cycle_resolves_a_simple_top_cycle():
    # Rock-paper-scissors cycle: margins B>C=7, A>B=5, C>A=1. The weakest
    # link (C>A) is discarded, leaving A undefeated -- same answer as
    # Schulze/Ranked Pairs on this simple 3-candidate cycle.
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_split_cycle_winner(ballots) == "A"


def test_split_cycle_can_diverge_from_schulze_and_ranked_pairs():
    """Found by random search: on this 4-candidate cyclic profile, Split Cycle's
    "discard the weakest link of EVERY cycle" rule leaves a different candidate
    undefeated than Ranked Pairs' strongest-majorities-first lock order.

    CORRECTED. This docstring used to add Schulze to that list and call the whole
    thing "a real algorithmic difference, not a tie-break artefact". For Schulze
    it was precisely a tie-break artefact: B and C BOTH satisfy the Schulze
    condition here, with strongest paths of 8 in each direction between them.
    The old assertion of "C" recorded nothing but which candidate happened to
    appear first in the ballot list, and shuffling these fifteen ballots flipped
    it. The anonymity fix breaks that tie alphabetically, so Schulze now reports
    B — the same candidate Split Cycle elects, for an entirely different reason.

    Ranked Pairs' "C" is the genuine divergence, and it is stable under
    permutation."""
    ballots = [
        ["C", "A", "B", "D"],
        ["C", "D", "B", "A"],
        ["B", "A", "D", "C"],
        ["C", "B", "D", "A"],
        ["D", "C", "A", "B"],
        ["B", "D", "C", "A"],
        ["B", "D", "C", "A"],
        ["B", "D", "A", "C"],
        ["B", "A", "D", "C"],
        ["B", "D", "C", "A"],
        ["C", "D", "A", "B"],
        ["A", "B", "C", "D"],
        ["C", "D", "B", "A"],
        ["C", "D", "A", "B"],
        ["D", "C", "B", "A"],
    ]
    assert get_condorcet_winner(ballots) is None
    # Schulze ties B and C; the alphabetical tie-break settles it on B.
    assert get_schulze_winner(ballots) == "B"
    assert get_ranked_pairs_winner(ballots) == "C"
    assert get_split_cycle_winner(ballots) == "B"


def test_split_cycle_single_and_empty():
    assert get_split_cycle_winner([]) is None
    assert get_split_cycle_winner([["A"]]) == "A"


def test_split_cycle_margin_must_be_signed_not_a_total_comparison_count():
    """Locks the sign of `margin(i, j) = pw[i][j] - pw[j][i]`. PR #157's
    mutation-testing baseline found `-` -> `+` survives every other test in
    this file: `+` makes margin symmetric (margin(i,j) == margin(j,i)),
    which makes every candidate mutually "undefeated" and silently routes
    every case here into the Borda-tiebreak-among-all-candidates fallback --
    which happens to still agree with the correct winner on the profiles
    above. This profile was found by random search specifically because it
    does NOT coincide: the correct (signed-margin) winner is the Condorcet
    winner B, but the symmetric-margin mutant returns C instead."""
    ballots = [
        ["C", "A", "B", "D"],
        ["B", "C", "D", "A"],
        ["D", "C", "A", "B"],
        ["A", "B", "C", "D"],
        ["B", "C", "A", "D"],
        ["B", "C", "A", "D"],
        ["C", "D", "B", "A"],
        ["C", "D", "A", "B"],
        ["B", "C", "A", "D"],
    ]
    assert get_condorcet_winner(ballots) == "B"
    assert get_split_cycle_winner(ballots) == "B"


def test_compare_all_methods_registers_split_cycle():
    names = ["A", "B", "C"]
    matrix = {
        i: {n: float(u) for n, u in zip(names, utils)}
        for i, utils in enumerate(
            [(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3 + [(0.5, 0.0, 1.0)] * 2
        )
    }
    res = compare_all_methods(
        [{"id": vid} for vid in matrix],
        [{"name": n} for n in names],
        [],
        override_utilities=matrix,
    )
    assert "split_cycle" in res["methods"]
    assert res["methods"]["split_cycle"]["winner"] in names


# The tests below close mutmut's 27 surviving mutants for get_split_cycle_winner
# (2026-09-13 baseline). All profiles were found by exhaustively probing every
# survivor's actual generated mutant function (mutmut's own trampoline dispatch,
# not a hand simulation) so each assertion is checked against ground truth, not
# a guess about what the algorithm "should" do. 5 of the 27 are documented here
# as genuine equivalent mutants rather than tested, with the reasoning that made
# each one provably unkillable:
#
# - The `blank_candidate_name` default value ("" -> "XXXX") is only read inside
#   `if not winners: return get_borda_winner(votes, blank_candidate_name)`.
#   Split Cycle's own theorem guarantees a non-empty winner set for any input
#   (Holliday & Pacuit 2021) -- confirmed empirically too: 300,000 random
#   profiles (2-6 candidates) never once produced an empty `winners`. That
#   branch is unreachable, so no value of its only parameter can matter.
# - `if i != j and margin(i, j) > 0` -> `if i != j or margin(i, j) > 0`: for
#   i == j this is False either way (margin(i, i) is always 0). For i != j
#   with margin(i, j) > 0, both forms agree (True). The only new case the
#   mutant adds is i != j with margin(i, j) <= 0, where it sets
#   s[i][j] = margin(i, j) instead of leaving the pre-initialized 0. That can
#   only ever make an s[][] entry *more negative* than the correct 0 --  never
#   larger -- and the only place s[][] values are read is
#   `margin(a, x) > s[x][a]` where margin(a, x) is already required to be > 0.
#   A smaller (more negative) s[x][a] can only make that comparison MORE true,
#   never flip it from True to False, so `winners` can never change.
# - `margin(i, j) > 0` -> `margin(i, j) >= 0` on the same line: the only value
#   this newly includes is margin(i, j) == 0, and s[i][j] is already
#   initialized to 0 -- setting it to 0 again is a no-op.
# - `margin(a, x) > 0 and margin(a, x) > s[x][a]` -> `margin(a, x) >= 0 and
#   margin(a, x) > s[x][a]`: the newly-included case (margin(a, x) == 0) only
#   matters if `0 > s[x][a]`, i.e. s[x][a] is negative. But s[x][a] is built
#   entirely from `max(..., min(non-negative values))` starting from a
#   0-initialized table -- it can never be negative. The new case is
#   unreachable given the rest of the (unmutated) function.
# - `borda_scores: dict[str, int] = {c: 0 for c in candidates}` -> `{c: 1 ...}`:
#   every candidate gets the same +1 exactly once, before any ballot is
#   counted. A uniform additive shift never changes which candidate has the
#   highest score, so `min(winners, key=lambda c: (-borda_scores[c], c))`
#   picks the same candidate regardless.
def test_split_cycle_widest_path_only_propagates_positive_margin_edges():
    """PR #157-style gap: the widest-path table's own edge population line,
    `if i != j and margin(i, j) > 0`, is what the mutmut survivors 13
    (`i == j and ...`), 25 (`if i != k` instead of skipping i == k), 27
    (`j not in (i, k)` instead of skipping j in (i, k)) and 41 (first `and` in
    the winners formula turned into `or`) all sit on or next to. This profile
    (margins: B>A=3, A>C=11, A>D=1, B>C=3, D>B=7, D>C=3) makes D the sole
    Split Cycle winner via a real multi-hop discard: D loses head-to-head to
    A directly (margin 1), but D's own return path back to A is worth 3 --
    stronger than that direct margin, so A>D is the weakest link of a cycle
    and gets discounted, leaving D undefeated. Each of these four mutations
    independently corrupts that path computation enough to (wrongly) hand the
    win to A instead -- verified directly against each generated mutant."""
    ballots = (
        [["B", "A", "D", "C"]] * 2
        + [["A", "C", "D", "B"]] * 4
        + [["D", "B", "A", "C"]] * 5
    )
    assert get_split_cycle_winner(ballots) == "D"


def test_split_cycle_widest_path_edge_threshold_is_strictly_greater_than_zero():
    """Mutant 19 turns the same edge line's `margin(i, j) > 0` into
    `margin(i, j) > 1`. Margins here: A>B=1, C>A=3, D>A=5, B>C=3, B>D=1, D>C=3
    -- B>D is a margin of exactly 1, the one value `> 0` and `> 1` disagree
    on: the mutant drops that edge from the widest-path table entirely.
    Verified directly against the real generated mutant (not hand-derived):
    dropping that edge is enough to flip the function's return value from D
    to B on this profile."""
    ballots = (
        [["A", "B", "D", "C"]] * 1
        + [["B", "D", "C", "A"]] * 3
        + [["C", "D", "A", "B"]] * 2
        + [["C", "B", "A", "D"]] * 2
        + [["D", "A", "B", "C"]] * 3
    )
    assert get_split_cycle_winner(ballots) == "D"


def test_split_cycle_widest_path_inner_skip_must_not_short_circuit_the_loop():
    """Mutants 26 and 28 each turn one of the two `continue` statements inside
    the Floyd-Warshall-style triple loop (skipping i == k, and skipping
    j in (i, k)) into `break` instead -- which abandons the rest of that
    inner loop's candidates entirely rather than skipping just the one that
    doesn't apply. Margins: B>A=11, A>C=1, D>A=11, B>C=1, D>B=9, C>D=1. The
    correct widest-path computation makes D the Borda-tiebreak winner over
    the {C, D} winner set; breaking early instead of continuing starves later
    (i, j) pairs of a path update they need, and the tie-break falls to C."""
    ballots = (
        [["A", "C", "B", "D"]] * 1
        + [["C", "D", "B", "A"]] * 5
        + [["B", "C", "D", "A"]] * 1
        + [["D", "B", "A", "C"]] * 6
    )
    assert get_split_cycle_winner(ballots) == "D"


def test_split_cycle_widest_path_comparison_must_be_strict():
    """Mutant 54 turns the winners formula's `margin(a, x) > s[x][a]` into
    `>=`. Margins: A>B=3, C>A=5, A>D=13, B>C=3, B>D=7, C>D=7 -- built so a
    direct defeat's margin lands EXACTLY equal to the best path discounting
    it for one candidate. Under strict `>` that defeat is discarded (the
    margin doesn't exceed the path, so it's the cycle's weakest link) and C
    wins the {B, C} tie-break; under `>=` the same defeat now counts as
    undischarged, flipping who ends up in the winner set and handing it to A
    instead."""
    ballots = (
        [["B", "C", "A", "D"]] * 5
        + [["C", "B", "D", "A"]] * 1
        + [["A", "C", "B", "D"]] * 1
        + [["A", "B", "D", "C"]] * 4
        + [["C", "A", "D", "B"]] * 4
    )
    assert get_split_cycle_winner(ballots) == "C"


def test_split_cycle_never_falls_back_to_unrestricted_borda_when_winners_exist():
    """Mutant 58 turns `if not winners:` into `if winners:` -- and because
    Split Cycle's winner set is never empty (see the equivalent-mutants note
    above), this makes the mutant take the "empty winners" branch on EVERY
    input, always returning `get_borda_winner(votes, ...)` computed over ALL
    candidates instead of ever using the real Split Cycle winner set or its
    restricted Borda tie-break. This profile's Split Cycle winners are
    {A, D} with Borda scores A=16, D=17 -- restricted to just those two, D
    correctly wins. But B (defeated, not a Split Cycle winner at all) also
    scores 17 over the full candidate set, tying D there and winning the
    alphabetical fallback -- so plain unrestricted Borda picks B instead."""
    ballots = (
        [["B", "C", "D", "A"]] * 4
        + [["D", "C", "A", "B"]] * 1
        + [["A", "D", "B", "C"]] * 5
    )
    assert get_split_cycle_winner(ballots) == "D"


def test_split_cycle_multi_winner_borda_tiebreak_favors_higher_score():
    """The Borda-tiebreak block below the winners computation is only
    reached when Split Cycle's own winner set has more than one member --
    every other test in this file resolves to a single winner and returns
    before ever reaching it, which is exactly why mutants 55 (`== 1` ->
    `!= 1`), 56 (`== 1` -> `== 2`), 70 (`if c in borda_scores` -> `not in`),
    72 (`+=` -> `-=`), 73 (`n - 1 - pos` -> `n - 1 + pos`), 77 and 79 (drop
    the `key=` function entirely) and 81 (flip the score's sign in the key)
    all survive the rest of the suite. Two ballots -- ['B','C','A'] and
    ['C','A','B'] -- tie A and B and C's pairwise record such that Split
    Cycle's winner set is exactly {B, C} (A is defeated), with Borda scores
    B=2, C=3: C must win the tie-break."""
    ballots = [["B", "C", "A"], ["C", "A", "B"]]
    assert get_split_cycle_winner(ballots) == "C"


def test_split_cycle_multi_winner_borda_tiebreak_handles_dict_format_ballots():
    """Same two-winner profile as above, in dict-ballot format
    (`{"ranking": [...]}`). Mutants 59 (`is_dict = _is_dict_format(votes)` ->
    `None`) and 60 (`_is_dict_format(votes)` -> `_is_dict_format(None)`) both
    leave `is_dict` falsy for these dict ballots, and mutant 65 passes `None`
    for `is_dict` directly to `_get_ranking` -- all three make `_get_ranking`
    return the whole `{"ranking": [...]}` dict instead of the ranking list
    inside it, corrupting every Borda contribution in the tie-break loop.
    Plain-list ballots can't distinguish these: `is_dict=False` and
    `is_dict=None` behave identically for list ballots, which is exactly why
    the profile above alone doesn't kill them."""
    ballots = [{"ranking": ["B", "C", "A"]}, {"ranking": ["C", "A", "B"]}]
    assert get_split_cycle_winner(ballots) == "C"


def test_split_cycle_borda_tiebreak_position_constant_must_be_n_minus_1():
    """Mutant 74 turns the Borda contribution `n - 1 - pos` into `n + 1 - pos`.
    When every ballot ranks all candidates, `n` is constant across ballots and
    this constant-term shift lands equally on every candidate every time they
    appear -- a no-op, which is why full-ranking profiles alone (like the one
    above) don't kill it. A partial ballot that omits a candidate breaks that
    symmetry: here, five voters submit a bare `['A']` ballot, so A collects
    the shifted constant an extra 5 times with no `pos` to offset it, which
    is enough to flip the {A, B} tie-break from B to A under the mutant."""
    ballots = (
        [["A", "B", "C"]] * 6
        + [["C", "B", "A"]] * 4
        + [["B", "A", "C"]] * 5
        + [["B", "C", "A"]] * 2
        + [["A"]] * 5
    )
    assert get_split_cycle_winner(ballots) == "B"


def test_split_cycle_borda_tiebreak_position_constant_must_not_shift_by_two():
    """Mutant 75 turns the same contribution into `n - 2 - pos`. This profile
    ties A and B's Borda score exactly under the correct formula (10 vs 10,
    A winning only the alphabetical fallback in `(-borda_scores[c], c)`); the
    mutant's extra -1-per-appearance shift lands unevenly across the partial
    ballots (`['A', 'C']` and four bare `['C']`s) and breaks the tie the
    other way, to B."""
    ballots = (
        [["B", "A", "C"]] * 5
        + [["A", "C", "B"]] * 2
        + [["A", "C"]] * 1
        + [["C"]] * 4
    )
    assert get_split_cycle_winner(ballots) == "A"
