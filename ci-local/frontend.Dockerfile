# Local reproduction of the GitHub "Frontend CI" job (.github/workflows/frontend-ci-cd-pipeline.yml).
#
# Fidelity choices that matter:
#  - ubuntu:24.04 == GitHub `ubuntu-latest` (same distro, case-SENSITIVE filesystem).
#  - Node 20 via NodeSource (== actions/setup-node node-version 20).
#  - Source is COPYed in (native ext4), NOT bind-mounted from the Windows host —
#    a Windows bind-mount masked the `@/` coverage-resolve bug we were chasing.
#  - `npm ci` from the committed lockfile (== the CI install step).
#  - CI=true (the workflow sets it on the test step).
#
# Build = environment + install (cached). The CI checks run as CMD, so `docker run`
# exits non-zero exactly when the PR would fail.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive CI=true
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates git \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && node --version && npm --version \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/voter-app

# Install layer — cached unless the lockfile changes.
COPY voter-app/package.json voter-app/package-lock.json ./
RUN npm ci

# Source layer — busts on any source change (so each run reflects current code).
COPY voter-app/ ./

# Mirror the workflow steps in order. Lint is `continue-on-error` upstream, so it
# is non-blocking here too; audit/coverage/build are gating.
CMD ["bash","-euo","pipefail","-c","\
echo '=== Lint (non-blocking) ===';        npm run lint || echo '(lint failed — non-blocking, matches continue-on-error)'; \
echo '=== npm audit (high blocks) ===';    npm audit --audit-level=high; \
echo '=== Tests + coverage ===';           npm run test:coverage; \
echo '=== Build ===';                       npm run build; \
echo '=== Frontend CI: PASS ==='"]
