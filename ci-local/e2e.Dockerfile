# Local reproduction of the GitHub "E2E Tests" job (.github/workflows/e2e.yml).
#
# That job became a gate on every PR (it used to run only at release, which is how
# the suite drifted for two months). ci-local mirrors the gating jobs, so it
# mirrors this one too.
#
# Fidelity choices:
#  - python:3.11 == actions/setup-python '3.11' (same base as backend.Dockerfile),
#    plus Node 20 via NodeSource == actions/setup-node '20'. One image, because the
#    workflow runs backend + frontend + browsers on ONE runner.
#  - `npx playwright install --with-deps chromium firefox` — the exact CI step, so
#    the browser builds match the pinned @playwright/test.
#  - The backend here is a FIXTURE (Assemblée mode and two Laboratoire fiches call
#    /api/v2/*); Backend CI is the job that actually tests it.
#  - CI=true → Playwright retries once, forbids test.only, and starts its own vite
#    server (reuseExistingServer is off under CI).
#
# CI checks run as CMD, so `docker run` exits non-zero exactly when the PR would fail.
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CI=true

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates git \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && node --version && npm --version && python --version \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend deps — cached unless requirements.txt changes.
COPY fast_api_voter/requirements.txt fast_api_voter/
RUN pip install -r fast_api_voter/requirements.txt

# Frontend deps — cached unless the lockfile changes.
WORKDIR /app/voter-app
COPY voter-app/package.json voter-app/package-lock.json ./
RUN npm ci

# Browsers — cached with the lockfile layer (they track @playwright/test).
RUN npx playwright install --with-deps chromium firefox

# Source layers — bust on any source change.
WORKDIR /app
COPY fast_api_voter/ fast_api_voter/
COPY voter-app/ voter-app/

# FLASK_ENV is still read (config.py accepts APP_ENV or FLASK_ENV). No
# JWT_SECRET_KEY: nothing in api/ has read it since auth was removed, and a
# secret-shaped ENV only earns a scanner suppression for a variable nobody uses.
ENV FLASK_ENV=testing

# Same sequence as the workflow: boot the backend, wait for /api/v2/health, run
# the suite (Playwright brings up the frontend itself).
CMD ["bash","-euo","pipefail","-c","\
echo '=== Start FastAPI backend (:4434) ==='; \
(cd /app/fast_api_voter && uvicorn api.main:app --host 0.0.0.0 --port 4434 &) ; \
for _ in $(seq 30); do curl -sf http://localhost:4434/api/v2/health >/dev/null && ready=1 && break; sleep 1; done; \
[ -n \"${ready:-}\" ] || { echo 'Backend did not start in time' >&2; exit 1; }; \
echo 'Backend is ready'; \
echo '=== Playwright E2E (chromium + firefox) ==='; \
cd /app/voter-app && npm run test:e2e; \
echo '=== E2E: PASS ==='"]
