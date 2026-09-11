#!/usr/bin/env bash
# test-visual-docker.sh — run (or regenerate) the visual-regression baselines
# inside the exact Docker image the visual-regression CI job uses.
#
# Why this exists: playwright.visual.config.ts's header explains the problem —
# pixel comparisons are only stable when the baseline and the comparison render
# with byte-identical fonts/AA/rasterization. "Same host OS" isn't a strong
# enough guarantee of that on its own (see docs/exploration/EXP-004). The fix
# is to pin the *exact* Docker image tag matching this repo's @playwright/test
# version, and never generate or compare baselines anywhere else. This script
# is that pin, made runnable: a baseline regenerated with this script renders
# identically to a baseline the CI job would produce, because they use the
# same image.
#
# Requires the backend on :4434 (`uvicorn api.main:app --port 4434` in
# fast_api_voter/, per CLAUDE.md) — Assemblée mode's hemicycle and the leader
# map's win-region overlay both genuinely need it (verified: without it,
# ParliamentCanvas shows its own "hémicycle indisponible" fallback banner
# instead of seats, and LeaderCanvas silently drops the colour overlay — see
# docs/exploration/EXP-004). `--network=host` lets the container reach that
# host-run backend at plain `localhost:4434`, same as every other local
# workflow in this repo expects.
#
# Usage:
#   scripts/test-visual-docker.sh                 # run the suite, compare to committed baselines
#   scripts/test-visual-docker.sh --update-snapshots   # (re)generate baselines
#
# The image tag is derived from package.json's pinned @playwright/test version
# so a version bump can't silently drift the two out of sync.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PW_VERSION=$(node -p "require('./package.json').devDependencies['@playwright/test'].replace(/^[^0-9]*/, '')")
IMAGE="mcr.microsoft.com/playwright:v${PW_VERSION}-noble"

echo "Running visual regression suite in ${IMAGE}"

docker run --rm \
  --ipc=host \
  --network=host \
  -v "$(pwd)":/work \
  -w /work \
  -e CI=true \
  "${IMAGE}" \
  bash -c "npm ci && npx playwright test --config=playwright.visual.config.ts $*"
