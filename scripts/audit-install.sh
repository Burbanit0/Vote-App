#!/usr/bin/env bash
#
# audit-install.sh — install the local audit toolchain for scripts/audit.sh.
# Idempotent; skips what's present. The CI workflow (.github/workflows/audit.yml)
# already runs Semgrep/CodeQL/Gitleaks/Trivy on Ubuntu, so installing locally is
# OPTIONAL — only needed if you want to run ./scripts/audit.sh on your machine.
#
# Windows note: the Python tools (semgrep, bandit) install via pip and work fine.
# Gitleaks/Trivy/jq are native binaries — on Windows use scoop/winget, e.g.
#   scoop install gitleaks trivy jq      (or)      winget install jqlang.jq
# If you skip them, audit.sh degrades gracefully and CI covers the scanning.
#
set -uo pipefail
have() { command -v "$1" >/dev/null 2>&1; }
echo "Installing local audit toolchain (optional — CI covers scanning)…"

# ---- Python tools (match the backend env; pip into the active interpreter) ----
for t in semgrep bandit flake8 mypy; do
  python -m "$t" --version >/dev/null 2>&1 || pip install "$t"
done

# ---- jq (JSON parsing for finding counts) ----
have jq || echo "ℹ️ jq not found — counts will show '?'. Install: scoop/winget/brew/apt install jq."

# ---- Gitleaks / Trivy (native binaries; CI runs them regardless) ----
have gitleaks || echo "ℹ️ gitleaks not found — CI workflow covers it. Local: brew/scoop install gitleaks."
have trivy    || echo "ℹ️ trivy not found — CI workflow covers it. Local: brew/scoop install trivy."

# ---- CodeQL: CI only ----
have codeql   || echo "ℹ️ CodeQL runs in CI (.github/workflows/audit.yml) — no local install needed."

# ---- JS/TS tools are project-local in voter-app/ (already present after npm ci) ----
if [ -f voter-app/package.json ]; then
  ( cd voter-app && npm ls eslint >/dev/null 2>&1 ) || echo "ℹ️ Run 'npm install' in voter-app/ for eslint/tsc."
fi

echo "✅ Done. Run: ./scripts/audit.sh   (or --security / --quality / --changed)"
