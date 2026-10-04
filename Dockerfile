# ──────────────────────────────────────────────────────────────────────────────
# Vote Lab — single-container production image.
#
# Builds the React/Vite frontend, then serves it AND the API from one
# FastAPI/uvicorn process (same origin → no CORS, same-origin websockets).
# Redis is optional and absent here; the app is fully stateless.
#
# Build context = repo root.
#   docker build -t votelab:prod .
#   docker run -p 4434:4434 votelab:prod   →  http://localhost:4434
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: frontend build (Vite → /voter-app/build) ───────────────────────
FROM node:26-slim AS frontend
WORKDIR /voter-app
# Install exactly what the committed lockfile pins (same as CI's `npm ci`);
# .npmrc carries engine-strict.
COPY voter-app/package.json voter-app/package-lock.json voter-app/.npmrc ./
RUN npm ci --no-audit --no-fund
COPY voter-app/ ./
# Production build defaults the API/socket base to '' (same origin — see
# vite.config.ts). Skip the redundant tsc pass (CI typechecks); vite build alone
# emits the bundle into ./build (vite.config build.outDir).
RUN npx vite build

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash app
WORKDIR /app

# The lockfile, not requirements.txt: transitive versions are pinned too.
# Binary wheels only — every pin ships one, so no compiler is needed, and a
# future pin without a wheel fails the build loudly instead of compiling.
COPY fast_api_voter/requirements.lock.txt .
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.lock.txt

# Backend code, then the built frontend.
COPY --chown=app:app fast_api_voter/ /app/
COPY --chown=app:app --from=frontend /voter-app/build /app/frontend

USER app

ENV APP_ENV=production \
    FRONTEND_DIR=/app/frontend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

EXPOSE 4434

# Stdlib only, no curl needed: /api/v2/health returns 200 healthy / 503
# degraded, and urlopen raises on a non-2xx status, so a 503 correctly fails
# the check. sys.exit(str) prints the message to stderr and exits 1 — a
# terse one-liner in `docker inspect`'s health log, not a full traceback
# (fast_api_voter/Dockerfile's dev image predates this and still raises raw;
# not changed here, out of scope).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request as u\ntry:\n u.urlopen('http://localhost:4434/api/v2/health')\nexcept Exception as e:\n sys.exit(f'health check failed: {e}')"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "4434", "--workers", "1"]
