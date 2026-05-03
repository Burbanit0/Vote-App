# Vote-App

A research sandbox for voting theory — demonstrating empirically that the choice of voting method changes the winner, and identifying methods that best resist strategic manipulation.

---

## Research Goal

This project allows you to:
- Run simulated elections with demographically realistic voters and observe how different voting methods elect different winners from the **same population**
- Measure **Bayesian Regret**, **majority satisfaction**, and **strategic vulnerability** per method
- Model **sincere vs. strategic voters** and visualise how tactical voting degrades certain methods
- Detect **Condorcet cycles** and **IIA violations** (spoiler effect)
- Compare scenarios side-by-side (e.g. adding a centrist candidate)

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.1 + SQLAlchemy 2.0 + PostgreSQL + Redis |
| Auth | JWT (Bearer tokens, 1 h expiry) + bcrypt |
| Background jobs | APScheduler |
| Frontend | React 19 + TypeScript + React Router v7 |
| UI | Bootstrap 5 + react-bootstrap |
| Charts | Recharts + Chart.js |
| CI/CD | GitHub Actions (path-based triggers) |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Node.js](https://nodejs.org/) 18+

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Burbanit0/Vote-App.git
cd Vote-App
```

### 2. Start the backend (Flask + PostgreSQL + Redis)

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

### 3. Seed the database

On first run, populate the database with demo users, parties and elections:

```bash
docker-compose exec web python seed.py
```

Default accounts created:

| Username | Password | Role |
|---|---|---|
| `admin` | `adminpassword` | Admin |
| `user1` … `user10` | `password1` … `password10` | User |

### 4. Start the frontend

In a separate terminal:

```bash
cd voter-app
npm install
npm start
```

Frontend available at http://localhost:3000.

---

## Reset the database

To wipe all data and start fresh:

```bash
cd flask_voter_app
docker-compose down -v          # removes containers AND the postgres volume
docker-compose up --build
docker-compose exec web python seed.py
```

---

## Development Commands

### Backend

```bash
docker-compose up --build                           # start all services
docker-compose exec web pytest                      # run all tests
docker-compose exec web pytest tests/test_votes.py  # single test file
docker-compose exec web flake8                      # lint
flask db migrate -m "description"                   # create migration
flask db upgrade                                    # apply migrations
```

### Frontend

```bash
npm start                  # dev server on :3000
npm test                   # Jest (jsdom environment)
npm run build              # production build
npm run lint               # ESLint
npm run prettier-format    # Prettier
npx jest src/path/to/file.test.tsx   # single test
```

---

## Architecture

### Backend

```
flask_voter_app/app/
├── models.py                      # SQLAlchemy ORM (User, Election, Vote, SimulationScenario, …)
├── config.py                      # Development / Testing / Production configs
├── routes/
│   ├── users.py                   # /api/auth/ — register, login, profile, permissions
│   ├── elections.py               # /api/elections/ — CRUD, participants
│   ├── votes.py                   # /api/votes/ — cast votes, results
│   ├── parties.py                 # /api/parties/ — party management
│   ├── simulation.py              # /simulations/ — simulation engine endpoints
│   └── scenarios.py               # /api/scenarios/ — save/load simulation scenarios
├── services/                      # Business logic (election, vote, party, user, participation)
└── utils/
    ├── simulation_voting_utils.py  # Voter/candidate generation, utility model, strategic voting
    ├── simulation_ranked_utils.py  # 12 ranked voting algorithms
    ├── simulation_score_utils.py   # 7 score voting algorithms
    └── simulation_metrics.py       # compare_all_methods(), get_condorcet_matrix()
```

### Frontend

```
voter-app/src/
├── pages/
│   └── SimulationComparePage.tsx  # Main simulation sandbox (5 tabs)
├── components/Simulation/
│   ├── IdeologicalSpaceChart.tsx  # 2D voter/candidate scatter plot
│   └── CondorcetMatrix.tsx        # Pairwise duel heatmap
├── services/
│   ├── simulationCompareApi.ts    # /simulations/* API calls
│   └── scenariosApi.ts            # /api/scenarios/* API calls
└── types.ts                       # TypeScript interfaces
```

### Data model

The key junction table `user_election_roles` links users to elections with a `role` field (`voter` / `candidate` / `organizer`) and tracks whether the user has voted.

`SimulationScenario` stores saved sandbox configurations and results per user.

---

## Simulation System

### Voter generation

Each voter is generated with realistic demographics (French age distribution, income via gamma distribution, education correlated with age). Attributes include:

- Socio-demographic: `age`, `gender`, `region`, `income`, `education`, `employment_status`, `family_status`, `religion`, `ethnicity_immigration`
- Ideological: `political_lean_normalized` [0=progressive, 1=conservative], `issue_positions` (per-issue position on 20 policy issues)
- Behavioural: `party_loyalty`, `likelihood_to_vote`, `strategic_propensity`, `voting_style` (`sincere` | `strategic`)

**Ideology distributions** (controllable): `random`, `centrist`, `polarized`, `left_skewed`, `right_skewed`

### Candidate generation

Candidates have `ideology_position` [0,1] either derived from their party or set explicitly. Policies are generated around that position with configurable variance.

### Utility model (spatial voting)

```
utility(voter, candidate) =
  0.60 × Σ issue_priorities[i] × (1 − |voter_position[i] − candidate_policy[i]|)
+ 0.20 × party_loyalty_bonus
+ 0.15 × charisma_effect
− scandal_penalty
+ mood_effect
```

### Strategic voting

Five strategy implementations, dispatched by method:

| Method category | Strategy |
|---|---|
| Plurality | Duverger / vote utile — switch to best viable top-2 candidate |
| Borda | Burial — rank the poll leader last |
| IRV / Condorcet / Schulze / … | Compromise — promote best viable candidate to first |
| Approval | Bullet vote — approve only the top candidate unless 2nd is within 10% |
| Score / STAR | Exaggeration — 5 to preferred, 0 to main threat, proportional for others |

### Voting methods

**Ranked (12):** Plurality, Two-Round, Borda, Approval, IRV, Coombs, Bucklin, Minimax, Schulze, Kemeny-Young, Positional Score, Condorcet

**Score (7):** Simple Score, STAR Voting, Median Voting, Mean-Median Hybrid, Variance-Based, Score Distribution Analysis, Bayesian Regret

---

## API Endpoints

### Auth — `/api/auth/`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Register a new user |
| POST | `/login` | Login (returns JWT) |
| GET | `/profile` | Current user profile |
| GET | `/users/me/permissions` | Check permissions |

### Elections — `/api/elections/`

| Method | Path | Description |
|---|---|---|
| GET/POST | `/` | List / create elections |
| GET | `/<id>` | Election detail |
| GET/POST | `/<id>/participants` | Manage participants |

### Votes — `/api/votes/`

| Method | Path | Description |
|---|---|---|
| GET/POST | `/` | List / cast votes |
| GET | `/<id>/results` | Vote results |

### Simulation — `/simulations/`

| Method | Path | Description |
|---|---|---|
| POST | `/` | Run a full simulation (votes / ranked / scores) |
| POST | `/simulate_voters` | Generate a voter population |
| POST | `/simulate_candidates` | Generate candidates |
| POST | `/simulate_utility` | Compute voter-candidate utilities |
| POST | `/compare` | Compare all methods on one population |
| POST | `/strategic-impact` | Bayesian regret vs. strategic voter % |
| POST | `/condorcet-matrix` | Full pairwise duel matrix |
| POST | `/sensitivity` | Vary one parameter, observe winner changes |

**`/compare` body:**
```json
{
  "num_voters": 500,
  "ideology_distribution": "polarized",
  "candidates": [
    {"name": "Alice", "party": "Liberal", "ideology_position": 0.25},
    {"name": "Bob",   "party": "Conservative", "ideology_position": 0.75},
    {"name": "Carol", "ideology_position": 0.5}
  ]
}
```

**`/sensitivity` body:**
```json
{
  "base_config": { "num_voters": 500, "candidates": ["Alice", "Bob", "Charlie"] },
  "variable": "ideology_distribution",
  "values": ["random", "centrist", "polarized", "left_skewed", "right_skewed"]
}
```

### Scenarios — `/api/scenarios/`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List user's saved scenarios |
| POST | `/` | Save a scenario |
| GET | `/<id>` | Load a scenario |
| DELETE | `/<id>` | Delete a scenario |

All scenario endpoints require JWT authentication.

---

## Simulation Sandbox (frontend)

Navigate to `/simulation/compare` after logging in.

The sandbox has 5 tabs:

| Tab | Description |
|---|---|
| **Winner Matrix** | One column per simulation run, one row per method. Click any cell for drill-down detail (metrics, Condorcet comparison, method explanation). |
| **Metrics** | Bar chart averaging Bayesian Regret, Majority Satisfaction and Strategic Vulnerability across all runs. |
| **Strategic Impact** | Line chart showing how Bayesian Regret evolves as the % of strategic voters increases (0–50%). Flat lines = method resists manipulation. |
| **Condorcet Matrix** | N×N pairwise duel heatmap. Green = row candidate wins, red = loses. Highlights cycles. |
| **Sensitivity** | Vary one parameter (ideology distribution / num voters / strategic %) and observe how winners and regret change across methods. |

**Additional features:**
- **Scenario B** — add a second configuration and compare side-by-side (spoiler effect / IIA)
- **Save / Load** — persist any configuration + results set under a name
- **Export JSON / CSV** — download raw results for external analysis
- **Ideological Space Chart** — 2D scatter plot of voters (coloured by voting style) and candidates

---

## Code Style

- Python: flake8 (config in `.flake8`)
- TypeScript: Prettier (`singleQuote`, `semi`, `printWidth: 100`, `tabWidth: 2`) + ESLint `react-app`
