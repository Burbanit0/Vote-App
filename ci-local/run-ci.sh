#!/usr/bin/env bash
# Portable runner for the local CI mirror (same Docker images as run-ci.ps1).
# Usage: ci-local/run-ci.sh [frontend|backend|audit|code|all] [--no-cache]
#   all   = frontend + backend + audit (run before each push)
#   code  = frontend + backend (quick iteration, skips the security audit)
#   audit = security scanners only (Semgrep · Gitleaks · Trivy)
set -uo pipefail

TARGET="${1:-all}"
NOCACHE=""
[[ "${2:-}" == "--no-cache" || "${1:-}" == "--no-cache" ]] && NOCACHE="--no-cache"
[[ "$TARGET" == "--no-cache" ]] && TARGET="all"

export DOCKER_BUILDKIT=1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Preflight: tracked-content guard ────────────────────────────────────────
# The images COPY the working tree, but GitHub checks out only git-TRACKED files.
# A source file on disk that git doesn't track (untracked OR gitignored) is absent
# on CI → "passes locally, fails on PR". This is the exact bug that cost a day:
# src/lib/utils.ts was swept up by a broad `lib/` .gitignore pattern. Fail loudly.
STRAY=$(git status --porcelain --ignored -- voter-app/src fast_api_voter/api 2>/dev/null \
  | grep -E '^(\?\?|!!)' | grep -E '\.(ts|tsx|js|jsx|py)$' | grep -vE '__pycache__|\.pyc' || true)
if [[ -n "$STRAY" ]]; then
  echo "ERROR: source files exist on disk but are NOT tracked by git (absent on CI):" >&2
  echo "$STRAY" >&2
  echo "Commit them (or fix .gitignore) before validating — CI will not see them." >&2
  exit 1
fi

declare -A RESULTS

run_job() {
  local name="$1" dockerfile="$2" tag="$3"
  echo -e "\n========== $name : build =========="
  if ! docker build -f "$dockerfile" -t "$tag" $NOCACHE . ; then
    RESULTS["$name"]="BUILD FAILED"; return
  fi
  echo -e "\n========== $name : run (CI checks) =========="
  if docker run --rm --cpus=4 "$tag"; then
    RESULTS["$name"]="PASS"
  else
    RESULTS["$name"]="FAIL"
  fi
}

[[ "$TARGET" == "frontend" || "$TARGET" == "all" || "$TARGET" == "code" ]] && run_job "Frontend CI" "ci-local/frontend.Dockerfile" "vote-ci-frontend"
[[ "$TARGET" == "backend"  || "$TARGET" == "all" || "$TARGET" == "code" ]] && run_job "Backend CI"  "ci-local/backend.Dockerfile"  "vote-ci-backend"
[[ "$TARGET" == "audit"    || "$TARGET" == "all" ]] && run_job "Security Audit" "ci-local/audit.Dockerfile" "vote-ci-audit"

echo -e "\n==================== SUMMARY ===================="
FAILED=0
for k in "${!RESULTS[@]}"; do
  printf "%-14s %s\n" "$k" "${RESULTS[$k]}"
  [[ "${RESULTS[$k]}" != "PASS" ]] && FAILED=1
done
echo "================================================"
exit $FAILED
