# Vote Lab

A research sandbox for voting theory — demonstrating empirically that the choice of voting method changes the winner, and exploring the constitutional role of the blank vote.

---

## Research Goal

- Run simulated elections with demographically realistic voters and observe how different voting methods elect different winners from the **same population**
- Measure **Bayesian Regret**, **majority satisfaction**, and **strategic vulnerability** per method
- Model **sincere vs. strategic voters** and visualise how tactical voting degrades certain methods
- Detect **Condorcet cycles** and **IIA violations** (spoiler effect)
- Simulate **blank vote rules** (symbolic, competitive, threshold 30%, majority required) and their constitutional impact

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.1 + SQLAlchemy 2.0 + PostgreSQL + Redis |
| Auth | JWT (Bearer tokens, 1 h expiry) + bcrypt |
| Frontend | React 19 + TypeScript + React Router v7 + Vite |
| UI | Bootstrap 5 + react-bootstrap |
| Charts | Recharts + Chart.js |
| CI/CD | GitHub Actions (path-based triggers) |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Node.js](https://nodejs.org/) 20+
- [Python](https://www.python.org/) 3.11+

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Burbanit0/Vote-App.git
cd Vote-App
```

### 2. Configure the backend environment

```bash
cp flask_voter_app/.env.example flask_voter_app/.env
```

The default values work for local development out of the box. For production, replace `SECRET_KEY` and `JWT_SECRET_KEY` with strong random values:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the backend (Flask + PostgreSQL + Redis)

```bash
cd flask_voter_app
docker-compose up --build
```

Services started:

| Service | URL |
|---|---|
| Flask API | http://localhost:4433 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

On first run, Docker will apply database migrations automatically via the entrypoint.

### 4. Start the frontend

In a separate terminal:

```bash
cd voter-app
npm install
npm start
```

Frontend available at **http://localhost:3000**.

---

## Development Commands

### Backend

```bash
# Start all services
docker-compose up --build

# Run tests
docker-compose exec web pytest
docker-compose exec web pytest tests/test_simulation.py   # single file

# Lint
docker-compose exec web flake8

# Run tests without Docker (SQLite in-memory)
cd flask_voter_app
FLASK_ENV=testing JWT_SECRET_KEY=test python -m pytest tests -v

# Database migrations
docker-compose exec web flask db migrate -m "description"
docker-compose exec web flask db upgrade
```

### Frontend

```bash
cd voter-app

npm start                                        # dev server on :3000 (Vite)
npm test                                         # Jest (jsdom)
npm run build                                    # production build (tsc + vite build)
npm run preview                                  # preview the production build
npm run lint                                     # ESLint
npm run prettier-format                          # Prettier
npx jest src/path/to/file.test.tsx               # single test file
```

---

## Local Setup for Contributors (one-time)

### Git hooks (required)

```bash
pip install pre-commit
pre-commit install                          # pre-commit hooks
pre-commit install --hook-type pre-push     # pre-push hooks (tests + coverage)
```

Hooks run automatically on `git commit` (secrets scan, bandit, flake8, eslint, npm audit) and `git push` (frontend + backend tests with coverage ≥ 30%).

### Python dev tools

```bash
pip install -r flask_voter_app/requirements-dev.txt
```

### Branch strategy

All changes must go through a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full branch policy.

```
main         ← official releases only (via Release workflow)
develop      ← integration branch
feature/xxx  ← one branch per feature/fix, merged into develop
```

---

## Architecture

### Backend

```
flask_voter_app/app/
├── models.py                        # SQLAlchemy ORM (User, SimulationScenario)
├── config.py                        # Dev / Testing / Production configs (env-based)
├── routes/
│   ├── users.py                     # /api/auth/ — register, login, profile
│   ├── scenarios.py                 # /api/scenarios/ — save/load simulation scenarios
│   ├── simulation_base.py           # /simulations/ — core simulation entry points
│   ├── simulation_compare.py        # /simulations/compare, /strategic-impact, /condorcet-matrix,
│   │                                #   /sensitivity, /arrow-criteria, /scenario, /constitutional-scenario
│   ├── simulation_advanced.py       # /simulations/bandwagon, /monte-carlo, /multiwinner,
│   │                                #   /real-elections, /blank-contagion
│   └── simulation_helpers.py        # shared helpers
├── services/                        # Business logic
└── utils/
    ├── simulation_voting_utils.py   # Voter/candidate generation, utility model, strategic voting
    ├── simulation_ranked_utils.py   # 12 ranked voting algorithms
    ├── simulation_score_utils.py    # Score voting algorithms
    ├── simulation_metrics.py        # compare_all_methods(), get_condorcet_matrix()
    ├── blank_vote_rules.py          # BlankVoteRule enum + apply_blank_rule()
    └── real_election_data.py        # Historical election data with blank vote rates
```

### Frontend

```
voter-app/src/
├── pages/
│   ├── HomePage.tsx                 # Landing page + onboarding tour
│   ├── SimulationComparePage.tsx    # Main sandbox (10 tabs)
│   ├── ScenarioBuilderPage.tsx      # 4-step wizard (candidates → electorate → blank rule → results)
│   ├── ConstitutionalCrisisPage.tsx # Blank vote crisis simulator
│   └── SimulationPage.tsx          # Single-method simulation
├── components/
│   ├── Simulation/                  # IdeologicalSpaceChart, CondorcetMatrix, …
│   └── shared/                      # MethodTooltip, ResponsiveTable, SkeletonCard,
│                                    #   ToastNotification, OnboardingTour, EmptyChart
├── context/
│   ├── AuthContext.tsx              # JWT auth state
│   ├── ThemeContext.tsx             # Dark / light mode
│   └── ExpertModeContext.tsx        # Beginner / expert display mode
├── hooks/
│   ├── useChartTheme.ts             # Chart colour palettes for dark mode
│   └── useMetaTags.ts              # Dynamic OG / Twitter meta tags
└── services/                        # axios wrappers pointing to http://localhost:4433
```

---

## Simulation System

### Voter generation

Each voter has realistic demographics (French age distribution, income via gamma distribution, education correlated with age):

- **Socio-demographic:** `age`, `gender`, `region`, `income`, `education`, `employment_status`, `religion`
- **Ideological:** `political_lean_normalized` [0=progressive, 1=conservative], `issue_positions` (20 policy issues)
- **Behavioural:** `party_loyalty`, `likelihood_to_vote`, `strategic_propensity`, `voting_style` (`sincere` | `strategic`)
- **Ideology distributions:** `random`, `centrist`, `polarized`, `left_skewed`, `right_skewed`

### Utility model (spatial voting)

```
utility(voter, candidate) =
  0.60 × Σ issue_priorities[i] × (1 − |voter_position[i] − candidate_policy[i]|)
+ 0.20 × party_loyalty_bonus
+ 0.15 × charisma_effect
− scandal_penalty
```

### Strategic voting

| Method category | Strategy |
|---|---|
| Plurality | Duverger — switch to best viable top-2 candidate |
| Borda | Burial — rank the poll leader last |
| IRV / Condorcet / Schulze | Compromise — promote best viable candidate to first |
| Approval | Bullet vote — approve only the top candidate unless 2nd is within 10% |
| Score / STAR | Exaggeration — max to preferred, 0 to main threat |

### Voting methods (15)

**Ranked:** Plurality, Two-Round, Borda, Approval, IRV, Coombs, Bucklin, Minimax, Schulze, Kemeny-Young, Positional Score, Condorcet

**Score:** Simple Score, STAR Voting, Median Voting, Mean-Median Hybrid, Variance-Based

### Blank vote rules

| Rule | Effect |
|---|---|
| `SYMBOLIC` | Counted separately, never affects the result |
| `COMPETITIVE` | Blank vote acts as a candidate — can win |
| `THRESHOLD_30` | If blank > 30%, the election is invalidated |
| `MAJORITY_REQUIRED` | Winner needs absolute majority; blank counts toward the total |

---

## API Reference

### Auth — `/api/auth/`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Register a new user |
| POST | `/login` | Login (returns JWT) |
| GET | `/profile` | Current user profile (JWT required) |

### Scenarios — `/api/scenarios/`

All routes require JWT (`Authorization: Bearer <token>`).

| Method | Path | Description |
|---|---|---|
| GET | `/` | List saved scenarios |
| POST | `/` | Save a scenario |
| GET | `/<id>` | Load a scenario |
| DELETE | `/<id>` | Delete a scenario |

### Simulation — `/simulations/`

No authentication required.

| Method | Path | Description |
|---|---|---|
| POST | `/compare` | Compare all 15 methods on one population |
| POST | `/strategic-impact` | Bayesian regret vs. % strategic voters |
| POST | `/condorcet-matrix` | Full N×N pairwise duel matrix |
| POST | `/sensitivity` | Vary one parameter, observe winner changes |
| POST | `/arrow-criteria` | Test Arrow's impossibility criteria per method |
| POST | `/scenario` | Run a named scenario (ScenarioBuilder) |
| POST | `/constitutional-scenario` | Blank vote crisis simulation |
| POST | `/bandwagon` | Bandwagon / underdog effect simulation |
| POST | `/monte-carlo` | Monte Carlo robustness analysis |
| POST | `/multiwinner` | Multi-winner election (proportional methods) |
| GET  | `/real-elections` | Historical election data |
| GET  | `/real-elections/<id>` | Single election detail with blank vote analysis |

**`/compare` example body:**

```json
{
  "num_voters": 1000,
  "ideology_distribution": "polarized",
  "blank_rule": "THRESHOLD_30",
  "candidates": [
    {"name": "Alice", "ideology_position": 0.25},
    {"name": "Bob",   "ideology_position": 0.75},
    {"name": "Carol", "ideology_position": 0.5}
  ]
}
```

---

## Simulation Sandbox (frontend)

Navigate to `/simulation` — no login required.

| Tab | Description |
|---|---|
| **Résultats** | Winner per method + scores. Click any cell for method explanation. |
| **Métriques** | Bayesian Regret, Majority Satisfaction, Strategic Vulnerability averaged across runs. |
| **Impact stratégique** | How Bayesian Regret evolves as the % of strategic voters increases (0–50%). |
| **Matrice de Condorcet** | N×N pairwise duel heatmap. Highlights Condorcet cycles. |
| **Sensibilité** | Vary one parameter (ideology / num voters / strategic %) across methods. |
| **Vote blanc** | Blank vote rate and constitutional rule impact. |
| **Critères d'Arrow** | Which methods satisfy Pareto, IIA, non-dictatorship, Condorcet. |
| **Monte Carlo** | Robustness analysis across 1 000+ random populations. |
| **Multi-gagnant** | Proportional / semi-proportional methods for multi-seat elections. |
| **Élections réelles** | Historical French election data with blank vote rates. |

**UX features:**
- **Dark mode** — toggle via navbar
- **Mode Débutant / Expert** — hides advanced tabs and terminology for newcomers
- **Tooltips pédagogiques** — hover any method name for origin, strengths, weaknesses
- **Partager** — generates a URL encoding the current configuration
- **Export PDF** — full simulation report
- **Présentation** — fullscreen mode for teaching

---

## Reset the database

```bash
cd flask_voter_app
docker-compose down -v          # removes containers AND the postgres volume
docker-compose up --build       # recreates and migrates automatically
```

---

## Code Style

- **Python:** flake8 (config in `flask_voter_app/.flake8`), bandit for SAST
- **TypeScript:** Prettier (`singleQuote`, `semi`, `printWidth: 100`, `tabWidth: 2`) + ESLint `react-app`
