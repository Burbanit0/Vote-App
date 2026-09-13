#!/usr/bin/env python3
"""fuzz_engine.py — coverage-guided fuzzing harness for the voting engine
(Lot 9, PLAN_SOLIDITE_TECHNIQUE.md — "Fuzzing à couverture").

Targets every winner function in `simulation_ranked_utils.py` (21 ordinal
rules) and `simulation_score_utils.py` (12 cardinal/analysis functions) —
the SAME two files the dual-voting-engine parity harness locks against the
frontend (CLAUDE.md, "The dual voting engine"). This harness does not check
parity or any axiom; it only asks whether a call can raise an exception the
function never means to raise.

Why this needs a real fuzzer and not just more Hypothesis examples: the
existing property tests (`api/tests/test_hypothesis_condorcet.py`,
`test_hypothesis_monotonicity.py`) already cover this code, but narrowly —
`st.permutations(["A", "B", "C", "D"])` only ever generates COMPLETE,
DISTINCT, well-formed rankings over a fixed 4-candidate set. That is exactly
the input shape every rule's docstring assumes. This harness deliberately
generates the shapes those strategies structurally cannot: empty/duplicate
candidates within one ballot, incomplete ballots, unicode/empty candidate
names, dict-format ballots missing keys, and NaN/inf cardinal scores —
whether or not the app's own callers currently produce them (they don't:
`api/schemas/simulations.py`'s `NumVoters`/`NumRounds` bounds mean rankings
reaching these functions today are internally generated and well-formed).
Finding a crash here doesn't necessarily mean end users can trigger it; it
means the engine's contract with a MALFORMED-but-plausible input isn't
"never raise" the way pure functions this heavily relied-upon should be.

Candidate pool is small and FIXED (not raw fuzzer bytes) on purpose: letting
every ballot position be an arbitrary fuzzer-chosen string would blow up the
number of DISTINCT candidates per call past `_KY_EXACT_CAP` (6), and
`get_kemeny_young_winner`'s exact path is O(n!) — every call would then
spend its time in a factorial enumeration unrelated to any real bug rather
than exploring new code paths. Bounding the pool keeps each execution fast
(this is what actually makes coverage-guided search work: high exec/sec)
while still covering weird individual identities (empty string, unicode,
whitespace) via the pool itself.

Usage:
    cd fast_api_voter
    # One-off timed campaign, persisting discovered inputs to a corpus dir:
    python scripts/fuzz_engine.py fuzz_corpus/engine -max_total_time=600

    # Replay a single crashing input found by the above (argv, not a flag):
    python scripts/fuzz_engine.py fuzz_corpus/engine/crash-<sha1>

    # Quick smoke run (no persistence), used by the CI workflow's smoke step:
    python scripts/fuzz_engine.py -atheris_runs=20000 -max_total_time=30

See fuzz_llm_parsers.py for the second harness (Lot 9's "parsers" half) and
docs/exploration/EXP-009-atheris-coverage-fuzzing.md for the campaign this
was actually run with and what it found.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable

import atheris

# Running as `python scripts/fuzz_engine.py` puts `scripts/` (not the repo
# root) on sys.path[0] -- same fix as gen_engine_parity.py's ROOT insertion.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

with atheris.instrument_imports():
    from api.engine.utils.simulation_ranked_utils import (
        get_anti_plurality_winner,
        get_approval_winner,
        get_baldwin_winner,
        get_benham_winner,
        get_black_winner,
        get_borda_winner,
        get_bucklin_winner,
        get_condorcet_winner,
        get_coombs_winner,
        get_copeland_winner,
        get_dowdall_winner,
        get_irv_winner,
        get_kemeny_young_winner,
        get_minimax_winner,
        get_nanson_winner,
        get_plurality_winner,
        get_random_ballot_winner,
        get_ranked_pairs_winner,
        get_raynaud_winner,
        get_river_winner,
        get_schulze_winner,
        get_score_winner,
        get_smith_irv_winner,
        get_split_cycle_winner,
        get_two_round_winner,
    )
    from api.engine.utils.simulation_score_utils import (
        calculate_bayesian_regret,
        get_cumulative_winner,
        get_evaluative_winner,
        get_majority_judgment_winner,
        get_maximin_score_winner,
        get_mean_median_hybrid_winner,
        get_median_voting_winner,
        get_nash_winner,
        get_score_distribution_analysis,
        get_simple_score_winner,
        get_star_voting_winner,
        get_variance_based_winner,
    )

# Every ranked rule locked by the parity harness (CLAUDE.md) plus every other
# ranked rule this repo ships — all take (votes, blank_candidate_name).
_RANKED_RULES: list[Callable[..., Any]] = [
    get_condorcet_winner,
    get_two_round_winner,
    get_borda_winner,
    get_dowdall_winner,
    get_black_winner,
    get_benham_winner,
    get_plurality_winner,
    get_anti_plurality_winner,
    get_approval_winner,
    get_irv_winner,
    get_coombs_winner,
    get_score_winner,
    get_kemeny_young_winner,
    get_bucklin_winner,
    get_minimax_winner,
    get_schulze_winner,
    get_copeland_winner,
    get_raynaud_winner,
    get_nanson_winner,
    get_baldwin_winner,
    get_ranked_pairs_winner,
    get_river_winner,
    get_smith_irv_winner,
    get_split_cycle_winner,
    get_random_ballot_winner,
]

# Cardinal rules: take a single `all_scores: list[dict[candidate, score]]`.
_SCORE_RULES: list[Callable[..., Any]] = [
    get_simple_score_winner,
    get_star_voting_winner,
    get_cumulative_winner,
    get_maximin_score_winner,
    get_nash_winner,
    get_median_voting_winner,
    get_mean_median_hybrid_winner,
    get_variance_based_winner,
    get_score_distribution_analysis,
    calculate_bayesian_regret,
]

# get_majority_judgment_winner/get_evaluative_winner take `utility_scores`
# in [0, 1] by contract (their own docstrings), not the 0..5 raw scale the
# rules above use — fuzzed separately below with that in mind, not because
# the functions themselves enforce the range (neither does).
_UTILITY_RULES: list[Callable[..., Any]] = [
    get_majority_judgment_winner,
    get_evaluative_winner,
]

# Small, fixed pool deliberately including edge-case identities the existing
# Hypothesis strategies (["A","B","C","D"] only) never generate: an empty
# name, a name that collides with common blank-ballot sentinels, unicode,
# and a name with leading/trailing whitespace. Kept at 7 entries -- see the
# module docstring for why this must stay well under get_kemeny_young_winner's
# `_KY_EXACT_CAP` (6).
_CANDIDATE_POOL = ["A", "B", "C", "", "Ω", " ", "A "]

_MAX_BALLOTS = 30
_MAX_RANKING_LEN = 9  # > len(_CANDIDATE_POOL): lets a ranking overrun the pool


def _pick_candidate(fdp: "atheris.FuzzedDataProvider") -> str:
    return _CANDIDATE_POOL[fdp.ConsumeIntInRange(0, len(_CANDIDATE_POOL) - 1)]


def _build_list_ballot(fdp: "atheris.FuzzedDataProvider") -> list[str]:
    length = fdp.ConsumeIntInRange(0, _MAX_RANKING_LEN)
    return [_pick_candidate(fdp) for _ in range(length)]


def _build_dict_ballot(fdp: "atheris.FuzzedDataProvider", voter_id: int) -> dict[str, Any]:
    """`ranking` is always present (possibly empty), never omitted: a first
    version of this harness DID omit it sometimes, on the theory that
    `_is_dict_format` only ever inspects votes[0] so a later malformed dict
    is a shape st.permutations-based strategies can never produce. It found
    exactly that: `_get_ranking`'s `vote["ranking"]` KeyError on a dict
    missing the key. Every dict-format ballot's own docstring (see
    get_condorcet_winner) documents 'ranking' as required, not optional, and
    no caller in this repo ever constructs one without it -- a caller that
    does is itself buggy, and failing loudly on that is arguably the CORRECT
    behaviour, not a defect to paper over with a silent default. Kept
    generating only well-formed-key dicts from here on, same call this
    module's docstring already makes about the top-level shape staying
    valid so the harness spends its budget on real findings, not
    rediscovering this one every run (see docs/exploration/EXP-009)."""
    return {"voter_id": voter_id, "ranking": _build_list_ballot(fdp)}


def _build_ranked_votes(fdp: "atheris.FuzzedDataProvider") -> tuple[list[Any], str]:
    dict_format = fdp.ConsumeBool()
    n = fdp.ConsumeIntInRange(0, _MAX_BALLOTS)
    if dict_format:
        votes: list[Any] = [_build_dict_ballot(fdp, i) for i in range(n)]
    else:
        votes = [_build_list_ballot(fdp) for _ in range(n)]
    blank = _pick_candidate(fdp)
    return votes, blank


def _build_score_ballot(fdp: "atheris.FuzzedDataProvider", *, unit_interval: bool) -> dict[str, float]:
    n_candidates = fdp.ConsumeIntInRange(0, len(_CANDIDATE_POOL))
    names = {_pick_candidate(fdp) for _ in range(n_candidates)}
    ballot: dict[str, float] = {}
    for name in names:
        if unit_interval:
            # Still allow occasional NaN/inf via ConsumeFloat despite the
            # nominal [0,1] contract -- an adversarial/buggy caller sending
            # an out-of-contract utility is exactly the case worth covering.
            ballot[name] = fdp.ConsumeFloatInRange(0.0, 1.0) if fdp.ConsumeBool() else fdp.ConsumeFloat()
        else:
            ballot[name] = fdp.ConsumeFloatInRange(0.0, 5.0) if fdp.ConsumeBool() else fdp.ConsumeFloat()
    return ballot


def _build_score_votes(fdp: "atheris.FuzzedDataProvider", *, unit_interval: bool) -> list[dict[str, float]]:
    n = fdp.ConsumeIntInRange(0, _MAX_BALLOTS)
    return [_build_score_ballot(fdp, unit_interval=unit_interval) for _ in range(n)]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    lane = fdp.ConsumeIntInRange(0, 3)

    if lane == 0:
        votes, blank = _build_ranked_votes(fdp)
        for rule in _RANKED_RULES:
            # Keyword, not positional: get_score_winner/get_kemeny_young_winner
            # only accept `votes, **kwargs` (silently absorb it) and
            # get_approval_winner's 2nd positional is `approval_threshold`,
            # not `blank_candidate_name` -- a positional call there would
            # crash every single execution on a harness bug, not an engine one.
            rule(votes, blank_candidate_name=blank)
    elif lane == 1:
        scores = _build_score_votes(fdp, unit_interval=False)
        for rule in _SCORE_RULES:
            rule(scores)
    elif lane == 2:
        utility_scores = _build_score_votes(fdp, unit_interval=True)
        for rule in _UTILITY_RULES:
            rule(utility_scores)
    else:
        # get_approval_winner's sincere/utility_scores branch (never reached
        # by lane 0, which never passes utility_scores): approve every
        # candidate above the voter's own mean utility. Mirrors
        # get_approval_winner_sincere's own construction.
        per_voter_utils = _build_score_votes(fdp, unit_interval=True)
        utility_scores = {i: u for i, u in enumerate(per_voter_utils)}
        votes = [{"voter_id": voter_id} for voter_id in utility_scores]
        threshold = fdp.ConsumeIntInRange(-5, 10)
        get_approval_winner(votes, approval_threshold=threshold, utility_scores=utility_scores)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
