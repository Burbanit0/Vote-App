# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Stack

- **Frontend**: React 19 + TypeScript · React Router v7 · Bootstrap 5 · Recharts · D3 7.x · i18next (FR/EN) · Vite · PWA (vite-plugin-pwa)
  - **Data layer** (Phase 5): TanStack Query v5 + **openapi-fetch** (`src/api/client.ts`, typed against `src/api/types.gen.ts` generated from the FastAPI OpenAPI schema). Panels call `$api.useQuery/useMutation` (`src/api/hooks.ts`); the `services/*Api.ts` wrappers call the `apiPost/apiGet/apiDelete` helpers. A middleware attaches the JWT Bearer from `useAuthStore`. **axios fully removed.**
  - **State layer** (Phase 5.4): **Zustand** stores in `src/stores/` — `useAuthStore`, `useUIStore` (theme/expert/teacher), `useLabStore` (pinned perturbations + animation bus), `useElectionStore` (global config + scenarios). The old `src/context/*` files are thin compatibility shims over these stores (kept until 5.5 repoints consumers).
- **Backend**: **FastAPI** (uvicorn) · SQLAlchemy 2.0 **async** (asyncpg/aiosqlite) · PostgreSQL · Redis · python-socketio (WebSocket, ASGI). *Flask + eventlet fully retired in Phase 4.5.b — see [STRATEGIC_REFACTOR_PLAN.md](STRATEGIC_REFACTOR_PLAN.md).*
- **Auth**: **fastapi-users** · JWT (1h, HS256) · bcrypt (legacy hashes) · OAuth (Google / GitHub)
- **Tests**: Jest 1480+ frontend (160 suites) · pytest 340+ backend (httpx TestClient + pytest-asyncio) · coverage ≥ 30 % (backend)
- **CI/CD**: GitHub Actions — currently disabled (billing limit); branch strategy: `feat/*` → `develop` → `main`

## Commands

### Frontend (`voter-app/`)

```bash
npm start                          # Vite dev server → http://localhost:3000
npm test                           # Jest --watchAll=false --coverage
npx jest src/path/to/file.test.tsx # single file (no coverage)
npm run build                      # production build (includes PWA)
npm run lint                       # ESLint .ts/.tsx
npm run prettier-format            # Prettier format
```

### Backend (`flask_voter_app/`)

The backend is the FastAPI package `flask_voter_app/api/`. (The directory is still
named `flask_voter_app/` for historical reasons; there is no Flask inside.)

```bash
# Run the dev server (FastAPI on :4434)
cd flask_voter_app
uvicorn api.main:app --reload --port 4434
curl http://localhost:4434/api/v2/health
open  http://localhost:4434/api/v2/docs    # Swagger UI (auto-generated)

# With Docker (full stack: FastAPI :4434, PostgreSQL :5432, Redis :6379)
docker-compose up --build

# Tests (in-memory aiosqlite, no DB/Redis needed). FLASK_ENV is the env name the
# Settings still read (api/core/config.py field `flask_env`); "testing" works.
FLASK_ENV=testing python -m pytest                          # whole suite (api/tests)
FLASK_ENV=testing python -m pytest api/tests/test_foo.py -v # single file
python -m mypy api/ --ignore-missing-imports
python -m flake8 api/
```

### Git workflow

```bash
git checkout -b feat/my-feature     # create feature branch from develop
git add <files>
git commit -m "feat(...): ..."
git push origin feat/my-feature
git checkout develop
git merge feat/my-feature --no-ff -m "Merge feat/my-feature into develop"
git push origin develop
# Never push directly to main — CI/CD handles main via Release workflow
```

## Architecture

### Frontend — key directories

