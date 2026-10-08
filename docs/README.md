# Documentation surfaces

Vote-App has several documentation surfaces, and they used to overlap badly
(Lot 0.1 of the [technical solidity plan](plan/vote-app/PLAN_SOLIDITE_TECHNIQUE.md)).
Each one has its own job and its own rhythm. Mixing them up, more than any lack
of discipline, is what made them drift.

| Surface | Job | Rhythm |
|---|---|---|
| [`docs/STATUS.md`](STATUS.md) | **Start here.** Where each part stands, the next 3 steps, the open questions. One page. | At the end of each plan phase, and whenever the next steps change |
| `docs/plan/` | Plans. The live one is [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md). Most other plans are finished and kept as history; few say so yet (`PLAN_BEYOND_CI.md` W4 adds a status line to each). | Per plan |
| `docs/exploration/EXP-*.md` | One file per tool or method tried: the verdict (adopted, rejected or suspended), plus what it actually found and cost. | Per closed experiment (`/log-experiment`) |
| `docs/exploration/README.md` | Index of every verdict. | Each time an experiment closes |
| `docs/adr/` | Binding architecture decisions, with the alternatives that were rejected. | Rarely |
| `docs/spec/behaviors.md` | Polity's behaviour catalogue: each invariant, with the test that locks it (`@pytest.mark.behavior`). | With the code |
| `docs/journal/commits.jsonl` | Generated machine trace of every commit, for archaeology. | Per commit, in the polity worktree only (`scripts/git_commit_capture.py`); enable it once per clone with `pre-commit install --hook-type post-commit` |
| `…/run/<run>/digest.json` + `digest.jsonl` | Machine trace of a simulation run: outcome (finished, crashed or interrupted), ticks reached, counts of every event type per year, population impact. Generated, never written by hand. | At **every** run end, crashes and interruptions included (`api/domain/polity/run_digest.py`) |
| `…/run/<run>/progress.json` | Live state of a running run: the completed tick **and the one in progress**, decisions by type, fallbacks, and an **LLM heartbeat** (`last_llm_response_at`). The only surface that answers "is this run alive?"; read it with `fast_api_voter/scripts/check_run_liveness.py`. | Per tick **and** on every LLM response (throttled to 5 s) |
| `…/run/<run>/TIMELINE.md` | The readable story of a run: what this simulated society went through, and what the population did. Written from the digest, never from raw logs. | Per finished run (`/log-run` → `run-narrator` sub-agent) |
| `docs/claude-memory/` | A versioned snapshot of the coding agent's memory: pitfalls reloaded each session. The live memory sits outside the repo; this copy is resynced by hand and can lag. | When a lesson is worth keeping |
| `docs/plan/vote-app/CODE_AUDIT.md` | Dated, replayable health check of the code. | Per cleanup pass |
| `docs/journal/JOURNAL_DE_BORD.md` | **Retired 2026-10-08.** A narrative log per work session, from 2026-09-04 to 2026-09-27 (older, reconstructed history in `docs/journal/archive/`). Kept as history; `STATUS.md` and PR bodies carry the state now. | — |

## Which surface?

- **What's the state of things, and what's next?** → `docs/STATUS.md`.
- **I tried a tool or a method and want to keep the verdict** →
  `/log-experiment` → `docs/exploration/EXP-*.md`, indexed in
  `docs/exploration/README.md`.
- **A structural decision was taken, alternatives were rejected, and it must
  still make sense in a year** → an ADR in `docs/adr/`.
- **A simulation run just finished (or died) and I want to know what
  happened** → `/log-run` → `TIMELINE.md` next to the run's `events.jsonl`,
  written from its `digest.json`.
- **How healthy is the code overall?** → `docs/plan/vote-app/CODE_AUDIT.md`.

## Language

New docs are written in English (decided 2026-10-08, `PLAN_BEYOND_CI.md` D3).
A living doc moves to English when it is next rewritten; a small fix keeps the
doc's current language rather than mixing two in one paragraph. Finished plans stay in the
language they were written in. THEORY.md and GUIDE_UTILISATEUR.md are
user-facing French reference and stay French for now.

## What this file is not

It is not one more log. It tells nothing by itself; it points to the right
surface. If it has to change every session, that means a new surface was added
and belongs here, not that this file should turn narrative.
