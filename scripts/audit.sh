#!/usr/bin/env bash
#
# audit.sh — security + quality audit for Vote-App (FastAPI backend + React/Vite frontend).
# Adapted from the generic audit-kit to this repo's real layout and gates.
#
# Philosophy: deterministic tools scan; their machine-readable output lands in
# ./audit-reports/. Claude reads ONLY audit-reports/SUMMARY.md (+ a detail file
# per finding), never the whole codebase — keeps token usage minimal.
#
# Scope note: the project's BLOCKING gates already live in CI + the local commands
# (flake8, mypy, pytest, eslint, tsc, bandit, pip-audit). This script is a
# SUPPLEMENTARY pass whose new value is the SAST / secret / CVE scanners the repo
# doesn't otherwise run locally (Semgrep, Gitleaks, Trivy). Everything degrades
# gracefully when a tool isn't installed.
#
# Usage:
#   ./scripts/audit.sh              # full audit
#   ./scripts/audit.sh --security   # security scanners only
#   ./scripts/audit.sh --quality    # project linters/types only
#   ./scripts/audit.sh --changed    # only files changed vs develop (fast, for hooks)
#
set -uo pipefail

# ---------- config (override via env) ----------
REPORT_DIR="audit-reports"
SUMMARY="$REPORT_DIR/SUMMARY.md"
PY_DIRS="${PY_DIRS:-flask_voter_app}"            # FastAPI backend (name is historical)
PY_PKG="${PY_PKG:-flask_voter_app/api}"          # the typed/tested package
TS_DIR="${TS_DIR:-voter-app}"                    # React/Vite frontend (holds package.json)
BASE_BRANCH="${BASE_BRANCH:-develop}"            # this repo integrates on develop
MODE="full"
CHANGED_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --fast)     MODE="fast" ;;
    --security) MODE="security" ;;
    --quality)  MODE="quality" ;;
    --changed)  CHANGED_ONLY=1; MODE="fast" ;;
  esac
done

mkdir -p "$REPORT_DIR"
: > "$SUMMARY"
have()    { command -v "$1" >/dev/null 2>&1; }                 # binary on PATH
have_py() { python -m "$1" --version >/dev/null 2>&1; }         # python module (Windows-friendly)
section() { echo -e "\n## $1\n" >> "$SUMMARY"; echo "▶ $1"; }
note()    { echo "$1" >> "$SUMMARY"; }
# jq is optional: count() echoes the jq result or "?" when jq is missing.
count()   { if have jq; then jq "$1" "$2" 2>/dev/null || echo "?"; else echo "?"; fi; }

# Resolve changed file set (for hook / fast incremental runs)
CHANGED_FILES=""
if [ "$CHANGED_ONLY" -eq 1 ]; then
  BASE="$(git merge-base HEAD "origin/$BASE_BRANCH" 2>/dev/null || echo HEAD~1)"
  CHANGED_FILES="$(git diff --name-only "$BASE" 2>/dev/null | tr '\n' ' ')"
  [ -z "$CHANGED_FILES" ] && CHANGED_FILES="$(git diff --name-only --cached | tr '\n' ' ')"
fi

echo "# Audit report — $(date '+%Y-%m-%d %H:%M')" >> "$SUMMARY"
note "Mode: \`$MODE\`  |  Changed-only: \`$CHANGED_ONLY\`  |  Backend: \`$PY_DIRS\`  |  Frontend: \`$TS_DIR\`"
have jq || note "_(jq not installed — finding counts show \`?\`; install jq for numbers.)_"

