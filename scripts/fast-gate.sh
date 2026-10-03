#!/usr/bin/env bash
# scripts/fast-gate.sh — the repo's fast checks, scoped to what this branch
# changed, run before a push (Claude Code's pre-push hook calls it; anyone can).
#
# Why: CI catches everything, but a cloud agent session has no git hooks, so a
# push with two unused imports (PR #714) costs a full CI round and a red PR.
# This runs the same tools CI runs, on the changed files only, in seconds to a
# few minutes.
#
# Rule: fail-closed on findings, fail-open on missing infrastructure. A section
# whose tools or dependencies aren't installed prints SKIPPED and doesn't fail
# the gate — CI still runs it — and the summary says so, so nobody mistakes a
# skip for a pass.
#
# Usage: scripts/fast-gate.sh [base-ref]   (default: origin/polity)
# Exit: 0 = no findings (some sections may be SKIPPED), 1 = a check failed.

set -uo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BASE="${1:-origin/polity}"

# Best effort: a stale base only widens the diff, it never hides a change.
timeout 20 git fetch -q origin "${BASE#origin/}" 2>/dev/null || true
if ! MB=$(git merge-base HEAD "$BASE" 2>/dev/null); then
  echo "fast-gate: cannot find a merge-base with $BASE — nothing to compare against, skipping."
  exit 0
fi
mapfile -t CHANGED < <(git diff --name-only --diff-filter=ACMR "$MB" HEAD)
if [ "${#CHANGED[@]}" -eq 0 ]; then
  echo "fast-gate: no committed changes vs $BASE."
  exit 0
fi

declare -a SUMMARY=()
FAILED=0
run() { # run <label> <command...>
  local label="$1"; shift
  echo "── $label"
  if "$@"; then SUMMARY+=("PASS     $label"); else SUMMARY+=("FAIL     $label"); FAILED=1; fi
}
skip() { echo "── $1: SKIPPED ($2)"; SUMMARY+=("SKIPPED  $1 — $2"); }
pick() { printf '%s\n' "${CHANGED[@]}" | grep -E "$1" || true; }

mapfile -t PY < <(pick '^fast_api_voter/.*\.py$')
mapfile -t PY_API < <(pick '^fast_api_voter/api/.*\.py$')
mapfile -t TS < <(pick '^voter-app/.*\.(ts|tsx|js|jsx|mjs)$')
mapfile -t ENGINE < <(pick '^(fast_api_voter/api/engine/utils/simulation_(ranked|score)_utils\.py|voter-app/src/lib/playgroundVoting\.ts|fast_api_voter/scripts/gen_engine_parity\.py)$')
mapfile -t NPM < <(pick '^(voter-app/package(-lock)?\.json|\.github/npm-audit-allowlist\.json)$')

backend_deps() { python3 -c 'import fastapi, pydantic' 2>/dev/null; }
front_deps() { [ -d voter-app/node_modules ]; }

# ── Python ──────────────────────────────────────────────────────────────────
if [ "${#PY[@]}" -gt 0 ]; then
  if command -v ruff >/dev/null; then
    run "ruff (${#PY[@]} changed files)" ruff check "${PY[@]}"
  else
    skip "ruff" "ruff not installed"
  fi
fi
if [ "${#PY_API[@]}" -gt 0 ]; then
  if ! backend_deps; then
    skip "mypy / import layering / pytest" "backend deps not installed (pip install -r fast_api_voter/requirements-dev.lock.txt)"
  else
    run "mypy api/ (strict)" bash -c 'cd fast_api_voter && python3 -m mypy api/ --config-file mypy.ini'
    if command -v lint-imports >/dev/null; then
      run "import layering (lint-imports)" bash -c 'cd fast_api_voter && lint-imports'
    else
      skip "import layering" "import-linter not installed"
    fi
    # Changed tests, plus test_<module>.py for each changed module.
    TESTS=()
    for f in "${PY_API[@]}"; do
      if [[ "$f" == fast_api_voter/api/tests/test_*.py ]]; then
        TESTS+=("${f#fast_api_voter/}")
      else
        cand="api/tests/test_$(basename "$f")"
        [ -f "fast_api_voter/$cand" ] && TESTS+=("$cand")
      fi
    done
    if [ "${#TESTS[@]}" -gt 0 ]; then
      mapfile -t TESTS < <(printf '%s\n' "${TESTS[@]}" | sort -u)
      run "pytest (${#TESTS[@]} related test files)" bash -c 'cd fast_api_voter && python3 -m pytest -o addopts="" -x -q "$@"' _ "${TESTS[@]}"
    fi
  fi
fi

# ── Frontend ────────────────────────────────────────────────────────────────
if [ "${#TS[@]}" -gt 0 ]; then
  if ! front_deps; then
    skip "eslint / tsc / vitest" "voter-app/node_modules missing (npm ci in voter-app/)"
  else
    REL=("${TS[@]#voter-app/}")
    run "eslint (${#TS[@]} changed files)" bash -c 'cd voter-app && npx eslint "$@"' _ "${REL[@]}"
    run "tsc --noEmit" bash -c 'cd voter-app && npx tsc --noEmit'
    run "vitest related" bash -c 'cd voter-app && npx vitest related --run --passWithNoTests "$@"' _ "${REL[@]}"
  fi
fi

# ── Cross-cutting ───────────────────────────────────────────────────────────
if [ "${#ENGINE[@]}" -gt 0 ]; then
  if backend_deps; then
    run "engine parity fixture in sync" ./scripts/check_engine_parity_drift.sh
  else
    skip "engine parity fixture" "backend deps not installed"
  fi
fi
if [ "${#PY_API[@]}" -gt 0 ]; then
  if backend_deps && front_deps; then
    run "OpenAPI contract in sync" ./scripts/check_openapi_drift.sh
  else
    skip "OpenAPI contract" "needs backend deps and voter-app/node_modules"
  fi
fi
if [ "${#NPM[@]}" -gt 0 ]; then
  if front_deps; then
    run "npm audit gate" bash -c 'cd voter-app && npm run -s audit:gate'
  else
    skip "npm audit gate" "voter-app/node_modules missing"
  fi
fi

# Report only: a weakened test suite isn't a failure here (deleting an obsolete
# test is legitimate), but the PR's `High-risk review gate` will hold it for the
# owner's review, so say so before the push rather than after.
if weakened=$(python3 scripts/check_test_integrity.py --base "$MB" --head HEAD 2>/dev/null) && [ -n "$weakened" ]; then
  echo "── test integrity: this PR will be held for the owner's review"
  printf '%s\n' "$weakened" | sed 's/^/   /'
  SUMMARY+=("HOLD     test integrity — $(printf '%s' "$weakened" | head -n1)")
fi

echo
echo "fast-gate summary (${#CHANGED[@]} changed files vs $BASE):"
if [ "${#SUMMARY[@]}" -eq 0 ]; then
  echo "  nothing to check for these files (docs/config only)"
else
  printf '  %s\n' "${SUMMARY[@]}"
fi
exit "$FAILED"
