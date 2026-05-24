#!/usr/bin/env bash
# scripts/bootstrap.sh — get a freshly-cloned Vote-App ready to develop on.
#
# Usage:   ./scripts/bootstrap.sh
#
# What it does:
#   1. Verifies the toolchain (python, node, docker)
#   2. Creates flask_voter_app/.env from .env.example if missing
#   3. Installs Python deps in a venv (flask_voter_app/.venv)
#   4. Installs npm deps (voter-app/node_modules)
#   5. Installs pre-commit hooks
#   6. Builds the docker images (postgres + redis + backend)
#   7. Boots the stack and waits for the healthcheck to go green
#   8. Runs the backend test suite once to confirm everything works
#
# Idempotent: safe to re-run. Each step skips if already done.

set -euo pipefail

# ── Locate repo root regardless of where the script is called from ──────────
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ── Tiny formatting helpers ──────────────────────────────────────────────────
say()  { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
fail() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. Toolchain check ──────────────────────────────────────────────────────
say "Checking toolchain"
command -v python3 >/dev/null 2>&1 || fail "python3 not found — install Python 3.11+"
command -v node    >/dev/null 2>&1 || fail "node not found — install Node 20+"
command -v npm     >/dev/null 2>&1 || fail "npm not found"
command -v docker  >/dev/null 2>&1 || fail "docker not found — install Docker Desktop"

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
NODE_VERSION=$(node --version 2>&1 | sed 's/^v//')
ok "Python $PYTHON_VERSION, Node $NODE_VERSION, Docker installed"

# ── 2. Backend .env ─────────────────────────────────────────────────────────
say "Setting up backend env file"
if [ ! -f flask_voter_app/.env ]; then
    cp flask_voter_app/.env.example flask_voter_app/.env
    ok "Created flask_voter_app/.env from template (defaults work for local dev)"
else
    ok ".env already exists, leaving alone"
fi

# ── 3. Backend deps ─────────────────────────────────────────────────────────
say "Installing backend dependencies"
if [ ! -d flask_voter_app/.venv ]; then
    python3 -m venv flask_voter_app/.venv
    ok "Created virtualenv at flask_voter_app/.venv"
fi
# shellcheck disable=SC1091
source flask_voter_app/.venv/bin/activate 2>/dev/null \
    || source flask_voter_app/.venv/Scripts/activate    # Windows Git Bash
pip install --quiet --upgrade pip
pip install --quiet -r flask_voter_app/requirements.txt
ok "Backend deps installed"
deactivate

# ── 4. Frontend deps ────────────────────────────────────────────────────────
say "Installing frontend dependencies"
if [ ! -d voter-app/node_modules ]; then
    (cd voter-app && npm install --no-fund --no-audit --silent)
    ok "Frontend deps installed (~2 min on cold cache)"
else
    ok "node_modules already populated"
fi

# ── 5. Pre-commit hooks ─────────────────────────────────────────────────────
say "Installing pre-commit hooks"
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install --hook-type pre-commit
    pre-commit install --hook-type pre-push
    ok "Pre-commit hooks armed (detect-secrets, bandit, mypy, flake8, eslint, npm audit)"
else
    warn "pre-commit not installed system-wide — run 'pip install pre-commit' if you want git hooks"
fi

# ── 6. Docker images ────────────────────────────────────────────────────────
say "Building docker images"
(cd flask_voter_app && docker compose build --quiet) \
    || (cd flask_voter_app && docker-compose build --quiet)
ok "Images built"

# ── 7. Boot stack and wait for healthcheck ──────────────────────────────────
say "Booting stack (postgres + redis + backend)"
(cd flask_voter_app && docker compose up -d) \
    || (cd flask_voter_app && docker-compose up -d)

printf "  Waiting for backend healthcheck"
for i in $(seq 1 30); do
    if curl -sf http://localhost:4433/api/health >/dev/null 2>&1; then
        printf "\n"
        ok "Backend healthy at http://localhost:4433"
        break
    fi
    printf "."
    sleep 2
    if [ "$i" = "30" ]; then
        printf "\n"
        warn "Backend didn't go green within 60s — check 'docker compose logs backend'"
    fi
done

# ── 8. Smoke test ───────────────────────────────────────────────────────────
say "Running a quick backend smoke test"
(cd flask_voter_app && docker compose exec -T backend python -m pytest tests/test_election_simulate.py -q --tb=line 2>&1 | tail -3) \
    || warn "Smoke test failed — investigate with 'docker compose logs backend'"

# ── Done ────────────────────────────────────────────────────────────────────
say "Bootstrap complete"
cat <<EOF

Next steps:
  ▸ Backend live:   http://localhost:4433
  ▸ Health check:   http://localhost:4433/api/health
  ▸ Start frontend: cd voter-app && npm start  (opens http://localhost:3000)
  ▸ Run backend tests: cd flask_voter_app && docker compose exec backend pytest
  ▸ Tear down:      cd flask_voter_app && docker compose down

Documentation:
  ▸ Project overview:    README.md
  ▸ Architecture notes:  CLAUDE.md
  ▸ Contribution guide:  CONTRIBUTING.md
  ▸ Refactor plan:       STRATEGIC_REFACTOR_PLAN.md
EOF