# =====================================================================
# SECURITY  (the supplementary value: SAST / secrets / CVEs)
# =====================================================================
if [ "$MODE" != "quality" ]; then

  # --- Secrets: Gitleaks ---
  section "Secrets (Gitleaks)"
  if have gitleaks; then
    if gitleaks detect --no-banner --redact \
        --report-format json --report-path "$REPORT_DIR/gitleaks.json" 2>/dev/null; then
      note "✅ No secrets detected."
    else
      note "🔴 $(count 'length' "$REPORT_DIR/gitleaks.json") potential secret(s). See \`$REPORT_DIR/gitleaks.json\`."
    fi
  else
    note "⚠️ gitleaks not installed — runs in CI (.github/workflows/audit.yml)."
  fi

  # --- SAST: Semgrep (multi-lang security rulesets) ---
  section "SAST (Semgrep)"
  if have semgrep; then
    SEMGREP_TARGET="."
    [ -n "$CHANGED_FILES" ] && SEMGREP_TARGET="$CHANGED_FILES"
    semgrep --config=p/python --config=p/javascript --config=p/react \
            --config=p/security-audit --config=p/secrets \
            --config=p/sql-injection --config=p/owasp-top-ten \
            --sarif --output "$REPORT_DIR/semgrep.sarif" \
            --json --output "$REPORT_DIR/semgrep.json" \
            --metrics=off --quiet $SEMGREP_TARGET 2>/dev/null
    if [ -f "$REPORT_DIR/semgrep.json" ]; then
      note "Findings: 🔴 $(count '[.results[]|select(.extra.severity=="ERROR")]|length' "$REPORT_DIR/semgrep.json") error · 🟠 $(count '[.results[]|select(.extra.severity=="WARNING")]|length' "$REPORT_DIR/semgrep.json") warning. See \`$REPORT_DIR/semgrep.sarif\`."
      if have jq; then
        jq -r '.results[]|select(.extra.severity=="ERROR")|"- \(.path):\(.start.line) — \(.check_id)"' \
          "$REPORT_DIR/semgrep.json" 2>/dev/null | head -30 >> "$SUMMARY"
      fi
    fi
  else
    note "⚠️ semgrep not installed — runs in CI. Local: \`pip install semgrep\`."
  fi

  # --- Dependencies + containers + misconfig: Trivy ---
  section "Dependencies, containers & misconfig (Trivy)"
  if have trivy; then
    trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
         --format json --output "$REPORT_DIR/trivy.json" --quiet . 2>/dev/null
    [ -f "$REPORT_DIR/trivy.json" ] && \
      note "🔴 $(count '[.Results[]?.Vulnerabilities[]?]|length' "$REPORT_DIR/trivy.json") HIGH/CRITICAL vuln(s). See \`$REPORT_DIR/trivy.json\`."
  else
    note "⚠️ trivy not installed — runs in CI."
  fi

  # --- Python-specific SAST: Bandit (same invocation as backend CI) ---
  section "Python SAST (Bandit)"
  if have_py bandit; then
    python -m bandit -r "$PY_PKG" -ll --skip B104,B311 \
      -f json -o "$REPORT_DIR/bandit.json" -q 2>/dev/null
    note "🔴 $(count '[.results[]|select(.issue_severity=="HIGH")]|length' "$REPORT_DIR/bandit.json") HIGH-severity issue(s). See \`$REPORT_DIR/bandit.json\`."
  else
    note "⚠️ bandit not installed — \`pip install bandit\` (already in backend CI)."
  fi

  # --- CodeQL: deep semantic analysis ---
  if [ "$MODE" = "full" ] || [ "$MODE" = "security" ]; then
    section "Deep SAST (CodeQL)"
    note "ℹ️ CodeQL needs GitHub Advanced Security (private repo) or a public repo — disabled while this repo is private. Semgrep above is the cross-language SAST in the meantime."
  fi
fi

# =====================================================================
# QUALITY / LINTING  (mirrors the repo's real gates; non-duplicative configs)
# =====================================================================
if [ "$MODE" != "security" ]; then

  # --- Python lint: Flake8 (project .flake8 — E9 + pyflakes, the blocking gate) ---
  section "Python lint (Flake8)"
  if have_py flake8; then
    python -m flake8 --config="$PY_DIRS/.flake8" "$PY_DIRS" > "$REPORT_DIR/flake8.txt" 2>&1
    note "Issues: $(grep -c ':' "$REPORT_DIR/flake8.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/flake8.txt\`."
  else
    note "⚠️ flake8 not installed — \`pip install flake8\`."
  fi

  # --- Python types: mypy (strict, on api/, with the project's config) ---
  section "Python types (mypy --config-file mypy.ini)"
  if have_py mypy; then
    ( cd "$PY_DIRS" && python -m mypy api/ --config-file mypy.ini ) \
      > "$REPORT_DIR/mypy.txt" 2>&1
    note "Type errors: $(grep -c 'error:' "$REPORT_DIR/mypy.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/mypy.txt\`."
  else
    note "⚠️ mypy not installed — \`pip install mypy\`."
  fi

  # --- TS/React: ESLint + tsc (frontend lives in $TS_DIR) ---
  if [ -f "$TS_DIR/package.json" ]; then
    section "TypeScript lint (ESLint)"
    if ( cd "$TS_DIR" && npx --no-install eslint --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install eslint . --format json -o "../$REPORT_DIR/eslint.json" 2>/dev/null )
      note "Issues: $(count '[.[].messages[]]|length' "$REPORT_DIR/eslint.json"). See \`$REPORT_DIR/eslint.json\`."
    else
      note "⚠️ eslint not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi
    section "TypeScript types (tsc --noEmit)"
    if ( cd "$TS_DIR" && npx --no-install tsc --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install tsc --noEmit > "../$REPORT_DIR/tsc.txt" 2>&1 )
      note "Type errors: $(grep -c 'error TS' "$REPORT_DIR/tsc.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/tsc.txt\`."
    fi
  else
    note "⚠️ No package.json in $TS_DIR/."
  fi
fi

# =====================================================================
# WRAP-UP
# =====================================================================
echo -e "\n---\n" >> "$SUMMARY"
note "**Reports in \`$REPORT_DIR/\`.** Feed \`$SUMMARY\` to Claude first;"
note "open individual JSON/SARIF/txt files only for the findings you triage."

echo ""
echo "✅ Done. Summary → $SUMMARY"
