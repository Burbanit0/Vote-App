# Vote Lab

A civic research sandbox for voting theory — demonstrating empirically that the choice of voting method changes the winner, and exploring the constitutional role of the blank vote.

---

## Research Goals

- Run simulated elections with demographically realistic voters and observe how different voting methods elect **different winners from the same population**
- Measure **Bayesian Regret**, **majority satisfaction**, **strategic vulnerability**, and **Gibbard-Satterthwaite manipulability** per method
- Model **sincere vs. strategic voters** and visualise how tactical voting degrades each method
- Detect **Condorcet cycles** and **IIA violations** (spoiler effect)
- Simulate **blank vote rules** (symbolic, competitive, threshold 30 %, majority required) and their constitutional impact
- Teach voting theory interactively with an animated vote-count visualiser, a pedagogical quiz, and a teacher presentation mode

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.1 + SQLAlchemy 2.0 + PostgreSQL + Redis |
| Auth | JWT (Bearer tokens, 1 h expiry) + bcrypt |
| Frontend | React 19 + TypeScript + React Router v7 + Vite |
| UI | Bootstrap 5 + react-bootstrap |
| Charts | Recharts + Chart.js |
| i18n | i18next (FR / EN toggle) |
| PDF | jsPDF + html2canvas |
| E2E tests | Playwright (Chromium + Firefox) |
| CI/CD | GitHub Actions (path-based triggers) |
| Type checking | mypy strict on backend utils + routes |

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

The default values work for local development. For production, generate strong keys:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the backend (Flask + PostgreSQL + Redis)

```bash
cd flask_voter_app
docker-compose up --build
```

| Service | URL |
|---|---|
| Flask API | http://localhost:4433 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Database migrations run automatically on first start.

### 4. Start the frontend

```bash
cd voter-app
npm install
npm start          # Vite dev server → http://localhost:3000
```

---

## Development Commands

### Backend

```bash
docker-compose up --build                            # start all services
docker-compose exec web pytest                       # all tests
docker-compose exec web pytest tests/test_sim.py     # single file
docker-compose exec web flake8                       # lint

# Without Docker (SQLite in-memory)
cd flask_voter_app
FLASK_ENV=testing JWT_SECRET_KEY=test python -m pytest tests -v

# Type checking (mypy strict on utils/ and routes/)
cd flask_voter_app && python -m mypy app/utils/ app/routes/ --config-file mypy.ini

# Database migrations
docker-compose exec web flask db migrate -m "description"
docker-compose exec web flask db upgrade
```

### Frontend

```bash
cd voter-app
npm start                      # Vite dev server on :3000
npm test                       # Jest unit tests
npm run test:e2e               # Playwright E2E (Chromium + Firefox)
npm run test:e2e:ui            # Playwright with interactive UI
npm run test:a11y              # axe-core accessibility audit
npm run build                  # production build
npm run lint                   # ESLint (includes jsx-a11y rules)
```

---

## Local Setup for Contributors (one-time)

```bash
# Git hooks (secrets scan, bandit, flake8, eslint, npm audit on commit;
#            frontend + backend tests with coverage ≥ 30% on push)
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push

# Python dev tools (mypy, bandit, pip-audit, …)
pip install -r flask_voter_app/requirements-dev.txt
```

### Branch strategy

```
main         ← official releases only (via Release workflow)
develop      ← integration branch
feature/xxx  ← one branch per feature/fix → PR to develop
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete policy.

---

## Architecture

### Backend

```
flask_voter_app/app/
├── models.py                         # SQLAlchemy ORM (User, SimulationScenario)
├── config.py                         # Dev / Testing / Production configs
├── types.py                          # Shared TypedDicts for type annotations
├── routes/
│   ├── users.py                      # /api/auth/ — register, login, profile
│   ├── scenarios.py                  # /api/scenarios/ — save/load scenarios
│   ├── simulation_base.py            # /simulations/ — core entry points
│   ├── simulation_compare.py         # /compare, /strategic-impact, /condorcet-matrix,
│   │                                 #   /sensitivity, /arrow-criteria, /scenario,
│   │                                 #   /constitutional-scenario, /manipulability
│   ├── simulation_advanced.py        # /bandwagon, /monte-carlo, /multiwinner,
│   │                                 #   /real-elections, /blank-contagion
│   ├── simulation_whatif.py          # /what-if — single-parameter variation
│   └── simulation_helpers.py         # shared route helpers
└── utils/
    ├── simulation_voting_utils.py    # voter/candidate generation, utility model
    ├── simulation_ranked_utils.py    # 12 ranked voting algorithms
    ├── simulation_score_utils.py     # 5 score voting algorithms
    ├── simulation_metrics.py         # compare_all_methods(), get_condorcet_matrix()
    ├── gibbard_satterthwaite.py      # manipulability index (Gibbard-Satterthwaite)
    ├── blank_vote_rules.py           # BlankVoteRule enum + apply_blank_rule()
    ├── arrow_criteria.py             # Arrow's impossibility criteria checker
    └── real_election_data.py         # historical election data
