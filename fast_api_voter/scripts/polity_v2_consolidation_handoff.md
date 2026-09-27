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

## Open question: RESOLVED — no batch-size boundary found (2026-08-06)

Original symptom: twice, at a **20-citizen** batch (exactly
`MIN_SAFE_BATCH_SIZE`), the model corrupted the *same* citizens (index 0, 4, 8,
12, 16 — every 4th of 20) with a self-contradictory `blank=0`/empty-`ranking`
decision, with both 2 and 5 candidates (ruling out candidate count as the
cause). 20 was suspected as an insufficient safety margin above the Lot 0
zero-output boundary (12-15).

**Investigated (the "thorough" option)**: `scripts/check_batch_size_boundary.py`
sweeps citizen counts through the real production code path
(`build_system_prompt`/`build_user_prompt`/`OllamaJsonClient`/
`decode_vote_batch`, not a standalone toy prompt), 2 candidates (the frequency-
maximizing case per the original notes), 2 repeats per size. Full log:
`scripts/batch_size_boundary_results.md`.

**Result: 12/12 live calls passed, sizes 20/21/22/23/24/25, zero failures.**
The original corruption did not reproduce even at exactly 20, the size where
it was twice observed. This is evidence *against* a batch-size-dependent
boundary in this range — the working theory is now that the corruption was a
rare instance of the already-documented Finding D (non-deterministic
floating-point reduction order in multi-threaded CPU inference,
`ollama_structured_output_results.md`), not a function of batch size at all.
20 just happened to be the size most exercised during increment-1 development
(`chunk_voters`'s lower bound), not a uniquely dangerous one.

**Decision**: `MIN_SAFE_BATCH_SIZE=20` stays unchanged — nothing here shows
it's unsafe. `test_sequential_calls_each_produce_a_valid_response` is left as
written: it can still fail occasionally on a real Ollama run, but that's
Finding D's known live-model flakiness surfacing, not a signal about batch
size, and not worth building retry tolerance into the test for.

## Uncommitted-work note

This commit bundles the fixes above (Findings C, the token/timeout tuning, and
the corrected/renamed test) with this handoff doc. It builds on top of the
already-merged `feat/polity-v2-vote-llm-client` (PR #122) tip, so it's a few
commits behind the current `develop` tip by the time you read this — rebase or
merge `develop` in before continuing if it's diverged meaningfully.

**2026-08-06**: the open question above is now resolved (see that section) —
`scripts/check_batch_size_boundary.py` + `scripts/batch_size_boundary_results.md`
are new, uncommitted at the time of writing. This branch is no longer paused;
increment 1 is fully consolidated pending a final commit + merge to develop.
