#!/usr/bin/env bash
# scripts/check_engine_parity_drift.sh — fail if the golden parity fixture is stale.
#
# There are two implementations of the voting rules: the live client engine
# (voter-app/src/lib/playgroundVoting.ts) and the authoritative Python backend
# (fast_api_voter/api/engine/utils/). A Vitest test
# (voter-app/src/lib/playgroundVoting.parity.test.ts) locks them together by
# asserting the client returns the winners recorded in
# voter-app/src/lib/__fixtures__/engineParity.json.
#
# That fixture is GENERATED (fast_api_voter/scripts/gen_engine_parity.py) — and
# nothing regenerated it in CI. A backend rule could change while the fixture kept
# the old winners: the parity test would stay green against a frozen snapshot while
# the two engines silently diverged, on the invariant this whole project rests on.
# CLAUDE.md asked for a re-run by convention; this makes it a mechanism.
#
# Same shape as scripts/check_openapi_drift.sh: regenerate, then diff against what
# is committed. The generator is deterministic (random.Random(SEED), json.dump with
# a fixed indent), so a clean tree regenerates byte-identical output.
#
# Usage:
#   ./scripts/check_engine_parity_drift.sh
#
# Requires: fast_api_voter's requirements.txt installed (the generator imports the
# engine directly — no server needed).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

FIXTURE="voter-app/src/lib/__fixtures__/engineParity.json"

echo "▶ Regenerating $FIXTURE from the backend engine"
PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py

echo "▶ Diffing against the committed fixture"
# --quiet, then --stat on failure: a rule change re-rolls the whole generator RNG
# stream, so the raw diff is ~200 kB of ballots — useless in a CI log.
if git diff --quiet -- "$FIXTURE"; then
  echo "✅ Engine parity fixture is in sync with the backend."
else
  git diff --stat -- "$FIXTURE"
  echo ""
  echo "🔴 The golden parity fixture is out of date." >&2
  echo "   A backend voting rule changed without regenerating it, so the client⇄backend" >&2
  echo "   parity test has been asserting against stale winners. Run:" >&2
  echo "     PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py" >&2
  echo "   then run the parity test and treat any failure as a real divergence:" >&2
  echo "     cd voter-app && npx vitest run src/lib/playgroundVoting.parity.test.ts" >&2
  echo "   Commit the regenerated fixture with the rule change." >&2
  exit 1
fi
