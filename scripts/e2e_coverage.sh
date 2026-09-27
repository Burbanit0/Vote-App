#!/usr/bin/env bash
# scripts/e2e_coverage.sh — runtime coverage under the real Playwright e2e suite.
#
# Lot 6, PLAN_SOLIDITE_TECHNIQUE.md ("Couverture runtime"): static dead-code
# detection (vulture/knip/depcruise) only sees what's syntactically reachable;
# unit-test coverage (pytest-cov, Vitest) only sees what tests call directly,
# which can diverge sharply from what a real user session ever touches. This
# script wraps BOTH the backend and the frontend in coverage instrumentation
# for one real end-to-end pass and produces two reports of what genuinely
# executes under real browser-driven usage -- diagnostic only, not a gate
# (see docs/exploration/EXP-003-*.md for why).
#
# Mechanism:
#   - Backend: `coverage run` around a small custom entrypoint
#     (fast_api_voter/scripts/run_e2e_coverage_server.py), NOT plain
#     `coverage run -m uvicorn ...` -- uvicorn's graceful-shutdown code
#     re-raises the stopping signal against itself once cleanup finishes (a
#     deliberate idiom so process supervisors see the real exit signal),
#     which kills the process before Python's normal `atexit` machinery
#     (coverage.py's own save hook) ever runs. The custom entrypoint installs
#     its own signal handler ahead of uvicorn's so it can call
#     `coverage.save()` at that exact re-raise moment. See that script's
#     docstring for the full trace of how this was found and confirmed.
#   - Frontend: Istanbul instrumentation (vite-plugin-istanbul, gated behind
#     E2E_COVERAGE=true in vite.config.ts) exposes `window.__coverage__` in
#     the running app; tests/e2e/coverageFixtures.ts (which every spec now
#     imports `test`/`expect` from instead of '@playwright/test' directly)
#     dumps that object to voter-app/.nyc_output/ after every test, since
#     Playwright gives each test a fresh page/context that would otherwise
#     wipe it. `nyc report` then merges all the per-test blobs into one
#     aggregate report.
#
# Usage:
#   ./scripts/e2e_coverage.sh              # all Playwright projects (chromium, firefox, mobile)
#   ./scripts/e2e_coverage.sh --chromium-only
#
# Requires: backend deps installed (fast_api_voter, coverage.py is already a
# pytest-cov transitive dependency), frontend deps + Playwright browsers
# installed (voter-app/node_modules, `npx playwright install`).
#
# Output:
#   fast_api_voter/htmlcov-e2e/index.html   (backend, coverage.py HTML report)
#   voter-app/coverage-e2e/index.html       (frontend, nyc/Istanbul HTML report)

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/fast_api_voter"
FRONTEND_DIR="$REPO_ROOT/voter-app"
# Overridable, NOT the usual :4434 (CLAUDE.md's normal e2e port): some dev
# environments already run an unrelated backend there (a stray, unkillable
# process was found squatting on :4434 while building this script — this
# lets the coverage run pick a free port instead of fighting it). vite.config.ts's
# dev proxy + src/api/client.ts's API_BASE both honour VITE_API_URL, so the
# frontend is pointed at the same port below.
BACKEND_PORT="${E2E_COVERAGE_PORT:-4444}"
BACKEND_COVERAGE_FILE="$BACKEND_DIR/.coverage.e2e"

PLAYWRIGHT_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --chromium-only) PLAYWRIGHT_ARGS+=(--project=chromium) ;;
  esac
done

echo "▶ Starting the backend under coverage.py on :$BACKEND_PORT"
rm -f "$BACKEND_COVERAGE_FILE"
(
  cd "$BACKEND_DIR" && \
  PYTHONPATH="$BACKEND_DIR" COVERAGE_FILE="$BACKEND_COVERAGE_FILE" \
    python -m coverage run scripts/run_e2e_coverage_server.py --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

# Poll for real readiness instead of a fixed sleep -- coverage-instrumented
# startup is measurably slower than raw uvicorn.
echo "▶ Waiting for the backend to accept connections"
BACKEND_UP=0
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/api/v2/health" >/dev/null 2>&1; then
    BACKEND_UP=1
    break
  fi
  sleep 1
done
if [ "$BACKEND_UP" -ne 1 ]; then
  echo "✗ Backend never came up on :$BACKEND_PORT — aborting." >&2
  kill -TERM "$BACKEND_PID" 2>/dev/null
  exit 1
fi

echo "▶ Running the e2e suite (E2E_COVERAGE=true instruments the frontend build, VITE_API_URL points it at :$BACKEND_PORT)"
rm -rf "$FRONTEND_DIR/.nyc_output" "$FRONTEND_DIR/coverage-e2e"
(
  cd "$FRONTEND_DIR" && \
  E2E_COVERAGE=true VITE_API_URL="http://localhost:$BACKEND_PORT" npx playwright test "${PLAYWRIGHT_ARGS[@]}"
)
E2E_EXIT=$?

echo "▶ Stopping the backend (SIGTERM — the custom entrypoint saves coverage on this signal)"
kill -TERM "$BACKEND_PID" 2>/dev/null
wait "$BACKEND_PID" 2>/dev/null

echo
echo "▶ Backend runtime-coverage report"
if [ -f "$BACKEND_COVERAGE_FILE" ]; then
  (
    cd "$BACKEND_DIR" && \
    python -m coverage report --data-file="$BACKEND_COVERAGE_FILE" || true
    python -m coverage html --data-file="$BACKEND_COVERAGE_FILE" -d htmlcov-e2e || true
  )
else
  echo "⚠️  No backend coverage data at $BACKEND_COVERAGE_FILE"
fi

echo
echo "▶ Frontend runtime-coverage report"
if [ -d "$FRONTEND_DIR/.nyc_output" ] && [ -n "$(ls -A "$FRONTEND_DIR/.nyc_output" 2>/dev/null)" ]; then
  (
    cd "$FRONTEND_DIR" && \
    npx nyc report --temp-dir=.nyc_output --report-dir=coverage-e2e \
      --reporter=text --reporter=html --reporter=json-summary
  )
else
  echo "⚠️  No frontend coverage data in $FRONTEND_DIR/.nyc_output — was E2E_COVERAGE honoured by the webServer?"
fi

echo
echo "Backend report:  $BACKEND_DIR/htmlcov-e2e/index.html"
echo "Frontend report: $FRONTEND_DIR/coverage-e2e/index.html"

exit "$E2E_EXIT"
