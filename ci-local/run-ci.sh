#!/usr/bin/env bash
# Portable runner for the local CI mirror (same Docker images as run-ci.ps1).
# Usage: ci-local/run-ci.sh [frontend|backend|all] [--no-cache]
set -uo pipefail

TARGET="${1:-all}"
NOCACHE=""
[[ "${2:-}" == "--no-cache" || "${1:-}" == "--no-cache" ]] && NOCACHE="--no-cache"
[[ "$TARGET" == "--no-cache" ]] && TARGET="all"

export DOCKER_BUILDKIT=1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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

[[ "$TARGET" == "frontend" || "$TARGET" == "all" ]] && run_job "Frontend CI" "ci-local/frontend.Dockerfile" "vote-ci-frontend"
[[ "$TARGET" == "backend"  || "$TARGET" == "all" ]] && run_job "Backend CI"  "ci-local/backend.Dockerfile"  "vote-ci-backend"

echo -e "\n==================== SUMMARY ===================="
FAILED=0
for k in "${!RESULTS[@]}"; do
  printf "%-14s %s\n" "$k" "${RESULTS[$k]}"
  [[ "${RESULTS[$k]}" != "PASS" ]] && FAILED=1
done
echo "================================================"
exit $FAILED
