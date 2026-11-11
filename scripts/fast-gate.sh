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

# macOS ships bash 3.2 and no `timeout`. This script used `mapfile` (bash 4) and `timeout`, and
# on a Mac it died on the first of them without failing: it printed "nothing to check" and
# exited 0, a false pass. So it sticks to what bash 3.2 has, and these two helpers stand in.
read_into() { # read_into <array>: fill the array from stdin, one element per line
  local __ri_name="$1" __ri_line
  eval "$__ri_name=()"
  # `|| [ -n ... ]` keeps a last line with no newline, as mapfile does.
  while IFS= read -r __ri_line || [ -n "$__ri_line" ]; do eval "$__ri_name+=(\"\$__ri_line\")"; done
}
with_timeout() { # with_timeout <seconds> <command...>
  local secs="$1"; shift
  if command -v timeout >/dev/null; then timeout "$secs" "$@"
  elif command -v gtimeout >/dev/null; then gtimeout "$secs" "$@"
  else
    # No timeout tool (stock macOS): at least never wait on a prompt, which is how a
    # fetch hangs here. A stalled network still waits, up to git's and ssh's own limits.
    GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=10" "$@"
  fi
}

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BASE="${1:-origin/polity}"

# Best effort: a stale base only widens the diff, it never hides a change.
with_timeout 20 git fetch -q origin "${BASE#origin/}" 2>/dev/null || true
if ! MB=$(git merge-base HEAD "$BASE" 2>/dev/null); then
  echo "fast-gate: cannot find a merge-base with $BASE — nothing to compare against, skipping."
  exit 0
fi
# Captured first: a process substitution would hide a failing `git diff` (a shallow clone, an
# index lock) and read as "no changes", a false pass.
if ! DIFF_OUT=$(git diff --name-only --diff-filter=ACMR "$MB" HEAD); then
  echo "fast-gate: git diff against $BASE failed, so nothing was checked." >&2
  exit 1
fi
read_into CHANGED <<< "$DIFF_OUT"
# Every expansion of an array below sits behind a length check: under `set -u`, bash 3.2
# aborts on "${empty[@]}", so keep it that way.
if [ "${#CHANGED[@]}" -eq 0 ] || { [ "${#CHANGED[@]}" -eq 1 ] && [ -z "${CHANGED[0]}" ]; }; then
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

read_into PY < <(pick '^fast_api_voter/.*\.py$')
read_into PY_API < <(pick '^fast_api_voter/api/.*\.py$')
read_into TS < <(pick '^voter-app/.*\.(ts|tsx|js|jsx|mjs)$')
read_into ENGINE < <(pick '^(fast_api_voter/api/engine/utils/simulation_(ranked|score)_utils\.py|voter-app/src/lib/playgroundVoting\.ts|fast_api_voter/scripts/gen_engine_parity\.py)$')
read_into NPM < <(pick '^(voter-app/package(-lock)?\.json|\.github/npm-audit-allowlist\.json)$')
# Every change, deletions included (CHANGED leaves them out): removing a workflow moves the counts.
read_into CI_FACTS < <(git diff --name-only "$MB" HEAD | grep -E '^(CONTRIBUTING\.md|\.claude/skills/voter-ci/SKILL\.md|scripts/(ci_facts|check_ci_health)\.py|scripts/setup-branch-protection\.sh|\.github/workflows/[^/]+\.ya?ml)$' || true)

# The backend sections need an interpreter at the version the repo targets
# (mypy.ini's python_version): an older one with fastapi installed passed the
# import probe alone, then failed mypy, pytest and the OpenAPI check on syntax it
# cannot parse (PEP 695 generics), which read as this branch's failure. Both
# names are checked: mypy and pytest run `python3`, the parity and OpenAPI drift
# scripts (shared with CI) run `python`. Too old or no deps: those sections are
# SKIPPED with the reason, and CI runs them.
NEED_PY=$(sed -nE 's/^python_version *= *([0-9]+\.[0-9]+).*/\1/p' fast_api_voter/mypy.ini | head -1)
BACKEND_WHY=""
for py in python3 python; do
  if ! "$py" -c "import sys; sys.exit(sys.version_info[:2] < tuple(map(int, '${NEED_PY:-0.0}'.split('.'))))" 2>/dev/null; then
    BACKEND_WHY="$py is $("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo missing), the backend needs ${NEED_PY} (put a ${NEED_PY} venv first on PATH)"
  elif ! "$py" -c 'import fastapi, pydantic' 2>/dev/null; then
    BACKEND_WHY="backend deps not installed for $py (pip install -r fast_api_voter/requirements-dev.lock.txt)"
  fi
  [ -n "$BACKEND_WHY" ] && break
done
backend_deps() { [ -z "$BACKEND_WHY" ]; }
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
    skip "mypy / import layering / pytest" "$BACKEND_WHY"
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
      read_into TESTS < <(printf '%s\n' "${TESTS[@]}" | sort -u)
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
    skip "engine parity fixture" "$BACKEND_WHY"
  fi
fi
if [ "${#PY_API[@]}" -gt 0 ]; then
  if backend_deps && front_deps; then
    run "OpenAPI contract in sync" ./scripts/check_openapi_drift.sh
  else
    skip "OpenAPI contract" "${BACKEND_WHY:-voter-app/node_modules missing}"
  fi
fi
if [ "${#CI_FACTS[@]}" -gt 0 ]; then
  if python3 -c 'import cogapp' 2>/dev/null; then
    run "CI counts in the docs in sync" env PYTHON=python3 ./scripts/check_generated_docs.sh CONTRIBUTING.md .claude/skills/voter-ci/SKILL.md
  else
    skip "CI counts in the docs" "cogapp not installed (fast_api_voter/requirements-dev.txt)"
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

# Report only: a regenerated test oracle passes its own check by design, so
# show what it changed (scripts/oracle_diff_report.py) before the reviewer has to.
if oracles=$(python3 scripts/oracle_diff_report.py --base "$MB" --head HEAD 2>/dev/null) && [ -n "$oracles" ]; then
  echo "── test oracles changed: review this behaviour change, not just the green check"
  printf '%s\n' "$oracles" | grep -E '^(###|- |  - )' | sed 's/^/   /'
  SUMMARY+=("NOTE     test oracles changed — see above")
fi

echo
echo "fast-gate summary (${#CHANGED[@]} changed files vs $BASE):"
if [ "${#SUMMARY[@]}" -eq 0 ]; then
  echo "  nothing to check for these files (docs/config only)"
else
  printf '  %s\n' "${SUMMARY[@]}"
fi
exit "$FAILED"