```
voter-app/src/
├── pages/                        # Route-level views
│   ├── ElectionLabPage.tsx       # Hub central — 20+ onglets adaptatifs (mobile/desktop)
│   ├── SimulationComparePage.tsx # 14 onglets comparaison
│   ├── HomePage.tsx              # QuickCompareWidget + hero
│   └── ...                      # Campaign, BlankContagion, Quiz, WhatIf, etc.
├── components/
│   ├── shared/                   # Composants réutilisables (panels, charts)
│   └── Simulation/               # Visualisations spécifiques simulation
├── stores/                       # Zustand (Phase 5.4) — source of truth
│   ├── useAuthStore.ts           # user/token/login/logout (client middleware reads it)
│   ├── useUIStore.ts             # theme + expertMode + teacherMode (slides/PDF)
│   ├── useLabStore.ts            # pinned perturbations + animation frame bus
│   └── useElectionStore.ts       # global config + scenarioMeta + SCENARIOS
├── api/                          # typed openapi-fetch client (Phase 5)
│   ├── client.ts                 # createClient<paths> + auth middleware + apiPost/apiGet/apiDelete
│   ├── hooks.ts                  # $api (openapi-react-query) — useQuery/useMutation
│   └── types.gen.ts              # generated from FastAPI OpenAPI (npm run gen:api)
├── context/                      # thin shims over the stores (deleted in 5.5)
│   ├── ElectionContext.tsx       # → useElectionStore
│   ├── AuthContext.tsx           # → useAuthStore
│   └── ThemeContext / ExpertModeContext / TeacherModeContext  # → useUIStore
├── hooks/
│   ├── useDragTouch.ts           # Drag SVG unifié mouse+touch
│   ├── useSwipe.ts               # Swipe mobile pour navigation onglets
│   ├── useMonteCarloStream.ts    # WebSocket streaming Monte Carlo
│   ├── useSimulationWorker.ts    # Web Worker hook (heatmap, matrix)
│   └── useDebouncedSimulation.ts
├── workers/
│   └── simulationWorker.ts       # Web Worker: computeGrid, partialResultsToMatrix
├── services/                     # data wrappers over apiPost/apiGet (→ /api/v2/*)
│   ├── electionApi.ts            # ElectionResult, simulateElection
│   └── simulationCompareApi.ts   # (authApi: JSON via apiClient; form login via raw fetch)
└── utils/
    └── voronoiRegions.ts         # d3-delaunay Voronoi path builder
```

### Frontend — ElectionContext / useElectionStore

La source de vérité globale est désormais **`stores/useElectionStore`** (Zustand,
Phase 5.4) ; `context/ElectionContext` est un shim qui réexpose `useElection()`.
Contenu :
- `config` : candidates (x,y), num_voters, ideology, seed, campaign, blank_vote, information_model
- `setConfig / setConfigDeep` : mutations partielles (persistées dans localStorage)
- `scenarioMeta` : metadata du scénario chargé (France 2002, etc.)
- `SCENARIOS` : configs prédéfinies pour 7 scénarios historiques

### Frontend — ElectionLabPage (hub)

Navigation adaptative :
- **Mobile < 768px** : `Form.Select` + boutons ‹ › (détecté via `MediaQueryList`)
- **Desktop** : Bootstrap `Tabs` contrôlés via `activeTab` state

Onglets actuels (20) :
`results` · `map` · `animation` · `montecarlo` · `manipulability` · `blank-divergence` · `campaign-sensitivity` · `pipeline` · `combined-effects` · `coalition` · `districts` · `primary` · `replay` · `jury` · `adaptive` · `abstention` · `stv` · `gerrymander` · (+ autres à venir)

### Backend — `api/` package (FastAPI, layered)

```
flask_voter_app/api/
├── main.py              # FastAPI app + CORS + lifespan + access-log middleware
│                        #   + slowapi limiter + Socket.IO ASGI wrap
├── core/
│   ├── config.py        # Pydantic Settings (12-factor; reads FLASK_ENV/DATABASE_URL/…)
│   ├── auth.py          # Bearer-JWT dep (HS256, accepts fastapi-users tokens)
│   ├── users.py         # fastapi-users wiring: AsyncUserDatabase adapter + UserManager
│   └── ratelimit.py     # slowapi Limiter (used by the public /api/v1 routes)
├── db/                  # ── ASYNC SQLALCHEMY (no Flask-SQLAlchemy) ─────────────
│   ├── base.py          # DeclarativeBase
│   ├── models.py        # User / SimulationScenario / GalleryScenario
│   └── session.py       # lazy async engine + async_sessionmaker + get_async_session
├── domain/              # ── PURE COMPUTE (0 import FastAPI) — the workers ──────
│   ├── election/        #   workers.py (35 workers) + _helpers.py + election_service.py
│   ├── simulations/     #   base/compare/advanced/whatif/campaign/helpers
│   ├── theory/          #   workers.py (15 theory workers) + __init__ aliases
│   ├── tech.py · public.py · export.py
├── engine/              # ── THE SIMULATION ENGINE (0 import FastAPI) ──────────
│   ├── constants.py     #   DEFAULT_ISSUES, ECONOMY/ENV/SOCIAL_ISSUES
│   └── utils/           #   simulation_metrics, *_ranked/score/multiwinner_utils,
│                        #   voting_utils, campaign_dynamics, blank_contagion, cache, …
├── routes/              # ── THIN HTTP ADAPTERS (validate → call worker → return) ─
│   ├── election.py theory.py simulations.py tech.py export.py
│   ├── public.py        #   /api/v1/* — public research API (slowapi rate limits)
│   ├── auth.py users.py oauth.py scenarios.py gallery.py health.py
├── schemas/             # Pydantic request/response contracts
├── sockets/             # python-socketio AsyncServer (Monte Carlo streaming)
└── tests/               # pytest + httpx TestClient + pytest-asyncio (aiosqlite)
```

