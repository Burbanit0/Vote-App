# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Frontend**: React 19 + TypeScript, React Router v7, Bootstrap 5, Recharts/Chart.js, axios
- **Backend**: Flask 3.1 + SQLAlchemy 2.0 + PostgreSQL + Redis
- **Auth**: JWT (Bearer tokens, 1h expiry), bcrypt passwords
- **Background jobs**: APScheduler
- **CI/CD**: GitHub Actions (path-based triggers for frontend and backend)

## Commands

### Frontend (`voter-app/`)

```bash
npm start                # dev server on :3000
npm test                 # Jest (jsdom environment)
npm run build            # production build
npm run lint             # ESLint on .ts/.tsx
npm run prettier-format  # format TS files with Prettier
```

Single test: `npx jest src/path/to/file.test.tsx`

### Backend (`flask_voter_app/`)

```bash
docker-compose up --build        # starts Flask (:4433), PostgreSQL (:5432), Redis (:6379)
docker-compose exec backend pytest                         # run all tests
docker-compose exec backend pytest tests/test_votes.py    # single test file
docker-compose exec backend flake8                         # lint
```

Backend tests use SQLite in-memory (`TestingConfig`) — no Docker required for unit tests if you set `FLASK_ENV=testing`.

## Architecture

### Frontend

Pages (`src/pages/`) are the view layer; they compose reusable `src/components/`. API calls go through `src/services/` (axios wrappers: `authApi`, `electionsApi`, `votesApi`, `partiesApi`, `simulationsApi`) — all pointing to `http://localhost:4433`.

Global state lives in two React contexts (`src/context/`):
- `AuthContext` — current user, JWT stored in localStorage, login/logout
- `SimulationContext` — simulation state

Route protection uses `AuthGuard` + `ProtectedRoute`. Custom hooks `useElectionParticipation` and `useUserPermissions` encapsulate role/permission queries.

### Backend

Blueprints map to route files in `app/routes/`:
- `/api/auth/` — registration, login, profile, permissions
- `/api/elections/` — election CRUD, participants
- `/api/votes/` — vote casting and results
- `/api/parties/` — party management
- `/api/simulation/` — election simulation engine

Business logic lives in `app/services/`, not in routes. `app/utils/` holds JWT decorators and election calculation helpers. `app/simulation/` is an agent-based voting simulation engine.

### Data model

Key junction table: `user_election_roles` links users to elections with a `role` field (`voter` / `candidate` / `organizer`) and tracks whether the user has voted. A `User` belongs to one `Party`; `Elections` have many `Votes`; each `Vote` stores the voting method data (supports multiple voting systems).

### Migrations

`flask_voter_app/migrations/` — use Flask-Migrate (`flask db migrate` / `flask db upgrade`) for schema changes.

## Code style

- Prettier config: `singleQuote: true`, `semi: true`, `printWidth: 100`, `tabWidth: 2`, `trailingComma: "es5"`
- ESLint extends `react-app` + `react-app/jest`
- Python: flake8 (config in `.flake8`)
