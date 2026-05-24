# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Stack

- **Frontend**: React 19 + TypeScript · React Router v7 · Bootstrap 5 · Recharts · D3 7.x · axios · i18next (FR/EN) · Vite · PWA (vite-plugin-pwa)
- **Backend**: Flask 3.1 · SQLAlchemy 2.0 · PostgreSQL · Redis · eventlet (WebSocket)
- **Auth**: JWT (1h expiry) · bcrypt · OAuth (Google / GitHub)
- **Tests**: Jest 780+ frontend · pytest 985+ backend · coverage ≥ 30 % (backend)
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

```bash
# With Docker (full stack: Flask :4433, PostgreSQL :5432, Redis :6379)
docker-compose up --build
docker-compose exec backend pytest
docker-compose exec backend flake8

# Without Docker (SQLite in-memory, fast)
FLASK_ENV=testing python -m pytest tests/ -v
FLASK_ENV=testing python -m pytest tests/test_foo.py -v   # single file
python -m mypy app/utils/ app/routes/ --ignore-missing-imports
python -m flake8
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
├── context/
│   ├── ElectionContext.tsx       # Config globale élection (persistée localStorage)
│   ├── AuthContext.tsx
│   └── ThemeContext / ExpertModeContext / TeacherModeContext
├── hooks/
│   ├── useDragTouch.ts           # Drag SVG unifié mouse+touch
│   ├── useSwipe.ts               # Swipe mobile pour navigation onglets
│   ├── useMonteCarloStream.ts    # WebSocket streaming Monte Carlo
│   ├── useSimulationWorker.ts    # Web Worker hook (heatmap, matrix)
│   └── useDebouncedSimulation.ts
├── workers/
│   └── simulationWorker.ts       # Web Worker: computeGrid, partialResultsToMatrix
├── services/                     # axios wrappers → http://localhost:4433
│   ├── electionApi.ts            # ElectionResult, simulateElection
│   └── simulationCompareApi.ts
└── utils/
    └── voronoiRegions.ts         # d3-delaunay Voronoi path builder
```

### Frontend — ElectionContext

`ElectionContext` est la source de vérité globale. Il contient :
- `config` : candidates (x,y), num_voters, ideology, seed, campaign, blank_vote, information_model
- `setConfig / setConfigDeep` : mutations partielles
- `scenarioMeta` : metadata du scénario chargé (France 2002, etc.)
- `SCENARIOS` : configs prédéfinies pour 7 scénarios historiques

### Frontend — ElectionLabPage (hub)

Navigation adaptative :
- **Mobile < 768px** : `Form.Select` + boutons ‹ › (détecté via `MediaQueryList`)
- **Desktop** : Bootstrap `Tabs` contrôlés via `activeTab` state

Onglets actuels (20) :
`results` · `map` · `animation` · `montecarlo` · `manipulability` · `blank-divergence` · `campaign-sensitivity` · `pipeline` · `combined-effects` · `coalition` · `districts` · `primary` · `replay` · `jury` · `adaptive` · `abstention` · `stv` · `gerrymander` · (+ autres à venir)

### Backend — Blueprints

```
app/routes/
├── election/            # Election Lab — package (B3 du sprint perf)
├── simulation_compare.py
├── simulation_advanced.py
├── simulation_base.py
├── export.py
├── gallery.py
├── api_public.py        # API publique v1 (OpenAPI 3.0)
├── health.py            # /api/health (DB + Redis status)
└── users.py / auth
```

### Backend — FastAPI sibling (Phase 2 du refactor stratégique)

Démarré en parallèle de Flask, expose `/api/v2/*` (Flask reste sur `/api/*`).
Stratégie strangler-fig : chaque endpoint migre une fois, l'ancien est supprimé.

```
api_v2/
├── main.py              # FastAPI app + CORS + lifespan + middleware access log
├── core/
│   └── config.py        # Pydantic Settings (12-factor)
├── domain/
│   └── election/        # Pure compute, 0 import Flask/FastAPI
├── routes/
│   ├── election.py      # /api/v2/election/* (1 endpoint pour Phase 2)
│   └── health.py        # /api/v2/health
└── tests/               # 18 tests pytest + FastAPI TestClient
```

Lancer :
```bash
cd flask_voter_app
uvicorn api_v2.main:app --reload --port 4434
# OU via docker-compose : le service `api_v2` boote tout seul
```

Tester :
```bash
curl http://localhost:4434/api/v2/health
open http://localhost:4434/api/v2/docs   # Swagger UI auto-généré
```

### Backend — election.py endpoints

Tous sous `/api/election/` :

| Endpoint | Description |
|---|---|
| `POST /simulate` | Simulation unifiée (tpool + eventlet timeout 120s) |
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

### Backend — utils clés

```
app/utils/
├── simulation_metrics.py         # compare_all_methods() — 17 méthodes
├── simulation_ranked_utils.py    # get_plurality_winner, get_irv_winner, get_schulze_winner,
│                                 # get_kemeny_young_winner (cap 6 + KwikSort fallback)
├── simulation_score_utils.py     # get_majority_judgment_winner (Balinski & Laraki 2010)
├── simulation_multiwinner_utils.py # get_stv_result (STV complet), get_dhondt_winners
├── simulation_voting_utils.py    # create_voter, create_candidate, calculate_utility
├── campaign_dynamics.py          # simulate_campaign (Brownian motion)
├── blank_contagion.py            # simulate_blank_contagion (SIS)
├── information_model.py          # apply_information_asymmetry
└── gibbard_satterthwaite.py      # indice de manipulabilité
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
- **Python**: flake8 · mypy strict sur `app/utils/` et `app/routes/` (toujours vérifier avant commit)
- **Tests**: toujours ajouter des tests pour les nouveaux endpoints/composants · coverage ≥ 30 % backend

## Conventions importantes

- **Git**: branche `feat/*` → merge `--no-ff` dans `develop`. Jamais pousser directement sur `main`.
- **mypy**: vérifier `python -m mypy app/routes/election.py --ignore-missing-imports` avant commit backend.
- **Web Worker**: `import.meta.url` n'est pas supporté par Jest → mocker `useSimulationWorker` dans les tests.
- **Tests act()**: les mises à jour d'état async après `waitFor(mock.called)` doivent être suivies d'un `await act(async () => {})` pour éviter les warnings React.
- **Coverage**: le seuil de 30 % s'applique à toute la suite, pas aux fichiers isolés.
- **Rate limiting**: `@sim_limiter.limit("10 per minute")` sur tous les nouveaux endpoints lourds.
- **eventlet**: `socketio.sleep(0)` obligatoire après chaque `emit()` en boucle ; `eventlet.monkey_patch()` doit être la toute première ligne de `run.py`.
