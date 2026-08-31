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
npm run build              # tsc --noEmit && vite build
npm run test:e2e           # Playwright, chromium + firefox (~1.5 min)
```

**The e2e suite is a gate on every PR** (`.github/workflows/e2e.yml`), not just at
release. It needs the backend on `:4434` (`uvicorn api.main:app --port 4434` in
`fast_api_voter/`) — Assemblée mode and two Laboratoire fiches hit it; Playwright
starts the frontend itself.

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
  `playgroundVoting.parity.test.ts`. 17 methods are locked identical (15 ordinal +
  score + STAR). `KNOWN_DIVERGENT` is empty.

**If you change a rule on either side**: re-run `python fast_api_voter/scripts/
gen_engine_parity.py`, then run the parity test. A change that breaks parity is a
bug until proven otherwise (the harness has caught real bugs on both sides).

`engineParity.json` is a **generated artifact** — never hand-edit it (not even to
silence a failing parity test); always regenerate it via `gen_engine_parity.py`.

## Playground architecture

The playground is a single "instrument" with a 5-moment rail (Électorat → Méthode →
Stratégie → Campagne → Bilan) and a Dirigeant↔Assemblée toggle. All state and
derivations live in `PlaygroundController.tsx` and flow through one context
(`usePlaygroundCtx`); moment panels and the instrument are thin consumers. Analytical
panels (sincerity, equilibrium, robustness, real-election backtest, valence) are pure
libs in `src/lib/` with a thin component each.

## i18n

- Namespace `playground` (`src/i18n/locales/playground.fr.ts` is the source of truth
  and the type; `playground.en.ts` must mirror it key-for-key — tsc enforces this).
- **Tests run in English** (jsdom). Assert EN strings, not FR.

## Workflow (mandated)

- One `feat/*` branch per step, **from `develop`**. Never commit features directly
  to `develop`; never rewrite already-pushed `develop` history.
- Open a PR per step against `develop`. Merge with `--no-ff`. `develop → main` for
  releases.
- Repo is public (MIT). Commit author email is the `noreply` form for new commits.