```

### Frontend

```
voter-app/src/
├── pages/
│   ├── HomePage.tsx                  # Landing page + onboarding tour
│   ├── SimulationComparePage.tsx     # Main sandbox (11 tabs)
│   ├── ScenarioBuilderPage.tsx       # 4-step wizard
│   ├── ConstitutionalCrisisPage.tsx  # Blank vote crisis simulator
│   ├── QuizPage.tsx                  # Pedagogical quiz (20 questions, 3 levels)
│   ├── WhatIfPage.tsx               # "Et si…" single-parameter variation
│   └── TeacherPresentationPage.tsx   # Teacher mode slide editor
├── components/
│   ├── Simulation/
│   │   ├── WinnerMatrixTab.tsx       # Winner table + drill-down + animated count
│   │   ├── ManipulabilityChart.tsx   # Gibbard-Satterthwaite horizontal bar chart
│   │   └── …                        # MetricsTab, CondorcetMatrix, BandwagonAnalysis, …
│   ├── pedagogy/
│   │   └── AnimatedVoteCount.tsx     # Step-by-step vote count visualisation
│   ├── teacher/
│   │   └── TeacherBanner.tsx         # Teacher mode banner + floating 📌 button + PinZone
│   └── shared/
│       ├── MethodTooltip.tsx         # Keyboard-accessible method definition tooltip
│       ├── ResponsiveTable.tsx       # Horizontal-scroll table with ARIA region
│       └── …                        # SkeletonCard, ToastNotification, OnboardingTour
├── context/
│   ├── AuthContext.tsx               # JWT auth state
│   ├── ThemeContext.tsx              # Dark / light mode (data-bs-theme)
│   ├── ExpertModeContext.tsx         # Beginner / expert display mode
│   └── TeacherModeContext.tsx        # Teacher slides, captureScreen, exportPresentation
├── constants/
│   └── chartColors.ts               # WCAG AA-compliant colour palettes (light + dark)
├── data/
│   └── quizQuestions.ts             # 20 quiz questions (débutant / intermédiaire / expert)
├── i18n/
│   ├── index.ts                      # i18next config (FR default, EN toggle)
│   └── locales/fr.ts + en.ts        # Full translations for all UI strings
├── hooks/ services/ utils/           # axios wrappers, useMetaTags, shareUtils, …
└── tests/e2e/                        # Playwright: navigation, simulation, scenario,
                                      #   dark-mode, accessibility
