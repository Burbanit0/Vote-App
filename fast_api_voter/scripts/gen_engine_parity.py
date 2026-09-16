"""Golden-fixture generator for the client⇄backend voting-engine parity test.

The Playground computes winners client-side (voter-app/src/lib/playgroundVoting.ts);
this repo's authoritative engine is the (tested) Python backend. To guarantee the
two agree, we run the backend rules on a set of seeded ranking profiles and dump
the winners; a Vitest test then asserts the TS client returns the same winner.

Run from anywhere:  PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py
Re-run whenever a ranked rule changes on either side — CI enforces it
(scripts/check_engine_parity_drift.sh regenerates and fails on any diff).

Voter counts are ODD so every pairwise majority is strict — that removes the
tie-break ambiguity that would otherwise make Condorcet methods diverge for
reasons unrelated to the algorithm.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import sys
from typing import Any

# Reproducibility: `random.Random(SEED)` alone is NOT enough. The engine iterates
# sets/dicts of candidate names, so Python's per-process string-hash randomisation
# changes tie-detection order, which changes how many times strict_winner() re-rolls,
# which shifts the whole RNG stream — three runs used to give three different
# fixtures. That made "just re-run the generator" produce a 200 kB spurious diff,
# so nobody re-ran it, so the parity test drifted against a frozen snapshot.
# PYTHONHASHSEED is read at interpreter start-up, so it cannot be set from here —
# refuse to run rather than silently emit a fixture nobody else can reproduce.
if os.environ.get("PYTHONHASHSEED") != "0":
    sys.exit(
        "PYTHONHASHSEED=0 is required for a reproducible fixture. Run:"
        "\n  PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py"
        "\nor just ./scripts/check_engine_parity_drift.sh, which sets it for you."
    )

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from api.engine.utils.simulation_ranked_utils import (  # noqa: E402
    get_anti_plurality_winner,
    get_approval_winner_sincere,
    get_baldwin_winner,
    get_benham_winner,
    get_black_winner,
    get_borda_winner,
    get_bucklin_winner,
    get_coombs_winner,
    get_copeland_winner,
    get_dowdall_winner,
    get_irv_winner,
    get_kemeny_young_winner,
    get_minimax_winner,
    get_nanson_winner,
    get_plurality_winner,
    get_ranked_pairs_winner,
    get_raynaud_winner,
    get_river_winner,
    get_schulze_winner,
    get_smith_irv_winner,
    get_split_cycle_winner,
    get_two_round_winner,
)
from api.engine.utils.simulation_score_utils import (  # noqa: E402
    get_simple_score_winner,
    get_star_voting_winner,
    get_cumulative_winner,
    get_majority_judgment_winner,
    get_maximin_score_winner,
    get_nash_winner,
)

# Client Rule id → backend winner fn. Only the purely ordinal rules both engines
# share (score/approval/STAR/MJ take cardinal ballots; random_ballot is a lottery).
RULES = {
    "plurality": get_plurality_winner,
    "two_round": get_two_round_winner,
    "borda": get_borda_winner,
    "irv": get_irv_winner,
    "coombs": get_coombs_winner,
    # The client's "condorcet" rule is labelled "Condorcet (Copeland)" in
    # RULE_LABELS and always resolves to a winner (Copeland's method, which
    # elects the Condorcet winner when one exists but doesn't return None
    # otherwise) -- get_condorcet_winner is the wrong backend twin: it's the
    # strict criterion (Optional[str], often None). Every scenario here that
    # used to compare against it happened to have a real Condorcet winner
    # (where the two functions necessarily agree), so this was masked until
    # an exhaustive small-profile comparison checked cases with none too
    # (Lot 4.3, PLAN_SOLIDITE_TECHNIQUE.md).
    "condorcet": get_copeland_winner,
    "minimax": get_minimax_winner,
    "schulze": get_schulze_winner,
    "bucklin": get_bucklin_winner,
    "nanson": get_nanson_winner,
    "baldwin": get_baldwin_winner,
    "ranked_pairs": get_ranked_pairs_winner,
    "kemeny": get_kemeny_young_winner,
    "black": get_black_winner,
    "anti_plurality": get_anti_plurality_winner,
    "dowdall": get_dowdall_winner,
    "raynaud": get_raynaud_winner,
    "benham": get_benham_winner,
    "river": get_river_winner,
    "smith_irv": get_smith_irv_winner,
    "split_cycle": get_split_cycle_winner,
}

# Cardinal rules that take the SAME per-voter score vector on both engines (so a
# shared score matrix is a fair comparison). Approval and majority judgment are
# excluded from THIS dict specifically because the two engines derive/quantise
# their ballots differently from a raw utility score (rankings/mean-threshold vs
# fixed 0.5 cutoff for approval; round(s*5) vs threshold buckets for MJ) — an
# arbitrary shared score matrix would flag that known, deliberate modelling
# difference as a false "divergence" on the counting algorithm it isn't testing.
# See _approval_winner/_mj_winner below, which sidestep this by generating ballots
# at exactly the values both engines are guaranteed to quantise identically.
CARDINAL = {
    "score": lambda b: get_simple_score_winner(b)["winner"],
    "star": lambda b: get_star_voting_winner(b)["winner"],
    "cumulative": get_cumulative_winner,
    "maximin": get_maximin_score_winner,
    "nash": get_nash_winner,
}

# approval: fed a per-voter {candidate: 0.0 or 1.0} ballot instead of a raw
# utility score. The client approves score >= 0.5 (winApproval); the backend's
# sincere mode approves score > the voter's own mean (get_approval_winner_sincere)
# — at exactly 0.0/1.0, with each voter approving a proper non-empty subset (so
# the mean is strictly between 0 and 1), both reduce to the SAME approval set,
# so this compares the tally, not ballot derivation. That's all it locks: every
# cutoff strictly between 0 and 1 approves the same set here, so either side's
# threshold can move without this noticing, and the two derivations (and the
# backend's approve-top-2 get_approval_winner most callers use) still disagree
# on real utility. Ties are filtered out by strict_winner_cardinal, not compared.
def _approval_winner(ballots):
    return get_approval_winner_sincere(dict(enumerate(ballots)))


# majority_judgment: fed a per-voter {candidate: grade/5.0} ballot (grade in
# 0..5) instead of a raw utility score. The client quantises via
# round(score*5) (winMajorityJudgment); the backend via fixed thresholds
# [0, .17, .33, .5, .67, .83] (_utility_to_grade). Those two quantisers
# disagree at arbitrary utility values (e.g. 0.15) but agree exactly on every
# multiple of 1/5 — the only values a grade can round-trip through both. Feeding
# only those values means both engines score the SAME 0-5 grade per candidate,
# so this compares median/tie-break selection, not grade quantisation.
def _mj_winner(ballots):
    return get_majority_judgment_winner(ballots)["winner"]

NAMES = ["A", "B", "C", "D", "E"]
SEED = 20260628
OUT = os.path.abspath(
    os.path.join(ROOT, "..", "voter-app", "src", "lib", "__fixtures__", "engineParity.json")
)


def strict_winner(fn, ballots, cands, rng):
    """The winner only if it is UNAMBIGUOUS — i.e. invariant to relabeling the
    candidates. A voting rule is neutral, so a strict winner can't depend on
    candidate order; if any random relabeling changes it, the result was decided
    by a tie-break (a convention, not the algorithm) → return None and skip it,
    so the parity test stays a pure algorithmic-correctness check."""
    base = fn(ballots)
    if base is None:
        return None
    for _ in range(200):
        shuffled = cands[:]
        rng.shuffle(shuffled)
        relabel = dict(zip(cands, shuffled))  # old name -> new name
        inv = {v: k for k, v in relabel.items()}
        rows = [[relabel[c] for c in b] for b in ballots]
        rng.shuffle(rows)  # ballot order too — neutrality AND anonymity, so any
        w = fn(rows)  # insertion-order tie-break shows up as an unstable winner
        if w is None or inv[w] != base:
            return None
    return base


def strict_winner_cardinal(fn, ballots, cands, rng, shuffle_keys=True):
    """As strict_winner, for score ballots (per-voter {candidate: score} dicts):
    keep the winner only if it survives relabeling the candidates and shuffling
    the voters, so it isn't a tie-break artefact.

    Relabeling alone keeps every candidate at the same dict position, so a
    tie broken by first-seen key order survives it and passes as "strict".
    shuffle_keys also reorders each trial's keys, which exposes that -- it
    defaults True because False is now a known-weaker mode with no upside, not
    a real alternative: pass shuffle_keys=False only to deliberately reproduce
    the pre-fix behavior (e.g. bisecting when it changed something), never for
    a new caller. single_rule_scenarios still passes it explicitly for
    clarity at the call site; main()'s cardinal loop relies on the default.
    The default used to be False, and the CARDINAL section (main()'s
    cardinal_scenarios loop) used to skip it entirely: without it, 59/60 of
    that section's maximin winners (and a few score/STAR ones) were key-order
    tie-breaks both engines happen to share, not genuine algorithmic
    agreement. Turning it on for CARDINAL dropped maximin's strict-winner
    count to a measured 1/60 (a real property of the rule, not a bug -- see
    MIN_STRICT_WINNERS_MAXIMIN's comment in playgroundVoting.parity.test.ts);
    score/STAR/cumulative/nash stayed comfortably above the shared 40-winner
    floor. PLAN_SURFACE_EXTERIEURE.md §2.E has the full before/after."""
    base = fn(ballots)
    if base is None:
        return None
    for _ in range(200):
        shuffled = cands[:]
        rng.shuffle(shuffled)
        relabel = dict(zip(cands, shuffled))
        inv = {v: k for k, v in relabel.items()}
        rows = [{relabel[c]: v for c, v in b.items()} for b in ballots]
        if shuffle_keys:
            order = cands[:]
            rng.shuffle(order)
            rows = [{c: row[c] for c in order} for row in rows]
        rng.shuffle(rows)
        w = fn(rows)
        if w is None or inv[w] != base:
            return None
    return base


def make_approval_ballot(cands, rng):
    """One voter's {candidate: 0.0/1.0} approval ballot -- a random NON-EMPTY,
    PROPER subset approved (never all-or-nothing), so the backend's
    approve-above-my-own-mean threshold is strictly between 0 and 1 and
    recovers exactly this same set (see _approval_winner's comment)."""
    k = rng.randint(1, len(cands) - 1)
    approved = set(rng.sample(cands, k))
    return {c: (1.0 if c in approved else 0.0) for c in cands}


def make_mj_ballot(cands, rng):
    """One voter's {candidate: grade/5.0} ballot, grade drawn uniformly from
    0..5 -- the only utility values the client's and backend's grade
    quantisers are guaranteed to agree on (see _mj_winner's comment)."""
    return {c: rng.randint(0, 5) / 5.0 for c in cands}


def single_rule_scenarios(rule, fn, make_ballot, to_json):
    """60 strict scenarios for one rule fed its own exact-value ballots, in the
    cardinal shape ({candidates, scores, winners: {rule: w}}).

    Each rule gets its OWN seeded streams, one for ballots and one for the
    relabel trials, instead of main()'s shared `rng`. That stream shifts
    whenever an earlier strict filter exits early, so any unrelated rule change
    used to re-roll every scenario here, and with it the exact mismatch list a
    tracked divergence is pinned to. A str seed is hashed with SHA-512, so it
    doesn't depend on PYTHONHASHSEED."""
    ballot_rng = random.Random(f"{SEED}:{rule}:ballots")
    trial_rng = random.Random(f"{SEED}:{rule}:trials")
    scenarios = []
    for m in (3, 4, 5):
        cands = NAMES[:m]
        for n in (21, 31, 41, 51, 61):
            for _ in range(4):
                ballots = [make_ballot(cands, ballot_rng) for _ in range(n)]
                winner = strict_winner_cardinal(fn, ballots, cands, trial_rng, shuffle_keys=True)
                scenarios.append({
                    "candidates": cands,
                    "scores": [[to_json(b[c]) for c in cands] for b in ballots],
                    "winners": {rule: winner},
                })
    return scenarios


def generate_exhaustive_scenarios() -> list[dict]:
    """Every possible ordinal profile for n<=3 candidates and m<=5 voters --
    an exhaustive proof of parity over that whole bounded domain, not a
    sample of it (Lot 4.3, PLAN_SOLIDITE_TECHNIQUE.md). Anonymity (already
    established by test_anonymity.py) means only the MULTISET of ballots
    matters, so `combinations_with_replacement` over the n! ballot types
    enumerates the space without redundant voter-relabellings -- 481 profiles
    total (20 for n=2, 461 for n=3), fully deterministic (itertools order,
    no dict/set iteration), no PYTHONHASHSEED dependency.

    Unlike the random scenarios above, winners here are RAW -- not run
    through strict_winner's relabel-robustness filter. That filter exists to
    stop "no comparable winner" ballast, but on a handful of large random
    profiles it also silently skips every tied/degenerate case, which is
    exactly where 4 of the 5 real bugs this exhaustive check found were
    hiding (a fifth, `condorcet`, was a wrong function mapping -- see RULES
    above). n=4 (an additional 98,280 profiles, ~60MB of JSON) was also
    verified this way as a one-time pass during development -- 0 mismatches
    after the fixes below -- but isn't committed here: regenerating it on
    every PR would be slow for a domain size a smaller committed slice
    already exercises the same bug CLASS on.
    """
    scenarios = []
    for n in (2, 3):
        cands = NAMES[:n]
        ballot_types = list(itertools.permutations(cands))
        k = len(ballot_types)
        for m in range(1, 6):
            for combo in itertools.combinations_with_replacement(range(k), m):
                ballots = [list(ballot_types[i]) for i in combo]
                winners = {rule: fn(ballots) for rule, fn in RULES.items()}
                scenarios.append({"candidates": cands, "ballots": ballots, "winners": winners})
    return scenarios


def _generate_exhaustive_cardinal_scenarios(
    rule: str,
    winner_fn: Any,
    ballot_types_for: Any,
    n_range: tuple,
    mmax_for: Any,
    to_score: Any = lambda v: v,
) -> list[dict]:
    """Shared body for the exhaustive small-profile CARDINAL domains (approval,
    majority_judgment, maximin — anything that reads `scores`, not `ranks`) —
    the same "every profile over a small ballot-type alphabet, not a sample"
    proof as generate_exhaustive_scenarios' ordinal domain above, parametrized
    over what a ballot TYPE means for each rule. Extracted from what used to be
    three (now: two, plus this one) near-identical ~40-line bodies differing
    only in the ballot-type source and the winner fn — see the git history of
    the PR that added this function for the duplication it replaced.

    Anonymity (test_anonymity.py) means only the MULTISET of ballot types
    matters, so `combinations_with_replacement` over `ballot_types_for(cands)`
    (not raw voters) enumerates the space without redundant voter-relabellings,
    the same argument generate_exhaustive_scenarios makes for `itertools.
    permutations` + `combinations_with_replacement` over ordinal ballots.

    `ballot_types_for(cands)` returns one tuple of per-candidate raw values per
    ballot type, in `cands` order, already in whatever unit `winner_fn` reads
    (0.0/1.0 for approval, a grade/5.0 utility for MJ, a raw grade int for
    maximin — each caller's own docstring explains its choice). That tuple is
    the SINGLE source both the ballot dict fed to `winner_fn` and the recorded
    `"scores"` JSON field are built from: `scores` is read back from the actual
    `ballots` that were scored (`to_score` applied to each cell), not
    reconstructed a second time from `ballot_types`/`combo` in a parallel
    expression. That second, independent expression is exactly what the
    approval and majority-judgment generators used to do individually — a
    real (if today-harmless, since both expressions compute the same thing
    from the same source) self-consistency risk multiple review passes
    flagged: if the ballot-derivation logic ever changed, the two expressions
    would have to be kept in lockstep by hand. Here there is exactly one.

    `to_score` converts a ballot cell's raw value into the JSON-friendly value
    the fixture records (int 0/1 for approval, the integer grade 0-5 for MJ,
    unchanged for maximin's already-integer grades). Defaults to the identity.

    Winners are RAW (ties/no-winner -> None), never `strict_winner_cardinal`-
    filtered — same reasoning as `generate_exhaustive_scenarios`: that filter
    exists to drop "no comparable winner" ballast, but it also silently skips
    exactly the tied/degenerate profiles an exhaustive check exists to catch.
    """
    scenarios = []
    for n in n_range:
        cands = NAMES[:n]
        ballot_types = ballot_types_for(cands)
        k = len(ballot_types)
        mmax = mmax_for(n)
        for m in range(1, mmax + 1):
            for combo in itertools.combinations_with_replacement(range(k), m):
                ballots = [
                    {c: ballot_types[i][j] for j, c in enumerate(cands)} for i in combo
                ]
                winner = winner_fn(ballots)
                scenarios.append(
                    {
                        "candidates": cands,
                        "scores": [[to_score(vote[c]) for c in cands] for vote in ballots],
                        "winners": {rule: winner},
                    }
                )
    return scenarios


def _approval_ballot_types(cands: list) -> list:
    """Every NON-DEGENERATE proper subset of `cands` (0 < |S| < n) -- the same
    domain make_approval_ballot draws from at random, enumerated exhaustively
    instead of sampled. Degenerate subsets (approve nobody / approve everybody)
    are excluded on purpose: at those two profiles the client's own >=0.5
    cutoff and the backend's above-own-mean cutoff structurally disagree (the
    mean equals the single value every candidate shares, so "strictly above"
    collapses to empty) -- a known ballot-DERIVATION difference (see
    _approval_winner's comment above CARDINAL), not the tally bug this
    exhaustive check exists to catch. Including them would flag that known,
    accepted modelling gap as a false "divergence" on every run."""
    n = len(cands)
    return [frozenset(s) for r in range(1, n) for s in itertools.combinations(cands, r)]


def generate_exhaustive_approval_scenarios() -> list[dict]:
    """Every possible approval profile for n<=3 candidates, m<=5 voters -- the
    approval instance of _generate_exhaustive_cardinal_scenarios' shared
    domain proof (see its docstring for the anonymity/combinations_with_
    replacement argument and the ballots -> scores self-consistency fix).

    A ballot TYPE here is one of the 2^n - 2 non-degenerate proper subsets of
    candidates (_approval_ballot_types) instead of one of n! permutations,
    turned into a per-candidate 0.0/1.0 tuple. 2^n - 2 happens to equal n! for
    n in {2, 3} (2 and 6), so this domain is exactly the same shape and size
    as the ordinal one: 481 profiles (20 for n=2, 461 for n=3) -- measured
    with combinations_with_replacement before committing to it, same as every
    other domain in this file (see gen_engine_parity.py's git history / the
    PR that added this function for the measured counts).

    Reuses _approval_winner (get_approval_winner_sincere) -- the tally logic
    is not reimplemented here.
    """
    return _generate_exhaustive_cardinal_scenarios(
        rule="approval",
        winner_fn=_approval_winner,
        ballot_types_for=lambda cands: [
            tuple(1.0 if c in s else 0.0 for c in cands) for s in _approval_ballot_types(cands)
        ],
        n_range=(2, 3),
        mmax_for=lambda n: 5,
        to_score=int,
    )


# Coarsened grade set for the exhaustive majority-judgment domain below: three
# of the six real quantisation points (worst / mid / best), not all six. See
# generate_exhaustive_majority_judgment_scenarios' docstring for why the full
# scale isn't tractable at n=3 and why coarsening loses no algorithmic
# coverage: get_majority_judgment_winner only ever compares grade INTEGERS
# with <, >, == (median, then the iterative strip-and-recompare tie-break --
# see _mj_strip_to_winner in simulation_score_utils.py; the older p-q
# majority-gauge shortcut this used to be approximated by is gone as of
# PR #538) -- never their magnitudes -- so any three strictly-increasing
# grades produce exactly the same set of order-patterns as any other three.
# These specific values are chosen only so the fixture reads as real MJ
# grades, not for coverage.
#
# This is a real premise, not just an implementation detail -- it's WHY 3
# grades is a legitimate coarsening rather than a silent loss of coverage.
# It holds for the algorithm as it exists today; if a future majority-
# judgment change ever made the tie-break magnitude-sensitive (e.g. a
# weighted or distance-based step, not just <, >, ==), this domain would
# need re-widening back toward the full 0-5 scale to keep meaning what its
# own "matches the backend on EVERY profile" test description claims.
MJ_EXHAUSTIVE_GRADES: tuple = (0, 2, 5)


def generate_exhaustive_majority_judgment_scenarios() -> list[dict]:
    """Every possible majority-judgment profile over MJ_EXHAUSTIVE_GRADES for
    n<=3 candidates -- the majority-judgment instance of
    _generate_exhaustive_cardinal_scenarios' shared domain proof (see its
    docstring for the anonymity argument and the ballots -> scores fix), with
    two tractability concessions measured (not guessed) before picking them
    (exact combinations_with_replacement(k, m) counts):

    1. Grades. A ballot type is one of G^n grade-vectors. The full G=6 scale
       is fine at n=2 (36 types: the full m<=5 domain is 749,397 profiles, a
       ~90MB fixture) but explodes at n=3 (216 types: m<=5 is ~4.2 BILLION
       profiles, and even m<=4 alone is ~95 million) -- nowhere near
       committable. Coarsening to G=3 (MJ_EXHAUSTIVE_GRADES) drops that to 9
       types at n=2, 27 at n=3, without losing coverage of the winner-
       selection algorithm's actual decision surface (see
       MJ_EXHAUSTIVE_GRADES' own comment: it's a purely ordinal algorithm
       over grade integers, so 3 coarse grades exercise the same code paths
       as any other 3 distinct grades would).
    2. Voters. Even at G=3, n=3's ballot-type count (27) makes m explode
       fast: m<=3 is 4,059 profiles, m<=4 is 31,464 -- an ~8x jump for one
       more voter, the same kind of blow-up that keeps ordinal n=4 out of
       this file (see generate_exhaustive_scenarios' docstring). m<=3 is the
       cutoff for n=3; it still exercises a real median (not just the min/max
       of a 1-2 voter list) and the iterative strip tie-break, without the
       blow-up. n=2 stays at the full m<=5 (only 2,001 profiles -- cheap).

    Domain: n=2, m in 1..5 (2,001 profiles) + n=3, m in 1..3 (4,059 profiles)
    = 6,060 profiles total (~700KB of fixture).

    Fixture size, acknowledged directly: this section alone adds ~700KB (plus
    ~58KB from generate_exhaustive_approval_scenarios), taking
    engineParity.json from ~460KB to ~1.3MB -- well past the 500KB budget
    PLAN_SURFACE_EXTERIEURE.md §2.E records this exact file being trimmed to
    respect (`check-added-large-files --maxkb=500`). That hook only checks
    NEWLY ADDED files, not growth on an already-tracked one, so this doesn't
    fail CI -- but it's still a real, deliberate overage of the established
    precedent, not an oversight. Judged worth it here: this is a generated
    test fixture, not shipped app code (the 1MB brotli budget that DOES gate
    the real build is voter-app's own `.size-limit.json`, unaffected by this
    file), and the whole point of the exhaustive domain is that a smaller one
    would re-introduce exactly the "silently skips the tied/degenerate cases"
    gap this file's own history says is where the real bugs hide. If this
    trade needs revisiting, the lever is m<=3 -> m<=2 for n=3 above (4,059 ->
    405 profiles, saving ~410KB) at the cost of the n=3 domain no longer
    exercising a real 3-way median.

    Reuses _mj_winner (get_majority_judgment_winner) -- the tally/tie-break
    logic is not reimplemented here.
    """
    return _generate_exhaustive_cardinal_scenarios(
        rule="majority_judgment",
        winner_fn=_mj_winner,
        ballot_types_for=lambda cands: [
            tuple(g / 5.0 for g in gv)
            for gv in itertools.product(MJ_EXHAUSTIVE_GRADES, repeat=len(cands))
        ],
        n_range=(2, 3),
        mmax_for=lambda n: 5 if n == 2 else 3,
        to_score=lambda v: round(v * 5),
    )


# Coarsened grade set for the exhaustive maximin domain below, legitimate for
# the SAME reason MJ_EXHAUSTIVE_GRADES is legitimate for majority judgment
# (see its comment above): get_maximin_score_winner (simulation_score_utils.py)
# computes, per candidate, `min()` over that candidate's own voters' raw
# scores, then `max()` over candidates keyed by that per-candidate minimum --
# both are ORDER comparisons (Python's min/max compare with `<`), never
# arithmetic on the score magnitudes. So maximin's winner is invariant under
# any strictly-increasing relabeling of the score alphabet, exactly like MJ's
# grade comparisons.
#
# This was verified independently before building this domain, not assumed
# from MJ's premise just because the technique looks the same: by re-reading
# get_maximin_score_winner's body (confirms the min/max-only argument above),
# AND empirically with a throwaway script (not committed) that relabeled
# (0, 2, 5) -> (1, 10, 100) -- a deliberately NON-linear, order-preserving
# remap -- across 200k random profiles (n in 2..5, m in 1..8), then again with
# a wider 0-5 grade set and a more aggressive remap across another 200k: 0
# winner changes in either run. Reusing MJ's exact three values here is only
# for fixture-reading consistency with the MJ section; any 3 strictly-
# increasing values would do.
MAXIMIN_EXHAUSTIVE_GRADES: tuple = (0, 2, 5)


def generate_exhaustive_maximin_scenarios() -> list[dict]:
    """Every possible maximin profile over MAXIMIN_EXHAUSTIVE_GRADES for n<=3
    candidates -- the maximin instance of
    _generate_exhaustive_cardinal_scenarios' shared domain proof, extending
    the same coarsened-grade technique generate_exhaustive_majority_judgment_
    scenarios uses (see MAXIMIN_EXHAUSTIVE_GRADES' comment for why it's sound
    for THIS rule specifically -- verified independently, not assumed from
    MJ's).

    Unlike MJ, maximin only ever computes min()/max() -- no median, no
    iterative strip-and-recompare tie-break -- but its ballot-TYPE alphabet is
    built exactly like MJ's: one of G^n grade-vectors, G=3. The
    combinations_with_replacement(k, m) counts behind the domain size are
    therefore IDENTICAL to MJ's -- measured explicitly here, not assumed from
    the shared technique, because that count is a pure function of (n, m, G),
    independent of which winner algorithm is layered on top of the same
    ballot-type alphabet:

      n=2, G=3 -> k=9  ballot types, m in 1..5 -> 2,001 profiles
      n=3, G=3 -> k=27 ballot types, m in 1..3 -> 4,059 profiles
      total: 6,060 profiles

    n=3 stays capped at m<=3 for the same reason as MJ: k=27 makes m<=4 jump
    to 31,464 profiles (~8x), and m<=3 already exercises a real 3+-way
    minimum comparison across candidates, not just a 1-2 voter edge case.

    Grades are fed to get_maximin_score_winner as UNSCALED raw ints (0, 2, 5)
    -- not divided by 5 like MJ's utility ballots. Unlike MJ's fixed [0, 1]
    grade-quantisation thresholds, neither engine's maximin implementation
    (get_maximin_score_winner here; winMaximin in playgroundVoting.ts) ever
    compares a score against an absolute threshold -- both only ever compare
    scores against EACH OTHER (min, then max) -- so no rescaling is needed for
    either side to read this domain correctly; `to_score` is left at the
    shared helper's default identity.

    Fixture size: this section measured at ~730KB after generation (6,060
    scenarios, slightly lighter than MJ's ~790KB for the same count -- a
    shorter "maximin" rule key than "majority_judgment" and no median/
    tie-break bookkeeping to record, just candidates/scores/winner), taking
    engineParity.json from ~1.3MB to ~2.0MB -- the same acknowledged,
    deliberate overage of the 500KB check-added-large-files precedent
    generate_exhaustive_majority_judgment_scenarios' docstring records (that
    hook only checks NEWLY ADDED files, not growth on an already-tracked one).

    Reuses get_maximin_score_winner directly: it already accepts a plain list
    of per-voter score dicts (no `dict(enumerate(...))` or `["winner"]`
    unwrapping needed, unlike approval/MJ's backend entry points) -- the
    tally logic is not reimplemented here.
    """
    return _generate_exhaustive_cardinal_scenarios(
        rule="maximin",
        winner_fn=get_maximin_score_winner,
        ballot_types_for=lambda cands: list(
            itertools.product(MAXIMIN_EXHAUSTIVE_GRADES, repeat=len(cands))
        ),
        n_range=(2, 3),
        mmax_for=lambda n: 5 if n == 2 else 3,
    )


def main() -> None:
    rng = random.Random(SEED)
    scenarios = []
    for m in (3, 4, 5):
        cands = NAMES[:m]
        for n in (21, 31, 41, 51, 61):
            for _ in range(4):  # 4 profiles per (m, n) → 60 scenarios
                ballots = [rng.sample(cands, m) for _ in range(n)]
                winners = {rule: strict_winner(fn, ballots, cands, rng) for rule, fn in RULES.items()}
                scenarios.append({"candidates": cands, "ballots": ballots, "winners": winners})

    # Own seeded streams, like single_rule_scenarios' — so a change to the
    # ordinal RULES section above doesn't re-roll every cardinal ballot too
    # (the same coupling bug fixed for approval/majority_judgment,
    # PLAN_SURFACE_EXTERIEURE.md §2.E). The 5 CARDINAL rules still share ONE
    # ballot stream, since they're deliberately fed the SAME score matrix per
    # scenario (that's the whole point of this section) — but each gets its
    # OWN trial stream for strict_winner_cardinal's 200-trial relabel/shuffle
    # loop, so a future change to one rule's tie-break behavior (e.g. finally
    # fixing get_maximin_score_winner's) can't shift how many relabel/shuffle
    # calls run before it and silently re-roll the OTHER rules' recorded
    # winners and ballots for later scenarios too.
    cardinal_ballot_rng = random.Random(f"{SEED}:cardinal:ballots")
    cardinal_trial_rngs = {rule: random.Random(f"{SEED}:cardinal:trials:{rule}") for rule in CARDINAL}
    cardinal_scenarios = []
    for m in (3, 4, 5):
        cands = NAMES[:m]
        for n in (21, 31, 41, 51, 61):
            for _ in range(4):
                score_ballots = [{c: cardinal_ballot_rng.randint(0, 5) for c in cands} for _ in range(n)]
                winners = {
                    rule: strict_winner_cardinal(fn, score_ballots, cands, cardinal_trial_rngs[rule])
                    for rule, fn in CARDINAL.items()
                }
                matrix = [[b[c] for c in cands] for b in score_ballots]
                cardinal_scenarios.append(
                    {"candidates": cands, "scores": matrix, "winners": winners}
                )

    approval_scenarios = single_rule_scenarios("approval", _approval_winner, make_approval_ballot, int)
    # Stored as the integer grade 0..5, like cardinalScenarios' scores; the test
    # divides by 5 again, since the client's MJ quantiser reads a [0, 1] score.
    mj_scenarios = single_rule_scenarios(
        "majority_judgment", _mj_winner, make_mj_ballot, lambda v: round(v * 5)
    )

    exhaustive_scenarios = generate_exhaustive_scenarios()
    exhaustive_approval_scenarios = generate_exhaustive_approval_scenarios()
    exhaustive_mj_scenarios = generate_exhaustive_majority_judgment_scenarios()
    exhaustive_maximin_scenarios = generate_exhaustive_maximin_scenarios()

    payload = {
        "_generatedBy": "fast_api_voter/scripts/gen_engine_parity.py",
        "_seed": SEED,
        "_note": "Authoritative winners from the Python backend. Asserted by playgroundVoting.parity.test.ts.",
        "scenarios": scenarios,
        "cardinalScenarios": cardinal_scenarios,
        "approvalScenarios": approval_scenarios,
        "majorityJudgmentScenarios": mj_scenarios,
        "exhaustiveScenarios": exhaustive_scenarios,
        "exhaustiveApprovalScenarios": exhaustive_approval_scenarios,
        "exhaustiveMajorityJudgmentScenarios": exhaustive_mj_scenarios,
        "exhaustiveMaximinScenarios": exhaustive_maximin_scenarios,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=0)
        f.write("\n")
    print(
        f"wrote {len(scenarios)} ordinal + {len(cardinal_scenarios)} cardinal + "
        f"{len(approval_scenarios)} approval + {len(mj_scenarios)} majority-judgment + "
        f"{len(exhaustive_scenarios)} exhaustive ordinal (n<=3) + "
        f"{len(exhaustive_approval_scenarios)} exhaustive approval (n<=3) + "
        f"{len(exhaustive_mj_scenarios)} exhaustive majority-judgment + "
        f"{len(exhaustive_maximin_scenarios)} exhaustive maximin scenarios -> {OUT}"
    )


if __name__ == "__main__":
    main()
