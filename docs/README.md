# Documentation surfaces

Vote-App has several documentation surfaces, and they used to overlap badly
(Lot 0.1 of the [technical solidity plan](plan/vote-app/PLAN_SOLIDITE_TECHNIQUE.md)).
Each one has its own job and its own rhythm. Mixing them up, more than any lack
of discipline, is what made them drift.

| Surface | Job | Rhythm |
|---|---|---|
| [`docs/STATUS.md`](STATUS.md) | **Start here.** Where each part stands, the next 3 steps, the open questions. One page. | At the end of each plan phase, and whenever the next steps change |
| `docs/plan/` | Plans. The current one is [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md). Each plan's first lines say its status; [Plans](#plans) below lists them all. | Per plan |
| `docs/exploration/EXP-*.md` | One file per tool or method tried: the verdict (adopted, rejected or suspended), plus what it actually found and cost. | Per closed experiment (`/log-experiment`) |
| `docs/exploration/README.md` | Index of every verdict. | Each time an experiment closes |
| `docs/adr/` | Binding architecture decisions, with the alternatives that were rejected. | Rarely |
| `docs/spec/behaviors.md` | Polity's behaviour catalogue: each invariant, with the test that locks it (`@pytest.mark.behavior`). | With the code |
| `docs/journal/commits.jsonl` | Generated machine trace of every commit, for archaeology. | Per commit, in the polity worktree only (`scripts/git_commit_capture.py`); enable it once per clone with `pre-commit install --hook-type post-commit` |
| `…/run/<run>/digest.json` + `digest.jsonl` | Machine trace of a simulation run: outcome (finished, crashed or interrupted), ticks reached, counts of every event type per year, population impact. Generated, never written by hand. | At **every** run end, crashes and interruptions included (`api/domain/polity/run_digest.py`) |
| `…/run/<run>/progress.json` | Live state of a running run: the completed tick **and the one in progress**, decisions by type, fallbacks, and an **LLM heartbeat** (`last_llm_response_at`). The only surface that answers "is this run alive?"; read it with `fast_api_voter/scripts/check_run_liveness.py`. | Per tick **and** on every LLM response (throttled to 5 s) |
| `…/run/<run>/TIMELINE.md` | The readable story of a run: what this simulated society went through, and what the population did. Written from the digest, never from raw logs. | Per finished run (`/log-run` → `run-narrator` sub-agent) |
| `docs/claude-memory/` | A versioned snapshot of the coding agent's memory: pitfalls reloaded each session. The live memory sits outside the repo; this copy is resynced by hand and can lag. | When a lesson is worth keeping |
| `docs/plan/vote-app/CODE_AUDIT.md` | Dated health check of the code (2026-08-20 to 2026-09-13), with the commands to replay it. Kept as history. | — |
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
- **How healthy is the code overall?** → today's numbers are the CI ratchets
  (`.github/quality-baseline.json`); `docs/plan/vote-app/CODE_AUDIT.md` is the dated
  baseline they started from.

## Plans

Every plan's first lines say its status: **live** (being executed or maintained),
**reference** (consulted, not executed), **done**, **superseded** (by another plan), or
**history** (a record, not a plan to follow).

| Live | Reference |
|---|---|
| [`PLAN_BEYOND_CI.md`](plan/PLAN_BEYOND_CI.md), the current plan | [`polity/polity-simulation-design-v2.md`](plan/polity/polity-simulation-design-v2.md), the authority on intent |
| [`polity/plan-polity-agency-roadmap.md`](plan/polity/plan-polity-agency-roadmap.md) | [`polity/polity-llm-reference.md`](plan/polity/polity-llm-reference.md), what the simulator does today |
| [`polity/plan-polity-build-order.md`](plan/polity/plan-polity-build-order.md) | [`polity/polity-decision-contracts.md`](plan/polity/polity-decision-contracts.md) |
| [`vote-app/PLAN_SOLIDITE_TECHNIQUE.md`](plan/vote-app/PLAN_SOLIDITE_TECHNIQUE.md) | [`polity/observations.md`](plan/polity/observations.md), the OBS log |
| [`vote-app/PLAN_SURFACE_EXTERIEURE.md`](plan/vote-app/PLAN_SURFACE_EXTERIEURE.md) | [`polity/fit-for-inference.md`](plan/polity/fit-for-inference.md) |
| [`vote-app/LISTING_ORDER_TIES.md`](plan/vote-app/LISTING_ORDER_TIES.md) | [`polity/polity-run-explorer.md`](plan/polity/polity-run-explorer.md), [`polity/tech-radar.md`](plan/polity/tech-radar.md) |

- **Done (16):** `vote-app/` PLAN, PLAN_A_VOUS_DE_JOUER, PLAN_CI_STRUCTURAL_GAPS,
  PLAN_METHODES_HISTOIRES_ATLAS, PLAN_REMEDIATION_CI_CD, PLAN_UX_ACCESSIBILITE,
  prompt-mutation-testing; `polity/` DEMARRAGE-polity-v0, dev-plan-v0-worktree,
  plan-calibration-ambition, plan-coalition-negotiation-v7,
  plan-distribution-positions-seeds, plan-full-run, plan-llm-decision-audit-sampling,
  plan-rupture-candidacy-threshold, plan-vllm-switch-readiness.
- **Superseded (1):** `polity/plan-flagship-30y-run.md` (by plan-full-run).
- **History (10):** `vote-app/` CODE_AUDIT, RETROSPECTIVE, cihardeningplanv2;
  `polity/` audit-precision-plan, plan-adversarial-framing-collapse,
  plan-decision-quality-validation, plan-llm-protocol-and-theory-program,
  plan-pressure-action-remediation, plan-pressure-action-resolution,
  synthese-programme-llm-2026-09-10.

A "done" plan can still name what it left open; its status line says so
(plan-full-run, plan-distribution-positions-seeds, PLAN_CI_STRUCTURAL_GAPS).

Finished plans stay where they are (moving them would break their links); their status
line says what they are.

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