**Layering rule**: `routes/` (HTTP) → `domain/` (workers, pure `(data:dict)->(body,status)`)
→ `engine/` (the 17 voting methods + metrics). `domain/` and `engine/` import neither
FastAPI nor the DB. DB-touching routes (auth/scenarios/gallery/oauth) use
`api.db` async sessions.

**URLs** (unchanged across the migration, so the frontend is untouched):
- `/api/v2/*` — the Election Lab + theory + simulations + scenarios + auth surface.
- `/api/v1/*` — the public research API (`api/routes/public.py`, OpenAPI 3.0).
- `/api/v2/socket.io` — Monte Carlo WebSocket stream.

### Backend — `/api/v2/election/*` endpoints

| Endpoint | Description |
|---|---|
| `POST /simulate` | Simulation unifiée (chaîne tous les modèles via ElectionService) |
| `POST /simulate-pipeline` | Pipeline step-by-step pour animation |
| `POST /interpret` | Interprétation textuelle déterministe |
| `POST /divergence` | Analyse blank vote avant/après |
| `POST /campaign-sensitivity` | Stabilité par méthode sous campagne |
| `POST /combined-effects` | Matrice 2³ factorielle |
| `POST /coalition` | D'Hondt + formation coalition greedy |
| `POST /districts` | N circonscriptions FPTP vs proportionnel |
| `POST /primary` | Primaires internes + élection générale |
| `POST /adaptive` | N rounds de vote tactique adaptatif |
| `POST /historical-replay` | Replay Brownien d'élection historique |
| `POST /jury` | Théorème du jury (courbe de compétence) |
| `POST /abstention` | Abstention différentielle (démobilisation) |
| `POST /stv` | STV + D'Hondt + FPTP (comparaison) |
| `POST /gerrymander` | Circonscriptions à frontières éditables |
| *(+ ~20 perturbers: nota, cascade, shy-voter, sortition, hotelling, …)* | |

### Backend — engine clés

```
api/engine/utils/
├── simulation_metrics.py         # compare_all_methods() — 17 méthodes
├── simulation_ranked_utils.py    # get_plurality_winner, get_irv_winner, get_schulze_winner,
│                                 # get_kemeny_young_winner (cap 6 + KwikSort fallback)
├── simulation_score_utils.py     # get_majority_judgment_winner (Balinski & Laraki 2010)
├── simulation_multiwinner_utils.py # get_stv_result (STV complet), get_dhondt_winners
├── simulation_voting_utils.py    # create_voter, create_candidate, calculate_utility
├── campaign_dynamics.py          # simulate_campaign (Brownian motion)
├── blank_contagion.py            # simulate_blank_contagion (SIS)
├── information_model.py          # apply_information_asymmetry
├── gibbard_satterthwaite.py      # indice de manipulabilité
└── cache.py                      # cache_result() — Redis memoisation (no-op without REDIS_URL)
```

### Méthodes de vote (17)

**Ranked (10)**: plurality, two_round, borda, approval, irv, coombs, bucklin, minimax, schulze, kemeny_young *(exact ≤6 candidats, KwikSort approximation >6)*

**Score (6)**: simple_score, star_voting, median_voting, mean_median_hybrid, variance_based, **majority_judgment** *(Balinski & Laraki 2010 — nouveau)*

**Spécial (1)**: quadratic

### Frontend — Composants shared notables

| Composant | Description |
|---|---|
| `DuelModePanel` | Comparaison côte à côte deux méthodes — badge winner + flip animation CSS |
| `AbstentionPanel` | Carte SVG voters abstentionnistes + LineChart turnout par camp |
| `STVPanel` | Stepper STV + 3 hémicycles comparaison |
| `GerrymanderMap` | Éditeur grille 10×10 + overlay voters + hémicycles |
| `HistoricalReplay` | 4 scénarios drag-and-drop + slider jour |
| `JuryTheoremPanel` | Courbe de compétence + BarChart précision |
| `PrimarySimulator` | Primaires internes + dérive idéologique |
| `AdaptiveVotingPanel` | Race chart rounds adaptatifs + overlay SVG |
| `CoalitionPanel` | Hémicycle SVG + formation coalition |
| `DistrictMap` | Grille SVG animée + dual hémicycles FPTP vs PR |
| `ElectionPipelineAnimator` | Animation step-by-step modèles |
| `MajorityJudgmentChart` | Barres empilées SVG + ligne médiane |

### Frontend — Composants Simulation notables

