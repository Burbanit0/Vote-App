# AGENTS.md

High-signal facts for working in this repo.

## Repository structure

Two independent packages:

| Package | Dir | Port | Dev command |
|---------|-----|------|-------------|
| Frontend (React 19 + Vite) | `voter-app/` | :3000 | `npm start` |
| Backend (Flask 3.1) | `flask_voter_app/` | :4433 | `docker-compose up --build` |

## Critical — stale docs

The `CLAUDE.md` and `README.md` describe models (Election, Vote, Party, user_election_roles) that **do not exist in the code**. The real `app/models.py` only has `User` and `SimulationScenario`. The app is a voting-*theory simulation research sandbox*, not a general voting app. Ignore any references to election CRUD, vote casting, party management, or the old "Vote-App" data model.

## Commands

### Frontend

```bash
npm start                # Vite dev server :3000
npm test                 # Jest (jsdom), coverage threshold 30%
npm run build            # tsc --noEmit && vite build
npm run lint             # ESLint
npm run prettier-format  # Prettier
npx jest src/path/to/file.test.tsx  # single test
npm run preview          # vite preview
```

### Backend

```bash
# Full stack with Docker (PostgreSQL :5432, Redis :6379)
docker-compose up --build
docker-compose exec backend pytest                     # all tests
docker-compose exec backend flake8                     # lint
docker-compose exec backend flask db migrate -m "msg"  # schema change
docker-compose exec backend flask db upgrade

# Without Docker (SQLite in-memory, no infra needed)
cd flask_voter_app
FLASK_ENV=testing JWT_SECRET_KEY=test python -m pytest tests -v
FLASK_ENV=testing JWT_SECRET_KEY=test python -m pytest tests/test_simulation.py -v  # single file
```

Backend tests use `TestingConfig` → SQLite in-memory. No Docker required for unit tests.

## Permissions

`opencode.json` requires **ask** for bash/edit/write. The agent must request permission before making changes or running commands.

## Architecture

### Frontend (`voter-app/src/`)

- **Pages** (`pages/`) compose **Components** (`components/`)
- **API calls** go through `services/` (axios, defaults to `http://localhost:4433`)
- **Contexts** (`context/`): `AuthContext` (JWT in localStorage), `ThemeContext` (dark/light), `ExpertModeContext`, `SimuContext`
- **i18n** in `i18n/` — UI labels in French
- **Vite** defines `process.env.VITE_API_URL` for Jest compatibility

### Backend (`flask_voter_app/app/`)

- **Blueprints** in `routes/`: `users` (auth), `simulation_base`, `simulation_compare`, `simulation_advanced`, `scenarios`
- **Business logic** in `services/`, **utils** in `utils/`
- **Config** in `config.py`: `DevelopmentConfig`, `TestingConfig` (SQLite :memory:), `ProductionConfig` (validates secrets)
- **Auth**: JWT (Bearer, 1h expiry) via Flask-JWT-Extended, bcrypt passwords
- **Models**: `User` (id, username, password_hash, role, profile fields) and `SimulationScenario` (id, user_id, name, config JSON, results JSON)
- **Migrations** (`migrations/`) are gitignored; use `flask db migrate/upgrade`

### Simulation system

- 15 voting methods (ranked + score), agent-based voter model, blank vote rules
- Simulation endpoints under `/simulations/` are **public** (no auth required)
- Scenario save/load under `/api/scenarios/` requires JWT

## Code style

- **Prettier**: singleQuote, semi, printWidth 100, tabWidth 2, trailingComma "es5"
- **ESLint**: extends react-app + react-app/jest, prettier plugin, `endOfLine: auto`
- **Flake8**: max-line-length 88, ignore F824/W503/E203
- **Coverage**: minimum 30% (frontend + backend)

## Git workflow

- Branch prefixes: `feature/`, `fix/`, `hotfix/`, `refactor/`, `chore/`, `docs/`, `test/`, `ci/`, `perf/`, `security/`
- Only PRs into `develop`, only `develop` PRs into `main` (via Release workflow)
- Conventional commits for PR titles: `type(scope): description`
- Pre-commit: detect-secrets, bandit, flake8, eslint, npm audit
- Pre-push: frontend + backend tests with coverage ≥ 30%
- PR template at `.github/PULL_REQUEST_TEMPLATE.md`

### Agent workflow for changes

When making a significant change, the agent must follow this sequence:

1. **Create a feature branch** from `develop` with the appropriate prefix
2. **Implement** the change, maintaining existing tests and writing new ones as needed
3. **Run all relevant tests** and confirm they pass (frontend: `npm test`, backend: `FLASK_ENV=testing JWT_SECRET_KEY=test python -m pytest tests -v`)
4. **Update `README.md`** if the change affects architecture, API, or commands
5. **Commit** with a conventional commit message (`type(scope): description`)
6. **Merge** the feature branch into `develop` with `--no-ff`
7. **Delete** the feature branch
8. **Push** `develop` to remote
9. **Wait for user approval** at each git step (branch, commit, merge, push) due to `ask` permissions

## CI/CD

Path-triggered workflows:
- `voter-app/**` changes → Frontend CI (lint, audit, test with coverage, build)
- `flask_voter_app/**` changes → Backend CI (flake8, bandit, pip-audit, pytest with 30% coverage)
- Branch policy validates branch naming and PR title format
- Release workflow: manual dispatch from `develop` → main, bumps `voter-app/package.json` version, creates GitHub release
