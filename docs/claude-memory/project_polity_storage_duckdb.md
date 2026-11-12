---
name: project-polity-storage-duckdb
description: "§16.6 storage lot shipped in PR #140, merged to develop — compaction.py builds a DuckDB analytical store per run, motif-only codebook decoding"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9988b0af-d35f-4d22-b8d0-3ab9d9b157f8
  modified: 2026-08-15T02:23:37.609Z
---

The design doc's §16.6 storage decision (DuckDB vs Postgres, previously marked 🟡 open) is resolved and implemented: `compaction.py` (new module in `fast_api_voter/api/domain/polity/`) compacts a run's raw JSONL journal into a `.duckdb` file beside it, merged to `develop` 2026-08-15 (PR #140).

**Resolution: DuckDB, not Postgres.** `fast_api_voter` has no existing SQL stack (only Redis, a cache); the only Postgres anywhere in the repo is an unrelated Umami web-analytics project. DuckDB is embedded/serverless — one pinned dependency (`duckdb==1.5.5`), zero new infrastructure. Unlike the vLLM switch, this lot needed no GPU/live-verification deferral — fully offline-testable against a real embedded DuckDB instance.

**Scope, deliberately narrow:** decodes the `motif` field only (via a `citizen_events_decoded` view joining against a `codebook_motifs` table, built from a new `codebook.motif_labels()` function — never rewriting the raw `citizen_events` table, per §3.7.4's "jamais par réécriture du journal brut"). Other enumerated payload fields (`act`, `stance`, `bf`, etc.) are explicitly deferred to a future §16.7 biography-view lot — they're one-liners at query time (`payload ->> '$.act'`) and don't need the store to change. `RunMetrics` (indexer.py's output) is deliberately NOT persisted into the store, to avoid creating a second source of truth alongside `metrics.json` (§16.2's own stated principle).

**A real, non-obvious finding worth remembering:** DuckDB 1.5.5 has an operator-precedence gotcha — an unparenthesized `x = 'a' AND payload ->> '$.k' = 'b'` silently mis-binds and errors trying to cast the whole JSON payload to a number. Fix: always parenthesize `(payload ->> '$.k')` when combined with `AND`/`=`. Documented in `compaction.py`'s own docstring so future query-writers don't rediscover it.

**Test-suite wall-clock cost, and how it was handled:** wiring compaction into `run_simulation` (via the already-shipped-but-previously-unconsumed `journal.index_after_run` flag) made the `test_polity_run_simulation.py` suite jump from ~17s to ~207s, since many tests build large journals (1000+ events under awakening/petition/mobilization). Fixed by overriding `index_after_run=False` in the shared test-config helper (`_config_with_output_dir`, which every other test helper chains through) — the shipped YAML default stays `true`; only the test suite's cost was addressed. See [[feedback_llm_reliability_investigation]]'s sibling principle: measure before assuming a change is cheap.

**How to apply:** if extending decode scope to payload fields (§16.7's eventual job), the raw `citizen_events` table should never need to change — only a new codebook table + a wider view, since decoding is a JOIN by design. If a future lot wants cross-run metric comparison in SQL (not just per-run `metrics.json` files), that's the trigger to reconsider persisting `RunMetrics`, deliberately not done here.
