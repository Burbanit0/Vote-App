# Polity v2 increment 1 — consolidation handoff (laptop move)

Context: v2 increment 1 (LLM-driven voting via a local Ollama `qwen3:8b`) was
merged to `develop` in PRs #120–122. This branch is a **post-merge consolidation
pass** — running the live tests that weren't executed before merge surfaced and
fixed several real bugs. It's paused mid-investigation, not finished; see
"Open question" below before continuing.

## Reproducing the environment on a new machine

Requires Docker Desktop running.

```bash
docker run -d -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama pull qwen3:8b   # ~5.2GB, one-time
```

If the container already exists but is stopped: `docker start ollama`.
Check it's up: `curl http://localhost:11434/api/tags` should list `qwen3:8b`.

## Getting this branch

```bash
git fetch origin
git checkout wip/polity-v2-consolidation
```

(Or `git worktree add ../Vote-App-polity wip/polity-v2-consolidation` from the
main `Vote-App` clone, if using the worktree-per-chantier convention — see
`CLAUDE.md`.)

## Verifying the baseline (fast, offline, no Ollama needed)

From `fast_api_voter/`:

```bash
python -m mypy api/ --config-file mypy.ini      # must show "Success: no issues found"
python -m pytest api/tests/ -o addopts="" -q    # 592 passed, 4 skipped (the POLITY_LLM_LIVE-gated tests)
python -m flake8 --config=.flake8 api/domain/polity/ api/tests/test_polity_llm_live.py
```

## Running the live tests

```bash
POLITY_LLM_LIVE=1 python -m pytest api/tests/test_polity_llm_live.py -o addopts="" -v
```

Wall-clock warning: each 25-citizen batch takes ~3.5-4 min on CPU (no GPU used in
this investigation). The full-run test (`test_a_short_live_run_produces_a_valid_journal`)
does 4 sequential batches for its one election — expect ~15-20 min for that test
alone; the full file (4 tests) runs ~35-40 min.

## What's already fixed and verified live (see `ollama_structured_output_results.md`
## for the full narrative — Findings A through D)

- Finding A/B (pre-existing, from the original Lot 0 spike): `$ref`/`$defs`
  schema dereferencing, explicit voter-cid enumeration in the prompt.
- Token budget: `compute_max_tokens()` gives a flat 1536-token reasoning headroom
  (Qwen3's `<think>` reasoning shares the completion budget, wasn't previously
  accounted for).
- Client timeout: raised from 300s to 600s default (the one earlier successful
  call took 294.64s — no real margin before).
- **Finding C** (the big one): candidates are also citizens, so candidate cids and
  voter cids share a number space and can collide. `ranking` now uses 1-indexed
  *positions* into the candidate list, never raw candidate cids —
  `sorted_candidates()`/`resolve_ranking_cids()` in `llm_behavior_engine.py`
  translate back to real cids for the ballot and the journal. Verified live, twice,
  on a full simulation run with real overlapping voter/candidate cid ranges
  (`test_a_short_live_run_produces_a_valid_journal` — passes reliably) and on the
  realistic single-election path (`test_cast_votes_against_the_real_client` —
  passes reliably).
- **Finding D**: identical requests (same prompts, same seed, `temperature=0`) are
  NOT guaranteed byte-identical output — a known property of multi-threaded CPU
  inference (llama.cpp), not fixable at the prompt layer. The live test was
  renamed from `test_sequential_calls_are_byte_identical` to
  `test_sequential_calls_each_produce_a_valid_response` and no longer asserts
  byte-identity — see `llm_client.py`'s module docstring for what this means for
  reproducibility (the deferred response cache's job, not a live-model guarantee).

## Open question (why this branch is paused)

`test_sequential_calls_each_produce_a_valid_response` still fails — but not for
the reason it was written to catch. Twice now, at a **20-citizen** batch (exactly
`MIN_SAFE_BATCH_SIZE`), the model corrupted the *same* citizens (index 0, 4, 8, 12,
16 — every 4th of 20) with a self-contradictory `blank=0`/empty-`ranking` decision.
This happened identically with 2 candidates and with 5 candidates, ruling out
candidate count as the cause. The common factor is the batch size itself: 20 was
chosen as "a safety margin above the boundary" after the original Lot 0 sweep
(which tested 12 and 15, not 20 itself) — that margin looks insufficient.

**Practical exposure today: none.** The shipped default config (`population_size:
100`, `llm.max_batch_size: 25`) always chunks into groups of 25, never 20 — every
live test at 25 has passed, every time. This only matters for other
population/batch-size combinations that could legitimately produce a 20-citizen
chunk (`chunk_voters()` explicitly permits exactly `MIN_SAFE_BATCH_SIZE`).

Three ways to close this out (discussed but not yet decided when the laptop move
interrupted):

1. **Cheap**: bump `MIN_SAFE_BATCH_SIZE` above 20 and fix the test to use 25
   citizens like everything else that's passed. No more live-test time, but the
   new threshold is asserted, not verified.
2. **Thorough**: spend a live cycle actually probing where the real safe boundary
   is (a citizen-count sweep at 20/22/25, mirroring the original Lot 0
   methodology) before touching the constant.
3. **Leave it**: `MIN_SAFE_BATCH_SIZE=20` stays as documented, since the shipped
   default never exercises it; just fix the test's batch size to stop it from
   being a false-negative signal.

## Uncommitted-work note

This commit bundles the fixes above (Findings C, the token/timeout tuning, and
the corrected/renamed test) with this handoff doc. It builds on top of the
already-merged `feat/polity-v2-vote-llm-client` (PR #122) tip, so it's a few
commits behind the current `develop` tip by the time you read this — rebase or
merge `develop` in before continuing if it's diverged meaningfully.