| Composant | Description |
|---|---|
| `IdeologyMapChart` | Carte 2D draggable + Voronoi + heatmap 30×30 + médian voter |
| `IdeologyHeatmap` | Grille SVG 900 cellules (Web Worker) + contours |
| `MedianVoterLayer` | Overlay SVG théorème de Black (pulsing cross) |
| `MethodSimilarityGraph` | D3 force-directed graph clusters méthodes |
| `MethodRaceBar` | Race bar SVG animé stabilité temps réel |
| `MonteCarloRaceChart` | Trajectoires win-rate + vue méthodes |
| `MajorityJudgmentChart` | Distribution notes MJ par candidat |
| `MetricsTab` | Métriques comparatives + modal graphe similarité |

### Web Worker

`src/workers/simulationWorker.ts` décharge les calculs lourds hors du thread principal :
- `COMPUTE_HEATMAP` → `computeGrid()` (30×30)
- `COMPUTE_MATRIX` → `partialResultsToMatrix()` (accord inter-méthodes)
- `SORT_MC_RESULTS` → `sortMethods()` (MethodRaceBar)

Hook : `useSimulationWorker()` → `dispatch(type, payload): Promise<Result>`

### Touch / Mobile

- `useDragTouch` — drag SVG unifié mouse+touch (IdeologyMapChart, HistoricalReplay)
- `useSwipe` — swipe horizontal pour navigation onglets mobile
- `MethodSimilarityGraph` — Pointer Events API (unifie mouse+touch+stylus)
- `DistrictMap` — cellules 48px + 5 cols max sur mobile < 768px

## Code style

- **TypeScript**: Prettier (`singleQuote: true`, `semi: true`, `printWidth: 100`, `tabWidth: 2`, `trailingComma: "es5"`) · ESLint `react-app`
- **Python**: flake8 · mypy strict sur `api/` (toujours vérifier avant commit)
- **Tests**: toujours ajouter des tests pour les nouveaux endpoints/composants · coverage ≥ 30 % backend

## Conventions importantes

- **Git**: branche `feat/*` → merge `--no-ff` dans `develop`. Jamais pousser directement sur `main`.
- **mypy**: vérifier `python -m mypy api/ --ignore-missing-imports` avant commit backend.
- **Nouveau endpoint backend**: 1) worker pur `(data:dict)->(body,status)` dans `api/domain/…`, 2) schéma Pydantic dans `api/schemas/`, 3) route fine dans `api/routes/…` (`_run_passthrough`), 4) test dans `api/tests/`. Garder `domain/`+`engine/` sans import FastAPI.
- **DB async**: les routes qui touchent la DB injectent `Depends(get_async_session)` (`api/db/session.py`) et utilisent `select()`/`AsyncSession` ; jamais de session synchrone.
- **Rate limiting**: `slowapi` (`@limiter.limit("10/minute")`) — uniquement sur la surface publique `/api/v1/*` ; une route décorée NE doit PAS avoir `from __future__ import annotations` (slowapi casse l'introspection du body Pydantic).
- **Fetch de données (frontend)**: un panel POST utilise `$api.useMutation('post', '/api/v2/.../slug')` (body typé par le schéma généré ; réponse castée vers l'interface manuelle tant qu'il n'y a pas de `response_model`). Effet de succès → 2ᵉ arg `{ onSuccess: (res) => …(res as unknown as T) }`. Les `services/*Api.ts` passent par `apiPost/apiGet/apiDelete` (`src/api/client.ts`) — pas d'axios, pas de `getAuthHeader()` (middleware).
- **Tests de panels migrés**: PAS de MSW. `jest.mock('../../../api/client')` (GET/POST/… = jest.fns) + rendre sous `<QueryClientProvider client={makeTestQueryClient()}>` (`src/test/queryWrapper.tsx`, retry:false) ; `apiClient.POST.mockResolvedValue({ data, error: undefined })`. Le body envoyé se lit `(apiClient.POST.mock.calls[0][1] as {body}).body`.
- **Stores Zustand**: les hooks sélectionnent les champs **un par un** (`useStore(s => s.x)`) — ne jamais retourner un objet composite frais depuis un seul sélecteur (casse le cache de snapshot). Les shims de provider appellent `store.hydrate()` au montage pour relire le localStorage.
- **Web Worker**: `import.meta.url` n'est pas supporté par Jest → mocker `useSimulationWorker` dans les tests.
- **Tests act()**: les mises à jour d'état async après `waitFor(mock.called)` doivent être suivies d'un `await act(async () => {})` pour éviter les warnings React.
- **Coverage**: le seuil de 30 % s'applique à toute la suite, pas aux fichiers isolés.
