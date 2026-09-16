# The run explorer (the Vote App's Polity page)

`/polity` replays a finished polity simulation run tick by tick. It shows:

- **Who governs, who runs, who votes and who protests**, on a map of the population.
- **The institutional timeline:** terms and events.
- **The run's curves:** legitimacy, pressure and elections.
- **One citizen's story.**

It reads a run's files and never writes to them. Nothing in it calls a model.

## Opening a run

Unset, the API serves only the committed fixture run
(`fast_api_voter/polity_fixtures/runs/explorer-fixture`). To read real runs, name their roots:

```bash
cd fast_api_voter
POLITY_RUN_ROOTS=p500=/path/to/Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs \
  uvicorn api.main:app --port 4434
cd ../voter-app && npm start        # then open http://localhost:3000/polity
```

- **Roots:** `POLITY_RUN_ROOTS` takes `label=path` pairs, separated by commas.
- **Run keys:** a run is known by a key derived from its root's label and its path inside that root. The same run has the same key on any machine that mounts it under the same label.
- **No paths leave the server:** no absolute path appears in a response.
- **When a run is listed:** it must have a journal (`events.jsonl`), a `config.json` and a census (`snapshots.jsonl`), and every file the explorer reads from it — those three plus `checkpoint.json`, `progress.json`, `run_metadata.json`, `digest.json` and `llm_calls_summary.json` — must resolve inside its root and be at most `POLITY_EXPLORER_MAX_JOURNAL_BYTES` (64 MB by default; each is read whole into memory). A run holding a file that escapes its root, by symlink or otherwise, is not listed at all, so no reader downstream has to be careful.
- **Crashed and interrupted runs** are listed too. Ticks after the last checkpoint are marked unconfirmed.
- **Caching:** the last `POLITY_EXPLORER_CACHE_RUNS` runs opened (4 by default) stay loaded. Each is reloaded when its journal changes.
- **E2E:** the e2e backend runs with `POLITY_RUN_ROOTS` unset (CLAUDE.md), so the Polity specs see exactly the fixture run.

## What a frame is, and how exact it is

A frame is the state after its tick, plus what happened in it. The API serves frames in chunks of 40 ticks.

**Per-citizen codes:**

- **Status:** elector, candidate or elected.
- **Chamber:** whether the citizen holds a sortition-chamber seat.
- **Pressure act.**
- **Ballot:** blank, for the winner, for another candidate, or none journaled.
- **Candidacy:** the furthest stage reached in the tick.

**The president:** position, pledge position, legitimacy, écart, mandate strength and lame duck.

**Replay.** `api/domain/polity/run_frames.py` replays the journal between the yearly censuses. Each event is applied the way `run_polity_simulation` applied the decision it records, and each year restarts from its census.

**The oracle** (`api/tests/polity_explorer_fixtures.replay_mismatches`) replays whole runs without that restart. It requires every census and the final checkpoint to come out exactly: roles, offices, pledges, revealed positions, chamber seats. It holds on:

- invalidated elections with reruns;
- staggered campaigns with recalls;
- the audited utility vote;
- the deterministic engine;
- opinion dynamics;
- p500 seeds 1 and 2.

**What is not exact:**

- **Dynamic runs:** with opinion dynamics, views move every tick but only the census records them. Citizens therefore move once a year on the map. A standing candidate's pledge between two censuses is placed at their view from the last census. The president's pledge comes whole from the journal, and it is the only pledge the map draws.
- **Ballots:** the vote lens shows what was journaled.
  - *All ballots:* LLM vote mode, and older runs.
  - *Audit sample:* S4.1's utility vote journals only the 10% audit sample.
  - *None:* the deterministic engine journals no ballot.

  The page says which case applies, and so does every election's blank share, which names its source.

## The map

**Factor-structure populations** use their two latent factors directly:

- **Citizens** sit at their factors, redrawn from the seed and checked against the tick-0 census.
- **Pledges, drift and party platforms** are placed by least squares in logit space against the same loadings.
- **Axes** read "Latent axis 1/2", with the issues loading most on each. The axes have no economic or societal names.

**Other populations** fall back to the census's first two principal components, as does a population whose redrawn structure doesn't reproduce the census.

**Drawing (ADR-013):** citizens are drawn on a canvas. Parties, the president, the selection and the axes are SVG over it. The tests check the scene and a recording context, not pixels.

## Measured on real runs

`fast_api_voter/scripts/check_polity_explorer_real_runs.py` reads every run under the given roots through the API and records times and sizes in `check_polity_explorer_real_runs_results.md`.

| p500 run (8 years) | Overview, cold / cached | All frames |
|---|---|---|
| seed 1 | 0.11 s / 5 ms | 210 KB |
| seed 2 | 0.10 s / 5 ms | 209 KB |
| seed 42 (crashed at tick 13) | 0.05 s / 5 ms | 89 KB, one tick unconfirmed |

The plan's budgets are 1.5 s cold, 50 ms cached and 400 KB of frames.

## Maintaining it

- **The fixture run:** regenerate with `python scripts/gen_polity_explorer_fixture.py` from `fast_api_voter/`.
  - **Manifest:** `MANIFEST.json` records each file's sha256 and the config hash. `test_polity_explorer_fixture.py` fails if the files, the config or the replay drift.
  - **Not regenerated in CI:** floats can differ in the last bits across BLAS builds, so regenerating is a reviewed change.
- **Screenshot baselines:** they come from the pinned Playwright image. A change to the page updates `surface-polity`, and a change to the map updates `polity-map-election`.
  1. Dispatch `e2e.yml` on the branch (`gh workflow run e2e.yml --ref <branch>`).
  2. Take the actual screenshots from its `playwright-report-visual` artifact.
  3. Check the diff against the change before committing them.
- **Pseudo-locale:** the sweep names the elements that overflow. Two WebKit-only overflows were found while building the page:
  - the React Query Devtools toggle, now kept out of automated browsers;
  - an option wider than its `<select>`, which WebKit counts into the page's scrollable width. The run picker's label clips horizontal overflow for that reason.

## Known limits

- **`GET /runs` is not paginated, and it re-walks every root on each request.** Each run costs a
  directory scan and its registry row (five small JSON reads and the journal's last 64 KB): measured
  at about 1 ms per run, so 100 runs answer in roughly 0.1 s and a root of a few thousand runs would
  take seconds. The three single-run routes pay only the scan, not the rows. Roots are a deliberate
  opt-in for a handful of batches; a root large enough for this to matter wants pagination and a
  cached scan, which v1 does not have.
- **The cache bounds runs, not bytes.** `POLITY_EXPLORER_CACHE_RUNS` counts runs, and a loaded run
  holds several times its journal in memory, so a large `POLITY_EXPLORER_MAX_JOURNAL_BYTES` and a
  large cache multiply. The defaults (4 runs, 64 MB) are sized for the p500 batch.

## Not in v1

- **Live runs:** following a run while it is still running.
- **Legislation:** bill-by-bill legislative detail beyond the timeline's glyphs.
- **Comparison:** comparing several runs side by side.