```

---

## Pages & Routes

| Route | Description | Auth |
|---|---|---|
| `/` | Landing page with live stats | Public |
| `/simulation/compare` | 11-tab simulation sandbox | Public |
| `/scenario-builder` | 4-step election wizard | Public |
| `/constitutional-crisis` | Blank vote crisis simulator | Public |
| `/quiz` | Pedagogical quiz — 20 questions | Public |
| `/what-if` | Single-parameter "Et si…" analysis | Public |
| `/teacher/presentation` | Teacher presentation editor | Teacher mode |
| `/login` / `/register` | Authentication | Public |
| `/profile` | User profile | JWT |

---

## Simulation Sandbox (`/simulation/compare`)

The main tool has **11 tabs**:

| Tab | Description |
|---|---|
| **Résultats** | Winner per method. Click any cell for a drill-down with metrics and an animated step-by-step vote count. |
| **Métriques** | Bayesian Regret, Majority Satisfaction, Strategic Vulnerability averaged across all runs. |
| **Impact stratégique** | How Bayesian Regret evolves as the % of strategic voters increases (0–50%). |
| **Matrice de Condorcet** | N×N pairwise duel heatmap — highlights cycles. |
| **Critères d'Arrow** | Empirical verification of Arrow's impossibility criteria. |
| **Effet bandwagon** | Cascading social influence across N rounds. |
| **Monte Carlo** | Robustness analysis across 1 000+ random populations. |
| **Élections réelles** | Historical elections (France 2002/2022, USA 1992, UK 2015) with blank vote rates. |
| **Multi-gagnants** | Proportional / semi-proportional methods for multi-seat elections. |
| **Sensibilité** | Vary one parameter and observe how winners change across methods. |
| **Manipulabilité** | Gibbard-Satterthwaite index — % of voters who can improve their outcome by not voting sincerely. |

**UX features:**
- **FR / EN language toggle** — instant UI switch, persisted in localStorage
- **Dark mode** — toggle in navbar
- **Beginner / Expert mode** — hides advanced tabs and terminology
- **Animated vote count** — step-by-step walk-through of how each method counts votes (📌 in results modal)
- **Keyboard-accessible tooltips** — Enter to open, Escape to close, Tab to navigate
- **Share URL** — encodes current configuration into a URL
- **Export PDF** — full simulation report
- **Fullscreen presentation mode**
- **Teacher Mode** — capture any view as a slide, build and export a PDF presentation

---

## Pedagogical Quiz (`/quiz`)

20 questions across three difficulty levels, with immediate feedback and explanations:

| Level | Topics |
|---|---|
| Débutant (7) | Plurality, approval, two-round, blank vote, majority, Borda, spoiler effect |
| Intermédiaire (7) | IRV elimination, Condorcet paradox, THRESHOLD_30, strategic voting, MAJORITY_REQUIRED |
| Expert (6) | Arrow's theorem, Bayesian regret, Schulze vs IRV, STAR, IIA, Gibbard-Satterthwaite |

Features: difficulty filter, Fisher-Yates shuffle on replay, best score per level in localStorage.

---

## "Et si…" Analysis (`/what-if`)

Compare winners across 5 methods while varying **one parameter** (number of voters, candidates, blank vote %, or polarisation). The Recharts line chart annotates every point where the winner changes between methods.

---

## Teacher Mode (`/teacher/presentation`)

Activated via the 🎓 button in the navbar (password-protected). When active:
- A green banner shows the slide count
- A floating **📌 Add** button captures any view as a slide (html2canvas screenshot)
- The presentation editor at `/teacher/presentation` provides:
  - Drag-and-drop slide reordering (HTML5 DnD)
  - Editable title and teacher notes per slide
  - Fullscreen presentation mode with keyboard navigation (← →, F, Esc)
  - **PDF export** — A4 landscape, one slide per page, notes in a grey zone at the bottom

---

## Animated Vote Count

The **📌 Animer** button in the winner matrix drill-down modal plays a step-by-step animation of how each voting method counts ballots:

| Method | Steps | Algorithm |
|---|---|---|
| Plurality | 1 | First-choice count |
| Borda | 1 | n−1 → 0 points per rank |
| IRV | N | Eliminate last-place, transfer votes |
| Two-Round | 1–2 | Majority check → runoff |
| Approval | 1 | Approve top ⌈n/2⌉ candidates |
| Schulze | 1 (simplified) | Pairwise win count |
| STAR | 2 | Score phase → automatic runoff |

In **Beginner mode**, the Plurality animation opens automatically on first result.

---

## Gibbard-Satterthwaite Manipulability

`GET /simulations/manipulability?num_candidates=4&num_voters=500`

Estimates the proportion of voters who can improve their outcome by submitting a non-sincere ballot (swapping adjacent pairs in their ranking). Returns results for 9 ranked methods, sorted by manipulability rate.

The frontend **ManipulabilityChart** colour-codes results:
- 🟢 < 5 % — Resistant
- 🟠 5–20 % — Moderate
- 🔴 > 20 % — Vulnerable

---

## Accessibility (WCAG 2.1 AA)

- **Chart colours** — all palettes in `chartColors.ts` meet ≥ 4.5:1 contrast on both light and dark backgrounds
- **Keyboard navigation** — MethodTooltip supports Enter (toggle), Space (toggle), Escape (close and blur)
- **Form labels** — every `<input>`, `<select>`, `<range>` has an associated `<label htmlFor>`
- **ARIA** — ResponsiveTable has `role="region"` + `aria-label` + `tabIndex`
- **axe-core audits** — `npm run test:a11y` runs AxeBuilder on all 4 main pages

---

## API Reference

### Auth — `/api/auth/`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Register a new user |
| POST | `/login` | Login (returns JWT) |
| GET | `/profile` | Current user profile (JWT required) |

### Scenarios — `/api/scenarios/`

All routes require JWT.

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
| POST | `/arrow-criteria` | Arrow's impossibility criteria per method |
| POST | `/scenario` | ScenarioBuilder wizard run |
| POST | `/constitutional-scenario` | Blank vote crisis simulation |
| POST | `/bandwagon` | Bandwagon effect simulation |
| POST | `/monte-carlo` | Monte Carlo robustness analysis |
| POST | `/multiwinner` | Multi-winner proportional methods |
| GET  | `/real-elections` | List historical elections |
| GET  | `/real-election` | Analyse one historical election |
| GET  | `/what-if` | Single-parameter variation analysis |
| GET  | `/manipulability` | Gibbard-Satterthwaite manipulability index |

### `/compare` example body

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

### `/manipulability` query params

```
GET /simulations/manipulability?num_candidates=4&num_voters=500&methods=all&num_trials=200
```

---

## Voting Methods (15)

**Ranked (12):** Plurality, Two-Round, Borda, Approval, IRV, Coombs, Bucklin, Minimax, Schulze, Kemeny-Young, Positional Score, Condorcet

**Score (3):** Simple Score, STAR Voting, Median Score

---

## Blank Vote Rules

| Rule | Effect |
|---|---|
| `SYMBOLIC` | Counted separately, never affects the result |
| `COMPETITIVE` | Blank acts as a full candidate — can win |
| `THRESHOLD_30` | If blank > 30 %, the election is invalidated |
| `MAJORITY_REQUIRED` | Winner must beat blank in a direct pairwise duel |

---

## Reset the Database

```bash
cd flask_voter_app
docker-compose down -v       # remove containers AND the postgres volume
docker-compose up --build    # recreate and migrate automatically
```

---

## Code Style

- **Python:** flake8 + bandit (SAST) + mypy strict on `app/utils/` and `app/routes/`
- **TypeScript:** Prettier (`singleQuote`, `semi`, `printWidth: 100`) + ESLint with `jsx-a11y`
