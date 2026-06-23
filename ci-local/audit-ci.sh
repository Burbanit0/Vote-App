#!/usr/bin/env bash
# Container entrypoint for the local CI Security Audit job (see audit.Dockerfile).
# Runs the three scanners against the COPYed repo at /repo. STRICT posture: every
# scanner GATES — Semgrep findings, Trivy HIGH/CRITICAL, or any Gitleaks secret all
# fail the job. The repo was triaged to strict-clean first; triaged false positives
# live in .gitleaksignore / .trivyignore.yaml, so only NEW problems break the build.
set -uo pipefail
fail=0

echo "===== Semgrep — SAST (gating) ====="
semgrep \
  --config=p/python --config=p/javascript --config=p/react \
  --config=p/security-audit --config=p/secrets \
  --config=p/sql-injection --config=p/owasp-top-ten \
  --metrics=off --error --quiet . \
  || { echo "🔴 Semgrep: finding(s) above — failing the audit job."; fail=1; }

echo ""
echo "===== Trivy — dependencies / containers / misconfig (gating) ====="
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
      --skip-dirs voter-app/node_modules,.claude,graphify-out \
      --ignorefile .trivyignore.yaml --exit-code 1 . \
  || { echo "🔴 Trivy: HIGH/CRITICAL finding(s) above — failing the audit job."; fail=1; }

echo ""
echo "===== Gitleaks — secret scan (BLOCKING) ====="
if gitleaks detect --source=. --no-banner --redact; then
  echo "✅ Gitleaks: no secrets detected."
else
  echo "🔴 Gitleaks: potential secret(s) detected — failing the audit job."
  fail=1
fi

exit "$fail"
