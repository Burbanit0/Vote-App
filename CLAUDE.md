# CLAUDE.md

Guidance for Claude Code working in this repo. README.md covers the product and
local setup; this file covers the things an agent needs that aren't obvious from
the code.

## Layout

- `voter-app/` — frontend: React 19 + TS + Vite + Tailwind v4 + shadcn (hand-written
  primitives in `src/components/ui/`). Run frontend commands from this directory.
- `fast_api_voter/` — backend: FastAPI (strangler-fig migration off Flask, now
  complete). The authoritative voting engine lives here.

## Gate commands

Frontend (run in `voter-app/`):

```bash
npx tsc --noEmit            # types (also the first half of `npm run build`)
npx vitest run             # unit tests
npm run lint               # eslint . --ext .js,.jsx,.ts,.tsx  (0 errors is gating)
npx prettier --config .prettierrc --write <files>
npm run build              # tsc --noEmit && vite build && size-limit (1 MB brotli budget)
npm run test:e2e           # Playwright, chromium + firefox + webkit + mobile
```

**The e2e suite is a required gate** (`.github/workflows/e2e.yml`), not just at release.
It runs on every PR that touches `voter-app/**`, `e2e.yml` itself, or the backend's
runtime code (`fast_api_voter/**` minus `scripts/`, `api/tests/` and `*.md`), in two shards; the required
"Playwright E2E" is the aggregator job that merges their reports. It needs the backend on `:4434` (`uvicorn api.main:app --port 4434` in
`fast_api_voter/`) — Assemblée mode and two Laboratoire fiches hit it; Playwright
starts the frontend itself. Start it with `POLITY_RUN_ROOTS` unset, so `/api/v2/polity`
serves exactly the committed fixture run (`fast_api_voter/polity_fixtures/`).

Two rules keep it from rotting the way it did before (5 specs frozen against a
UI that had moved on for two months):

- **Routes are data.** `voter-app/src/routes.ts` holds the surfaces and the
  legacy redirects; `App.tsx` renders from it and `tests/e2e/routes.ts` reads it.
  Add a route there and the suite covers it; a surface with no test anchor fails
  the run.
- **Anchor on `data-testid`, never on CSS classes or translated strings.** The
  old suite matched `.card`/`.badge` and French labels; both moved. Tests run in
  `fr-FR` (the Playwright config pins the locale) but assert on testids.

Backend (run in `fast_api_voter/`):

```bash
python -m pytest <paths> -o addopts="" -q   # -o addopts="" disables the coverage
                                            # gate from pyproject for a quick run
mypy api/                                    # strict, must stay clean
```

