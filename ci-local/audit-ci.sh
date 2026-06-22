#!/usr/bin/env bash
# Container entrypoint for the local CI Security Audit job (see audit.Dockerfile).
# Runs the three scanners against the COPYed repo at /repo. Posture mirrors the
# GitHub workflow: Gitleaks BLOCKS on secrets (exit 1); Semgrep + Trivy are
# informational (findings printed, never gating — security is non-blocking here,
# secrets excepted).
set -uo pipefail
fail=0

echo "===== Semgrep — SAST (informational) ====="
semgrep \
  --config=p/python --config=p/javascript --config=p/react \
  --config=p/security-audit --config=p/secrets \
  --config=p/sql-injection --config=p/owasp-top-ten \
  --metrics=off --error --quiet . \
  || echo "⚠️  Semgrep reported findings (informational — review above)."

echo ""
echo "===== Trivy — dependencies / containers / misconfig (informational) ====="
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
      --skip-dirs voter-app/node_modules,.claude,graphify-out --exit-code 0 . \
  || echo "⚠️  Trivy scan reported issues (informational)."

echo ""
echo "===== Gitleaks — secret scan (BLOCKING) ====="
if gitleaks detect --source=. --no-banner --redact; then
  echo "✅ Gitleaks: no secrets detected."
else
  echo "🔴 Gitleaks: potential secret(s) detected — failing the audit job."
  fail=1
fi

exit "$fail"
