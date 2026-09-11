"""api/tests/test_engine_benchmarks.py — pytest-benchmark suite for the ranked
and cardinal voting engine (Lot 8.1, PLAN_SOLIDITE_TECHNIQUE.md: "Une
régression de perf sur simulation_ranked_utils est aujourd'hui totalement
invisible" -- a perf regression on `simulation_ranked_utils.py` /
`simulation_score_utils.py` is completely invisible today; nothing measures
their wall-clock cost at all).

**Design decision -- absolute ceilings, not a stored-baseline comparison.**
pytest-benchmark's headline feature (`--benchmark-autosave` +
`--benchmark-compare-fail=mean:X%`, comparing this run against a *stored*
prior run) is a well-documented flakiness trap on shared CI runners: GitHub
Actions' shared runners have real run-to-run CPU variance (this repo has
already been burned by exactly this category of problem once -- see the
180s worker timeout in api/core/worker_dispatch.py, calibrated from an
isolated local measurement that then failed for real under CI contention;
same lesson, different mechanism). Confirmed independently before picking a
design (not assumed): pytest-benchmark's own docs describe thresholds like
`min:15%` as the norm specifically *because* shared runners are noisy, and
GitHub Actions runner variance is a widely reported pitfall for exactly this
comparison mode. Committing a machine-specific stored baseline to this repo
and comparing every PR's runner against it would trade a real signal
(catastrophic regressions) for a noisy one (which runner GitHub handed out
today) -- not a trade worth making for a blocking gate.

So this file asserts **generous absolute wall-clock ceilings** instead (the
same philosophy as the e2e suite's `timeout: 30_000` -- "no test legitimately
needs 30s"): every ceiling below is 15-500x looser than the slowest value
actually measured on a modest dev machine (see the constants). That is wide
enough to absorb ordinary CI noise (a slower runner, a noisy neighbour VM)
while still catching what actually matters here -- an accidentally
introduced O(n^2)/O(n^3) pass, a redundant recomputation inside a loop, a
`_KY_EXACT_CAP` bump that reintroduces factorial blowup. Verified live during
development: temporarily adding a redundant O(n^2) pass over the electorate
inside `get_copeland_winner` pushed its measured mean from ~7ms to well over
a second at this file's input size -- comfortably tripping the 500ms
ceiling, confirming the gate has real teeth and isn't just a number nobody
will ever hit. See docs/exploration/EXP-006-pytest-benchmark-engine-perf.md
for the full protocol and numbers.

**Design decision -- its own invocation, not part of the default suite.**
pytest-benchmark auto-disables itself when pytest-xdist is active ("Benchmarks
are automatically disabled because xdist plugin is active" -- confirmed via
pytest-benchmark's own source/docs), and this repo's default backend test job
runs `pytest api/tests -n auto` (backend-ci-cd-pipeline.yml). Running this
file inside that invocation would silently skip every real measurement (the
`benchmark` fixture still calls the function once but records no timing
data), which is worse than not running it at all -- a green check that
proves nothing. So this file is excluded from pyproject.toml's default
`addopts` (`--ignore=api/tests/test_engine_benchmarks.py`, same mechanism
already used for test_schema_contract.py) and given its own CI step that
invokes it explicitly, without `-n auto`:

    cd fast_api_voter && python -m pytest api/tests/test_engine_benchmarks.py -o addopts="" -v

Locally, for real profiling work (not just the CI ceiling), pytest-benchmark's
stored-baseline workflow is still genuinely useful -- it's just not what
gates a PR:

    pytest api/tests/test_engine_benchmarks.py -o addopts="" --benchmark-autosave
    # ... make a change ...
    pytest api/tests/test_engine_benchmarks.py -o addopts="" --benchmark-compare --benchmark-compare-fail=mean:20%

**Input sizes.** `num_voters=1000` is the actual production ceiling
(`ProfileSimulateRequest.num_voters`, `api/schemas/election.py`, `le=1000`),
not an arbitrary round number. `num_candidates=8` is likewise the production
ceiling (`ProfileCandidateSpec` list, `max_length=8`). Kemeny-Young gets two
cases instead of one: `_KY_EXACT_CAP = 6` in simulation_ranked_utils.py means
6 candidates is the worst case for the exact O(n!) path, and 8 candidates
exercises the KwikSort O(n log n) approximation fallback -- two genuinely
different algorithms behind one function name, both worth a floor.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List

import pytest

from api.engine.utils import simulation_ranked_utils as ranked
from api.engine.utils import simulation_score_utils as score

# Production ceilings this benchmark deliberately targets (see module
# docstring) -- not arbitrary round numbers.
NUM_VOTERS = 1000
NUM_CANDIDATES = 8

# Fixed seeds for reproducible INPUT shape across runs/machines. Deliberately
# plain ints, never Python's built-in hash() of a str/tuple -- PYTHONHASHSEED
# randomizes that per-process (the exact pitfall already hit once in this
# repo's Schemathesis work, see PLAN_SOLIDITE_TECHNIQUE.md Lot 3). The
# timing assertion doesn't depend on which particular profile gets
# generated (the ceilings have 15-500x margin either way) -- the fixed seed
# is only so a failing run is reproducible, not load-bearing for the pass/
# fail outcome itself.
_ORDINAL_SEED = 820260911
_CARDINAL_SEED = 820260912
_KEMENY_SEED = 820260913

# Two tiers, generous on purpose (see module docstring): these exist to catch
# a CATASTROPHIC regression, not to police everyday timing noise. Every
# measured value on a modest dev machine was 15-500x under its tier's
# ceiling at NUM_VOTERS/NUM_CANDIDATES above.
FAST_CEILING_S = 0.10  # O(n) tallies, single-pass positional/cardinal scoring
HEAVY_CEILING_S = 0.50  # elimination rounds, pairwise matrices, Kemeny exact

BENCHMARK_ROUNDS = 10
WARMUP_ROUNDS = 1


def _make_votes(num_voters: int, num_candidates: int, seed: int) -> List[List[str]]:
    rng = random.Random(seed)
    candidates = [f"C{i}" for i in range(num_candidates)]
    votes = []
    for _ in range(num_voters):
        ranking = candidates[:]
        rng.shuffle(ranking)
        votes.append(ranking)
    return votes


def _make_scores(num_voters: int, num_candidates: int, seed: int, max_score: int = 5) -> List[Dict[str, int]]:
    rng = random.Random(seed)
    candidates = [f"C{i}" for i in range(num_candidates)]
    return [{c: rng.randint(0, max_score) for c in candidates} for _ in range(num_voters)]


def _assert_under_ceiling(benchmark: Any, name: str, ceiling_s: float) -> None:
    mean_s = benchmark.stats.stats.mean
    assert mean_s < ceiling_s, (
        f"{name}: mean {mean_s * 1000:.1f}ms exceeds the {ceiling_s * 1000:.0f}ms "
        f"ceiling at {NUM_VOTERS} voters / {NUM_CANDIDATES} candidates. This "
        "ceiling is deliberately generous (15-500x the measured baseline, see "
        "module docstring) -- a real trip here means a genuine algorithmic "
        "regression, not CI noise."
    )


# The 21 ordinal rules locked in the client<->backend parity harness
# (scripts/gen_engine_parity.py's `RULES` dict) -- this benchmark suite
# mirrors that exact set so every rule with a production frontend twin has a
# perf floor, not an arbitrary subset. `kemeny` is handled separately below
# (two input sizes, two code paths -- see module docstring).
ORDINAL_CASES: List[tuple] = [
    ("plurality", ranked.get_plurality_winner, FAST_CEILING_S),
    ("two_round", ranked.get_two_round_winner, FAST_CEILING_S),
    ("borda", ranked.get_borda_winner, FAST_CEILING_S),
    ("dowdall", ranked.get_dowdall_winner, FAST_CEILING_S),
    ("anti_plurality", ranked.get_anti_plurality_winner, FAST_CEILING_S),
    ("bucklin", ranked.get_bucklin_winner, FAST_CEILING_S),
    ("irv", ranked.get_irv_winner, HEAVY_CEILING_S),
    ("coombs", ranked.get_coombs_winner, HEAVY_CEILING_S),
    ("benham", ranked.get_benham_winner, HEAVY_CEILING_S),
    ("raynaud", ranked.get_raynaud_winner, HEAVY_CEILING_S),
    ("nanson", ranked.get_nanson_winner, HEAVY_CEILING_S),
    ("baldwin", ranked.get_baldwin_winner, HEAVY_CEILING_S),
    ("condorcet_copeland", ranked.get_copeland_winner, HEAVY_CEILING_S),
    ("minimax", ranked.get_minimax_winner, HEAVY_CEILING_S),
    ("schulze", ranked.get_schulze_winner, HEAVY_CEILING_S),
    ("ranked_pairs", ranked.get_ranked_pairs_winner, HEAVY_CEILING_S),
    ("river", ranked.get_river_winner, HEAVY_CEILING_S),
    ("smith_irv", ranked.get_smith_irv_winner, HEAVY_CEILING_S),
    ("split_cycle", ranked.get_split_cycle_winner, HEAVY_CEILING_S),
    ("black", ranked.get_black_winner, HEAVY_CEILING_S),
]

CARDINAL_CASES: List[tuple] = [
    ("score", lambda scores: score.get_simple_score_winner(scores), FAST_CEILING_S),
    ("star", lambda scores: score.get_star_voting_winner(scores), FAST_CEILING_S),
    ("cumulative", score.get_cumulative_winner, FAST_CEILING_S),
    ("maximin", score.get_maximin_score_winner, FAST_CEILING_S),
    ("nash", score.get_nash_winner, FAST_CEILING_S),
]


@pytest.fixture(scope="module")
def ordinal_votes() -> List[List[str]]:
    return _make_votes(NUM_VOTERS, NUM_CANDIDATES, seed=_ORDINAL_SEED)


@pytest.fixture(scope="module")
def cardinal_scores() -> List[Dict[str, int]]:
    return _make_scores(NUM_VOTERS, NUM_CANDIDATES, seed=_CARDINAL_SEED)


@pytest.mark.parametrize("name,fn,ceiling_s", ORDINAL_CASES, ids=[c[0] for c in ORDINAL_CASES])
def test_ordinal_engine_benchmark(
    benchmark: Any, ordinal_votes: List[List[str]], name: str, fn: Callable[..., Any], ceiling_s: float
) -> None:
    benchmark.pedantic(fn, args=(ordinal_votes,), rounds=BENCHMARK_ROUNDS, warmup_rounds=WARMUP_ROUNDS)
    _assert_under_ceiling(benchmark, name, ceiling_s)


@pytest.mark.parametrize("name,fn,ceiling_s", CARDINAL_CASES, ids=[c[0] for c in CARDINAL_CASES])
def test_cardinal_engine_benchmark(
    benchmark: Any, cardinal_scores: List[Dict[str, int]], name: str, fn: Callable[..., Any], ceiling_s: float
) -> None:
    benchmark.pedantic(fn, args=(cardinal_scores,), rounds=BENCHMARK_ROUNDS, warmup_rounds=WARMUP_ROUNDS)
    _assert_under_ceiling(benchmark, name, ceiling_s)


@pytest.mark.parametrize(
    "case_name,num_candidates",
    [("kemeny_exact_6cand", 6), ("kemeny_approx_8cand", 8)],
    ids=["kemeny_exact_6cand", "kemeny_approx_8cand"],
)
def test_kemeny_young_engine_benchmark(benchmark: Any, case_name: str, num_candidates: int) -> None:
    votes = _make_votes(NUM_VOTERS, num_candidates, seed=_KEMENY_SEED)
    benchmark.pedantic(ranked.get_kemeny_young_winner, args=(votes,), rounds=BENCHMARK_ROUNDS, warmup_rounds=WARMUP_ROUNDS)
    _assert_under_ceiling(benchmark, case_name, HEAVY_CEILING_S)