`scripts/fast-gate.sh <base>` runs the relevant subset of all of the above on a branch's
changed files (the push guard runs it before every `git push`). A `SKIPPED` section is not a
pass: it means the tool could not run here (missing deps, or a `python3`/`python` older than
`mypy.ini`'s `python_version`), and CI is then the only check, so say so under **Non vérifié**.
A PR touching `.github/workflows/` or `.claude/hooks/` must also pass the required
`Workflow lint` (actionlint + `zizmor --offline` + `python3 -m unittest discover -s
.claude/hooks/tests`).

A test that checks an invariant of `docs/spec/behaviors.md` carries
`@pytest.mark.behavior("<ID>")`; `api/tests/test_behavior_catalogue.py` keeps the catalogue
and the markers in step. Finished experiment scripts live in `fast_api_voter/scripts/archive/`
(see its README): not imported, type-checked or import-smoked.

`-o addopts=""` only skips coverage for the quick local run — full coverage is
still enforced by `ci-local/` and GitHub CI, so never use this flag to judge
whether a change is actually covered.

CI mirror: `ci-local/` is a Dockerised harness that mirrors GitHub CI — run it
before opening PRs when in doubt.

## The dual voting engine — keep it in sync

There are **two** implementations of the voting rules, and a test locks them
together. Do not let them drift.

- Client (live, fast, spatial): `voter-app/src/lib/playgroundVoting.ts`.
  `ruleWinnerFromRanks(ranks, m, rule, scores?)` is the dispatch entry. Voter
  utility = `-distance + valence` (valence optional, 0 by default).
- Backend (authoritative, tested): `fast_api_voter/api/engine/utils/
  simulation_ranked_utils.py` + `simulation_score_utils.py`.
- Parity harness: `fast_api_voter/scripts/gen_engine_parity.py` generates golden
  winners → `voter-app/src/lib/__fixtures__/engineParity.json`; asserted by
  `playgroundVoting.parity.test.ts`. 28 methods are locked identical: 21 ordinal,
  score/STAR/cumulative/maximin/nash over a shared score matrix, approval, and
  majority judgment. `KNOWN_DIVERGENT` (an exact mismatch list per rule, not a
  count) is empty and should stay that way. Approval is locked **at the tally
  only**: both sides get the same 0/1 ballot, because each engine derives
  approvals from utility its own way (client ≥ 0.5; backend above the voter's
  mean, or approve-top-2 in most backend callers), and those still disagree.
  `random_ballot` stays excluded (a lottery).

**If you change a rule on either side**: re-run `PYTHONHASHSEED=0 python
fast_api_voter/scripts/gen_engine_parity.py` (it refuses to run without the seed
pinned, so the fixture stays reproducible), then run the parity test. A change that breaks parity is a
bug until proven otherwise (the harness has caught real bugs on both sides).

`engineParity.json` is a **generated artifact** — never hand-edit it (not even to
silence a failing parity test); always regenerate it via `gen_engine_parity.py`.
This is enforced, not just written down: `.claude/settings.json`'s `PreToolUse`
hook blocks any Edit/Write/MultiEdit targeting the file, and a `PostToolUse`
hook reminds to regenerate parity whenever either side of the engine changes.

## Playground architecture

The playground is a single "instrument" with a 5-moment rail (Électorat → Méthode →
Stratégie → Campagne → Bilan) and a Dirigeant↔Assemblée toggle. All state and
derivations live in `PlaygroundController.tsx`, exposed through **contexts split by
concern** so a consumer re-renders only when a slice it actually reads changes:

- `useStoreCtx()` — config/playground bindings and pure reads of them (`mode`, `dims`,
  `electorate`…). Changes only on a settings edit.
- `useJourneyCtx()` — active moment, rule under examination, map lens. Discrete clicks.
- `useInstrumentCtx()` — live spatial data (voters, candidates, drag/shake). The
  **high-frequency** one: every candidate drag frame recomputes it.
- `useScorecardCtx()` — async diagnostics + the Monte-Carlo scorecard/values dial.
- `useMethodSelection()` — `enabledRules`/`setEnabledRules`/`lensItems` (the first
  slice split out, for MethodMoment's rapid-fire rule checkboxes).

`usePlaygroundCtx()` is a composed view over the first four — fine for a consumer that
genuinely reads (nearly) every slice (`InstrumentPanel`, `StrategyMoment`,
`BilanMoment`), but it re-renders on **any** slice changing. **For a new consumer, use the
narrowest hook(s) it needs**, and put a new field in the context matching how often it
changes — a low-frequency value placed in `instrumentCtx` drags its readers along on every
drag. `PlaygroundController.render.test.tsx` asserts the isolation directly. Analytical
panels (sincerity, equilibrium, robustness, real-election backtest, valence) are pure
libs in `src/lib/` with a thin component each.

## i18n

- Namespace `playground` (`src/i18n/locales/playground.fr.ts` is the source of truth
  and the type; `playground.en.ts` must mirror it key-for-key — tsc enforces this).
- **Tests run in English** (jsdom). Assert EN strings, not FR.

## Definition of done

A change is done when it does **what was asked**, not when it compiles and CI is green.
Before opening a PR:

- Run `/verify "<the original request, verbatim>"`. It runs `scripts/fast-gate.sh`, then
  the `spec-checker` agent, which sees only the request and the diff, never your summary.
  A `FAIL` (something asked is missing) means no PR yet.
- Fill the PR template's `## Demande` (verbatim), `## Critères d'acceptation` and
  `## Preuves` (commands actually run and their output) sections.
- The **Non vérifié** line is mandatory: say what you did not check and why. "rien" only
  when true. An unverified claim stated as done is worse than a gap stated plainly.

## Workflow (mandated)

- **`polity` is the working branch** (since the 2026-09-27 convergence, #671/#674/#675,
  `develop` and `polity` were identical). One branch per step, **from `polity`**,
  named for what it does: `feat/*`, `fix/*`, `refactor/*`, `ci/*`, `chore/*`. Never
  commit features directly to `polity` or `develop`; never rewrite their pushed
  history.
- Open a PR per step against `polity`. Merge with `--no-ff`. `develop` only receives
  release syncs (`chore/sync-polity-into-develop-<date>`, a real merge commit), and
  `develop → main` is the release (see the `release` skill).
- Repo is public (MIT). Commit author email is the `noreply` form for new commits.
- **Run `/code-review high` on the branch *before opening* any PR**, once, then fix
  what it finds rather than re-running it. It matters most on the voting engine
  (`simulation_ranked_utils.py`, `simulation_score_utils.py`, `playgroundVoting.ts`)
  and other high-blast-radius surfaces (auth-adjacent config, CI/CD workflows, the
  parity/axiom test harnesses). Run it before opening, not "before merging":
  the Mergify queue (on `polity` and `develop`) auto-merges the moment required checks go green, often
  within minutes of opening the PR, so a review gated on merge time can be (and has
  been) raced and skipped entirely. It runs locally on the branch's diff and needs
  no PR or GitHub remote, so there's no reason to wait for one. It exists and is
  underused — standard CI gates catch regressions in what's already tested, not a
  subtly-wrong new rule implementation or a logic error a human reviewer would
  have caught.
- PRs touching the high-risk paths listed in
  `.mergify.yml`, or that weaken the test suite (fewer tests in the changed test
  files, or an added skip/only/xfail: `scripts/check_test_integrity.py`, which
  `scripts/fast-gate.sh` also reports before a push), are held until the owner comments `/reviewed <sha>`
  (`human-review.yml` binds that approval to the commit and releases the required
  `High-risk review gate` status). A regenerated test oracle (parity fixture, golden,
  OpenAPI contract, baselines, snapshots) passes its own check by design, so
  `scripts/oracle_diff_report.py` spells out what it changed (winners by rule, moved values)
  in the gate's run summary and in fast-gate: say it in the PR too. **Never post
  `/reviewed`, add a `reviewed` label, set a `human-review` or `High-risk review gate` status, or merge a PR
  yourself** — that approval is the owner's alone.
