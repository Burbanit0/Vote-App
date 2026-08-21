#!/usr/bin/env bash
# scripts/check_openapi_drift.sh — fail if the generated API contract is stale.
#
# fast_api_voter/openapi.gen.json is dumped from the live FastAPI app
# (scripts/gen_openapi.py) and voter-app/src/api/types.gen.ts is generated
# from that JSON (openapi-typescript, via `npm run gen:api`). Together they
# are the single source of truth shared backend <-> frontend (see
# fast_api_voter/scripts/gen_openapi.py's docstring). Nothing enforced that
# a route/schema change was followed by regenerating both — this script
# regenerates them and fails if the working tree then differs from what's
# committed, so a stale contract shows up in CI instead of at runtime.
#
# Usage:
#   ./scripts/check_openapi_drift.sh
#
# Requires: fast_api_voter's requirements.txt installed (to import the app)
# and voter-app's node_modules installed (for openapi-typescript).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "▶ Regenerating fast_api_voter/openapi.gen.json"
(cd fast_api_voter && python scripts/gen_openapi.py)

echo "▶ Regenerating voter-app/src/api/types.gen.ts"
(cd voter-app && npm run --silent gen:api)

echo "▶ Diffing against committed files"
if git diff --exit-code -- fast_api_voter/openapi.gen.json voter-app/src/api/types.gen.ts; then
  echo "✅ API contract is in sync."
else
  echo ""
  echo "🔴 The generated API contract is out of date." >&2
  echo "   A route or Pydantic schema changed without regenerating it. Run:" >&2
  echo "     cd fast_api_voter && python scripts/gen_openapi.py" >&2
  echo "     cd voter-app && npm run gen:api" >&2
  echo "   then commit the updated files." >&2
  exit 1
fi
