# Vote Lab

A civic research sandbox for voting theory — demonstrating empirically that **the choice of voting method changes the winner**, and exploring what happens when campaign dynamics, blank votes, information asymmetry, and social contagion all act on the same electorate.

---

## What it does

Vote Lab lets you configure a complete election and observe it through multiple lenses simultaneously:

- Run elections with **16 voting methods** on the same population and compare who wins
- Animate **step-by-step ballot counting** (IRV elimination rounds, Borda accumulation, Schulze matrix)
- **Drag candidates** on an interactive 2D ideological map and watch which voter zones shift in real time
- **Animate the full election pipeline** — watch each model (campaign, contagion, information) transform voter preferences before the final count
- Stream **Monte Carlo simulations** with live convergence charts as 1 000+ elections run
- Study **combined effects** (blank vote × campaign × media bias) with a 2³ factorial matrix
- Compare methods on **5 quality axes** simultaneously with a radar chart
- Explore **5 historical elections** (France 2002, USA 1992, Germany 2021…) pre-configured as research scenarios

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (uvicorn) · SQLAlchemy 2.0 async · PostgreSQL · Redis |
| WebSockets | python-socketio (ASGI, Monte Carlo streaming) |
| Auth | JWT + bcrypt + OAuth (Google / GitHub) |
| Frontend | React 19 · TypeScript · React Router v7 · Vite |
| UI | Bootstrap 5 · react-bootstrap |
| Charts | Recharts · D3 (Voronoi, hexbin) |
| i18n | i18next (FR / EN toggle, persisted) |
| PWA | vite-plugin-pwa · Workbox (offline, installable) |
| Tests | Jest (unit) · Playwright (E2E + axe-core a11y) |
| Type checking | mypy strict on `api/` |
| CI/CD | GitHub Actions (path-based triggers for backend and frontend) |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)
- [Node.js](https://nodejs.org/) 20+

### 1. Clone & configure

```bash
git clone https://github.com/Burbanit0/Vote-App.git
cd Vote-App
cp flask_voter_app/.env.example flask_voter_app/.env   # default values work locally
```

### 2. Start the backend

```bash
cd flask_voter_app
docker-compose up --build
```

| Service | URL |
|---|---|
| FastAPI + WebSocket | http://localhost:4434 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Start the frontend

```bash
cd voter-app
npm install
npm start      # Vite dev server → http://localhost:3000
```

---

## Development

### Backend

```bash
# Run tests (SQLite in-memory, no Docker needed)
cd flask_voter_app
FLASK_ENV=testing python -m pytest api/tests -v

# Type checking
python -m mypy api/ --ignore-missing-imports

# Lint
flake8

# With Docker
docker-compose exec api pytest
docker-compose exec api flake8
```

### Frontend

```bash
cd voter-app
npm test                 # Jest (641 tests)
npm run test:e2e         # Playwright (Chromium + Firefox)
npm run test:a11y        # axe-core WCAG 2.1 AA audit
npm run build            # production build (includes PWA manifest + service worker)
npm run lint
```

---

## Application Structure

### Pages & Routes

| Route | Description |
|---|---|
| `/` | Home — QuickCompare widget (choose a scenario, compare 2 methods instantly) |
| `/election-lab` | **Election Lab** — unified hub combining all models on one election |
| `/simulation/compare` | Method comparison sandbox (14 tabs, radar chart, streaming Monte Carlo) |
| `/scenario-builder` | 4-step election wizard |
| `/constitutional-crisis` | Blank vote crisis simulator |
| `/quiz` | Pedagogical quiz — 20 questions, 3 difficulty levels |
| `/what-if` | Single-parameter "Et si…" variation analysis |
| `/campaign` | Day-by-day campaign dynamics (Brownian motion) |
| `/blank-contagion` | SIS social contagion model for blank votes |
| `/regimes-internationaux` | Comparative international blank-vote law |
| `/galerie` | Community scenario gallery |
| `/api-docs` | Public API documentation |

---

## Election Lab — Unified Hub (`/election-lab`)

The central tool. Configure one election and explore all dimensions in a single interface.

**Parameters (left panel):**
- Candidates with explicit (x, y) ideological positions
- Electorate size, ideology distribution, seed
- Campaign dynamics (Brownian motion, polling effect, duration)
- Blank vote (symbolic / competitive / threshold-30 rule)
- Social contagion (SIS model — β, γ, network topology)
- Media information model (media bias per candidate, voter segments)

**Result tabs (right panel):**

| Tab | Visualisation |
|---|---|
| 📊 Résultats | Winners per method · `ElectionInsightPanel` (auto-generated analysis) · `HistoricalReferencePanel` (vs real election) |
| 🗺 Carte idéologique | 2D scatter of voters — drag candidates, Voronoi win-zone overlay, hover tooltips |
| 🎬 Pipeline | Step-by-step animation of each model transforming the electorate |
| ▶ Animation | Ballot-counting animation (IRV rounds, Borda accumulation, Schulze matrix…) |
| 🎲 Monte Carlo | Streaming robustness analysis across 1 000+ elections |
| ⚡ Manipulabilité | Gibbard-Satterthwaite index per method |
| 📊 Vote blanc | Before/after divergence: does blank vote increase method disagreement? |
| 📈 Campagne | Swimlane chart — which method elects who at each campaign stage |
| 🔬 Effets combinés | 2³ factorial matrix (blank × campaign × media) |

**Pre-loaded historical scenarios:** France 2002 (Condorcet paradox), USA 1992 (spoiler effect), Germany 2021 (fragmentation), Condorcet cycle, Consensus.

---

## Simulation Sandbox (`/simulation/compare`)

14 tabs, debounced live results (updates 600 ms after any parameter change):

| Tab | Content |
|---|---|
| Matrice des vainqueurs | Winner per method + animated drill-down |
| 🗺 Carte idéologique | Draggable 2D ideology map with Voronoi zones |
| ▶ Animation | Step-by-step ballot counting |
| 🕸 Radar | Spider chart — 5 quality axes per method (equity, satisfaction, resistance, Condorcet, stability) |
| Métriques | Bayesian Regret, Majority Satisfaction, Strategic Vulnerability |
| Impact stratégique | Regret vs % strategic voters |
| Matrice de Condorcet | N×N pairwise duel heatmap |
| Critères d'Arrow | IIA, unanimity, non-dictatorship |
| Effet bandwagon | Social influence cascades |
| Monte Carlo | Live streaming — race chart + convergence panels |
| Élections réelles | Historical elections analysis |
| Multi-gagnants | Proportional seat allocation |
| Sensibilité | Vary one parameter, observe winner changes |
| Manipulabilité | Gibbard-Satterthwaite vulnerability |

---

## Visualisations

### Interactive Ideology Map
SVG canvas (480×480) with 200 voter dots. Candidates are **draggable** — after each drop a new election is computed (150 ms debounce). Toggle **Voronoi win-zone overlay** to see which candidate "owns" each ideological territory in real time.

### Pipeline Animator
Animated step-by-step pipeline — 2 to 5 stages depending on active models. Each voter dot **transitions colour** (CSS `fill 0.6s ease`) as the campaign, contagion, or media model shifts their preferences. Blank voters fade to grey.

### Monte Carlo Race Chart
Live `AreaChart` during streaming Monte Carlo. Shows the **win-rate trajectory** of each candidate at every 50-iteration checkpoint — like a statistical horse race.

### Campaign Swimlane
Replaces the bar chart with an **SVG swimlane** sorted by stability. Each row = one method, each segment = the candidate elected at that campaign stage. Click any segment to highlight that candidate across all methods.

### Radar Chart
Recharts `RadarChart` comparing all methods on 5 normalised axes. Auto-selects the top 5 by global score. Badge indicates the "best overall method" (highest mean normalised score).

### Method Group Donut
`PieChart` in `ElectionInsightPanel` showing how methods split between winning candidates. Click a sector to expand the full method list. Single-group case shows a full circle with ✓ centre.

---

## Voting Methods (16)

**Ranked (11):** Plurality, Two-Round, Borda, Approval, IRV, Coombs, Bucklin, Minimax, Schulze, Kemeny-Young, Positional Score

**Score (5):** Simple Score, STAR Voting, Median Voting, Mean-Median Hybrid, Variance-Based

**Experimental (1):** Quadratic Voting (budget allocation per voter)

---

## Blank Vote Rules

| Rule | Effect |
|---|---|
| `symbolic` | Counted but never affects outcome |
| `competitive` | Blank is a full candidate — can win the election |
| `threshold_30` | Election invalidated if blank > 30 % |

---

## Public API (`/api/v1/`)

Rate-limited (60 req/min). No authentication needed.

```
GET  /api/v1/methods           # list of all 16 methods with descriptions
POST /api/election/simulate    # full unified simulation
POST /api/election/interpret   # auto-generated text interpretation of results
POST /api/election/divergence  # blank vote divergence analysis
POST /api/election/campaign-sensitivity  # campaign sensitivity by method
POST /api/election/combined-effects      # 2³ factorial analysis
POST /api/election/simulate-pipeline     # step-by-step pipeline snapshots
POST /api/export/simulation-dataset      # CSV dataset (up to 1 000 scenarios)
POST /api/export/simulation-dataset-json # JSON export
GET  /api/openapi.json         # OpenAPI 3.0 spec
```

---

## Architecture

```
flask_voter_app/api/        # FastAPI backend (Flask retired in Phase 4.5.b)
├── main.py                 # FastAPI app + CORS + slowapi + Socket.IO ASGI wrap
├── routes/                 # thin HTTP adapters (validate → worker → return)
│   ├── election.py theory.py simulations.py tech.py export.py gallery.py
│   ├── public.py           # /api/v1/* public research API + OpenAPI spec
│   └── auth.py users.py oauth.py scenarios.py health.py
├── domain/                 # pure compute workers (0 import FastAPI)
│   ├── election/           #   workers.py + _helpers.py + election_service.py
│   ├── simulations/ theory/ tech.py public.py export.py
├── engine/                 # the simulation engine (0 import FastAPI)
│   ├── constants.py
│   └── utils/
│       ├── simulation_voting_utils.py    # voter/candidate generation
│       ├── simulation_ranked_utils.py    # 11 ranked algorithms
│       ├── simulation_score_utils.py     # 5 score algorithms
│       ├── simulation_metrics.py         # compare_all_methods()
│       ├── campaign_dynamics.py          # Brownian motion campaign model
│       ├── blank_contagion.py            # SIS epidemic model
│       ├── information_model.py          # Media bias distortion
│       ├── gibbard_satterthwaite.py      # Manipulability index
│       └── quadratic_voting.py           # QV budget allocation
├── db/                     # async SQLAlchemy (models, session, base)
├── core/                   # config, auth, fastapi-users, ratelimit
├── schemas/  sockets/  tests/

voter-app/src/
├── pages/
│   ├── ElectionLabPage.tsx          # Unified hub
│   ├── SimulationComparePage.tsx    # 14-tab sandbox
│   └── HomePage.tsx                 # QuickCompare onboarding widget
├── components/shared/
│   ├── ElectionPipelineAnimator.tsx # Step-by-step pipeline animation
│   ├── ElectionInsightPanel.tsx     # Auto-generated analysis text
│   ├── MethodGroupDonut.tsx         # Winner distribution donut chart
│   ├── CampaignSwimlane.tsx         # SVG swimlane timeline
│   ├── BlankVoteDivergencePanel.tsx # Before/after blank vote comparison
│   ├── CampaignSensitivityPanel.tsx # Method stability under campaign
│   ├── CombinedEffectsMatrix.tsx    # 2³ factorial heatmap
│   ├── MetricTooltip.tsx            # Contextual metric explanations
│   └── QuickCompareWidget.tsx       # Home page interactive widget
├── components/Simulation/
│   ├── IdeologyMapChart.tsx         # Draggable 2D map + Voronoi overlay
│   ├── MethodRadarChart.tsx         # 5-axis spider chart
│   ├── MonteCarloRaceChart.tsx      # Live win-rate trajectories
│   ├── MonteCarloConvergencePanel.tsx # Regret + agreement + CI charts
│   ├── VoteStepAnimator.tsx         # Ballot-counting animation
│   └── CampaignSwimlane.tsx
├── context/
│   ├── ElectionContext.tsx          # Global election config (persisted)
│   └── AuthContext / ThemeContext / ExpertModeContext / TeacherModeContext
└── utils/
    └── voronoiRegions.ts            # d3-delaunay Voronoi path builder
```

---

## Branch Strategy

```
main       ← stable releases (CI/CD via Release workflow)
develop    ← integration branch
feat/xxx   ← one branch per feature → PR to develop
```

---

## Code Style

- **Python:** flake8 + mypy strict on `api/`
- **TypeScript:** Prettier (`singleQuote`, `semi`, `printWidth: 100`) + ESLint with `jsx-a11y`
- **Tests:** Jest ≥ 641 frontend · pytest ≥ 825 backend · coverage ≥ 30 %
