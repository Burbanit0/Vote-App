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
PY_DIRS="${PY_DIRS:-fast_api_voter}"            # FastAPI backend (name is historical)
PY_PKG="${PY_PKG:-fast_api_voter/api}"          # the typed/tested package
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

  # --- Secrets, verified-active only: TruffleHog (Lot 9, PLAN_SOLIDITE_TECHNIQUE.md
  # — complements Gitleaks above: live credential verification against the
  # provider's own API, not just a regex match. Output is NDJSON, one finding
  # per line, hence `wc -l` rather than the jq-based `count` helper.) ---
  section "Secrets — verified-active only (TruffleHog, informational)"
  if have trufflehog; then
    trufflehog filesystem --no-update --results=verified --json \
      "$PY_DIRS/api" "$PY_DIRS/scripts" "$TS_DIR/src" "$TS_DIR/tests" scripts docs \
      > "$REPORT_DIR/trufflehog.json" 2> "$REPORT_DIR/trufflehog.log"
    TH_COUNT=$(wc -l < "$REPORT_DIR/trufflehog.json" 2>/dev/null | tr -d ' ')
    if [ "${TH_COUNT:-0}" = "0" ]; then
      note "✅ No verified-active secrets. See \`$REPORT_DIR/trufflehog.json\` (empty)."
    else
      note "🔴 $TH_COUNT verified-active secret(s). See \`$REPORT_DIR/trufflehog.json\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §9."
    fi
  else
    note "⚠️ trufflehog not installed — runs in CI. Local: https://github.com/trufflesecurity/trufflehog#installation."
  fi

  # --- SAST: Semgrep (multi-lang security rulesets) ---
  section "SAST (Semgrep)"
  if have semgrep; then
    SEMGREP_TARGET="."
    [ -n "$CHANGED_FILES" ] && SEMGREP_TARGET="$CHANGED_FILES"
    semgrep --config=p/python --config=p/javascript --config=p/react \
            --config=p/security-audit --config=p/secrets \
            --config=p/sql-injection --config=p/owasp-top-ten \
            --sarif-output="$REPORT_DIR/semgrep.sarif" \
            --json-output="$REPORT_DIR/semgrep.json" \
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

  # --- Dependency vulnerabilities, second opinion: OSV-Scanner (Lot 9,
  # PLAN_SOLIDITE_TECHNIQUE.md — a different vuln DB than Trivy above; see
  # docs/exploration/ for the measured overlap). Explicit -L per lockfile
  # rather than `-r .`: a recursive directory scan silently finds zero
  # package sources when run from inside a git *worktree* (confirmed
  # reproducible — the same lockfiles are found fine via -L, or via -r in a
  # plain non-worktree checkout; likely irrelevant to CI's normal checkout,
  # but -L sidesteps it either way and is faster). --data-source native
  # avoids a deps.dev gRPC resolution call that timed out in this sandboxed
  # dev environment (plain HTTPS to both osv.dev and deps.dev is reachable —
  # the gRPC transport specifically was the problem); detection verified
  # against known-CVE pins (urllib3==1.26.4, Jinja2==2.4.1 -> 18 real
  # findings each) before trusting a clean result on this repo's real deps.
  section "Dependency vulnerabilities — second opinion (OSV-Scanner, informational)"
  if have osv-scanner; then
    osv-scanner scan source \
      -L "$PY_DIRS/requirements.txt" -L "$PY_DIRS/requirements-dev.txt" \
      -L "$TS_DIR/package-lock.json" \
      --data-source native \
      --format json --output-file "$REPORT_DIR/osv-scanner.json" >/dev/null 2>&1
    note "$(count '[.results[]?.packages[]?.vulnerabilities[]?]|length' "$REPORT_DIR/osv-scanner.json") vulnerability finding(s) (any severity). See \`$REPORT_DIR/osv-scanner.json\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §9."
  else
    note "⚠️ osv-scanner not installed — runs in CI. Local: download a release binary from https://github.com/google/osv-scanner/releases."
  fi

  # --- Malicious packages (not just known CVEs): GuardDog (Lot 9,
  # PLAN_SOLIDITE_TECHNIQUE.md — typosquatting, hostile install scripts; a
  # blind spot of pip-audit/Trivy/OSV-Scanner above, which only see already-
  # disclosed CVEs). NOT in requirements-dev.txt: guarddog pins
  # pygit2<1.19, and pygit2 only shipped cp314 wheels from 1.20.0 onward
  # (verified against PyPI's file index) — installing it into this repo's
  # actual 3.14-pinned backend venv would force a from-source pygit2 build
  # (needs libgit2 headers, not guaranteed present) or fail outright.
  # `have` (PATH binary), not `have_py`, matches the Semgrep pattern above:
  # install guarddog into its own venv (Python <=3.13) or via `pipx`, not
  # into fast_api_voter/.venv. Scoped to requirements.txt (production) only
  # for the local run — requirements-dev.txt roughly doubles the wall time
  # for lower-priority (non-shipped) risk; CI's own job covers both.
  # guarddog's requirements parser silently drops any line whose inline `#`
  # comment follows extra whitespace (this repo's convention for documenting
  # *why* a version is pinned, e.g. a CVE ID -- see any line of
  # requirements.txt) -- verified: 11/15 lines of this repo's real
  # requirements.txt were silently ignored before this fix. Feed it a
  # comment-stripped TEMP copy instead of editing the real file (those
  # comments are load-bearing documentation, not scanned).
  section "Malicious packages (GuardDog, informational)"
  if have guarddog; then
    GUARDDOG_TMP="$(mktemp)"
    sed -E 's/[[:space:]]+#.*$//' "$PY_DIRS/requirements.txt" > "$GUARDDOG_TMP"
    guarddog pypi verify "$GUARDDOG_TMP" --output-format json \
      > "$REPORT_DIR/guarddog-pypi.json" 2> "$REPORT_DIR/guarddog-pypi.log"
    rm -f "$GUARDDOG_TMP"
    note "See \`$REPORT_DIR/guarddog-pypi.json\` (\`$REPORT_DIR/guarddog-pypi.log\` for any requirements lines it still couldn't parse). Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §9. Slow (real per-package download + static analysis, not a local pattern match) — expect at least a couple of minutes even for the ~15 production deps."
  else
    note "⚠️ guarddog not installed — runs in CI. Local (Python <=3.13 only, see comment above): \`pip install guarddog\` or \`pipx install guarddog\`."
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

  # --- License compliance: production dependencies (same gate as backend CI) ---
  section "Python license compliance — production deps (same invocation as backend CI, gating)"
  if [ -x "$PY_DIRS/scripts/check_license_compliance.sh" ] && have python3; then
    if bash "$PY_DIRS/scripts/check_license_compliance.sh" > "$REPORT_DIR/license-py.txt" 2>&1; then
      note "✅ All production dependency licenses allow-listed. See \`$REPORT_DIR/license-py.txt\`."
    else
      note "🔴 A production dependency license is NOT allow-listed — this gates CI. See \`$REPORT_DIR/license-py.txt\`. Not a Lot-6-informational item; see PLAN_SOLIDITE_TECHNIQUE.md §6.7."
    fi
  else
    note "⚠️ $PY_DIRS/scripts/check_license_compliance.sh not found or not executable."
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

    # --- TS/React cognitive complexity + bug patterns: eslint-plugin-sonarjs ---
    section "TypeScript cognitive complexity & bug patterns (sonarjs, informational)"
    if [ -f "$TS_DIR/eslint.sonarjs.config.js" ] && ( cd "$TS_DIR" && npx --no-install eslint --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install eslint -c eslint.sonarjs.config.js . --format json -o "../$REPORT_DIR/sonarjs.json" 2>/dev/null )
      note "Findings: $(count '[.[].messages[]]|length' "$REPORT_DIR/sonarjs.json"). See \`$REPORT_DIR/sonarjs.json\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §6.6 (dominated by cognitive-load style suggestions, not correctness bugs)."
    else
      note "⚠️ eslint.sonarjs.config.js not found in $TS_DIR (run \`npm install\` there)."
    fi
  else
    note "⚠️ No package.json in $TS_DIR/."
  fi

  # =====================================================================
  # DEAD CODE, DUPLICATION & COMPLEXITY — informational only (see
  # CODE_AUDIT.md). None of these gate the script or CI: they're new (added
  # alongside the audit) and the repo hasn't done its first cleanup pass yet.
  # Once findings settle near zero, promote them to blocking gates like the
  # linters above.
  # =====================================================================

  # --- Python dead code: vulture ---
  section "Python dead code (vulture, informational)"
  if have_py vulture; then
    ( cd "$PY_DIRS" && python -m vulture api/ .vulture_whitelist.py --config pyproject.toml ) \
      > "$REPORT_DIR/vulture.txt" 2>&1
    note "Findings: $(grep -c ':' "$REPORT_DIR/vulture.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/vulture.txt\`. Not gated — see CODE_AUDIT.md."
  else
    note "⚠️ vulture not installed — \`pip install vulture\` (in requirements-dev.txt)."
  fi

  # --- Python modernization: refurb ---
  section "Python modernization (refurb, informational)"
  if have_py refurb; then
    ( cd "$PY_DIRS" && python -m refurb api/ ) \
      > "$REPORT_DIR/refurb.txt" 2>&1
    note "Findings: $(grep -c '^api/' "$REPORT_DIR/refurb.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/refurb.txt\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §6.3."
  else
    note "⚠️ refurb not installed — \`pip install refurb\` (in requirements-dev.txt)."
  fi

  # --- Python performance anti-patterns: perflint (pylint plugin) ---
  section "Python performance anti-patterns (perflint, informational)"
  if have_py pylint; then
    ( cd "$PY_DIRS" && python -m pylint api/ --ignore=tests ) \
      > "$REPORT_DIR/perflint.txt" 2>&1
    note "Findings: $(grep -cE '^api/.*\(use-|\(loop-|\(dotted-|\(memoryview-|\(unnecessary-|\(incorrect-' "$REPORT_DIR/perflint.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/perflint.txt\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §6.3 (loop-invariant-statement disabled — too noisy at whole-repo scale, see [tool.pylint] in pyproject.toml)."
  else
    note "⚠️ pylint/perflint not installed — \`pip install perflint pylint\` (in requirements-dev.txt)."
  fi

  # --- Python second type-checker opinion: basedpyright ---
  section "Python second type-checker opinion (basedpyright, informational)"
  if have_py basedpyright; then
    ( cd "$PY_DIRS" && python -m basedpyright ) \
      > "$REPORT_DIR/basedpyright.txt" 2>&1
    note "$(grep -m1 -E '^[0-9]+ errors?, [0-9]+ warnings?' "$REPORT_DIR/basedpyright.txt" 2>/dev/null || echo 'see report'). See \`$REPORT_DIR/basedpyright.txt\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §6.2 (baseline is ~32 known pydantic/pyright false positives, not zero)."
  else
    note "⚠️ basedpyright not installed — \`pip install basedpyright\` (in requirements-dev.txt)."
  fi

  # --- Python unused/undeclared deps: deptry ---
  section "Python unused/undeclared deps (deptry, informational)"
  if have_py deptry; then
    ( cd "$PY_DIRS" && python -m deptry . ) \
      > "$REPORT_DIR/deptry.txt" 2>&1
    note "Findings: $(grep -cE 'DEP[0-9]{3}' "$REPORT_DIR/deptry.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/deptry.txt\`. Not gated — see CODE_AUDIT.md."
  else
    note "⚠️ deptry not installed — \`pip install deptry\` (in requirements-dev.txt)."
  fi

  # --- TS/React dead code + unused exports + unused deps: knip ---
  if [ -f "$TS_DIR/package.json" ]; then
    section "TypeScript dead code & unused deps (knip, informational)"
    if ( cd "$TS_DIR" && npx --no-install knip --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install knip --no-progress --reporter json > "../$REPORT_DIR/knip.json" 2>/dev/null )
      note "Unused files: $(count '[.issues[]|select(.files|length>0)]|length' "$REPORT_DIR/knip.json"). See \`$REPORT_DIR/knip.json\`. Not gated — see CODE_AUDIT.md."
    else
      note "⚠️ knip not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi

    # --- TS/React circular imports: madge ---
    section "Circular imports (madge, informational)"
    if ( cd "$TS_DIR" && npx --no-install madge --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install madge --circular --extensions ts,tsx src ) \
        > "$REPORT_DIR/madge.txt" 2>&1
      note "$(grep -m1 '^✖ Found\|^No circular' "$REPORT_DIR/madge.txt" 2>/dev/null || echo 'see report'). See \`$REPORT_DIR/madge.txt\`. Not gated — see CODE_AUDIT.md. Graph image needs graphviz (\`dot\`) installed: \`npx madge --image graph.svg --extensions ts,tsx src\`."
    else
      note "⚠️ madge not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi

    # --- TS/React hardcoded strings & i18n key hygiene: i18next-cli lint ---
    section "TypeScript i18n hardcoded strings (i18next-cli lint, informational)"
    if [ -f "$TS_DIR/i18next.config.ts" ] && ( cd "$TS_DIR" && npx --no-install i18next-cli --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install i18next-cli lint ) \
        > "$REPORT_DIR/i18next-lint.txt" 2>&1
      note "Findings: $(grep -c 'Error: Found hardcoded' "$REPORT_DIR/i18next-lint.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/i18next-lint.txt\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §7 (baseline is dominated by internal method-key literals like \"fptp\"/\"irv\", not user-facing text)."
    else
      note "⚠️ i18next-cli not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi

    # --- TS/React type coverage: type-coverage ---
    section "TypeScript type coverage (type-coverage, informational)"
    if ( cd "$TS_DIR" && npx --no-install type-coverage --version >/dev/null 2>&1 ); then
      ( cd "$TS_DIR" && npx --no-install type-coverage --detail ) \
        > "$REPORT_DIR/type-coverage.txt" 2>&1
      note "$(grep -oE '\([0-9]+ / [0-9]+\) [0-9.]+%' "$REPORT_DIR/type-coverage.txt" 2>/dev/null || echo 'see report'). See \`$REPORT_DIR/type-coverage.txt\`. Not gated — see PLAN_SOLIDITE_TECHNIQUE.md §6.4 (run via project node_modules, not bare \`npx type-coverage\` — the isolated npx cache resolves its own mismatched typescript and crashes)."
    else
      note "⚠️ type-coverage not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi

    # --- License compliance: production dependencies (same gate as frontend CI) ---
    section "TypeScript license compliance — production deps (same invocation as frontend CI, gating)"
    # `--version` alone exits 1 on this tool regardless of success (checked
    # directly) -- detect via the installed binary instead of exit code.
    if [ -x "$TS_DIR/node_modules/.bin/license-checker-rseidelsohn" ]; then
      SELF="$( (cd "$TS_DIR" && node -p "require('./package.json').name") )@$( (cd "$TS_DIR" && node -p "require('./package.json').version") )"
      if ( cd "$TS_DIR" && npx --no-install license-checker-rseidelsohn --production \
            --onlyAllow "MIT;ISC;Apache-2.0;BSD-2-Clause;BSD-3-Clause;BlueOak-1.0.0;MPL-2.0;CC0-1.0;MIT-0;Python-2.0;Unlicense;0BSD;(MIT OR CC0-1.0);MIT AND ISC" \
            --excludePackages "$SELF" ) > "$REPORT_DIR/license-ts.txt" 2>&1; then
        note "✅ All production dependency licenses allow-listed. See \`$REPORT_DIR/license-ts.txt\`."
      else
        note "🔴 A production dependency license is NOT allow-listed — this gates CI. See \`$REPORT_DIR/license-ts.txt\`. Not a Lot-6-informational item; see PLAN_SOLIDITE_TECHNIQUE.md §6.7."
      fi
    else
      note "⚠️ license-checker-rseidelsohn not found in $TS_DIR/node_modules (run \`npm install\` there)."
    fi
  fi

  # --- Cross-language duplication: jscpd ---
  section "Code duplication (jscpd, informational)"
  if have npx; then
    npx --yes jscpd --config .jscpd.json "$PY_PKG" "$TS_DIR/src" \
      --reporters json --output "$REPORT_DIR/jscpd" > "$REPORT_DIR/jscpd.txt" 2>&1
    JSCPD_STATS="$REPORT_DIR/jscpd/jscpd-report.json"
    note "$(count '.statistics.total|"\(.clones) clone(s), \(.duplicatedLines) duplicated line(s) (\((.percentage*100|round)/100)%)"' "$JSCPD_STATS"). Full report: \`$JSCPD_STATS\`. Not gated — see CODE_AUDIT.md."
  else
    note "⚠️ npx not available — can't run jscpd."
  fi

  # --- Python cyclomatic complexity: radon/xenon ---
  section "Python cyclomatic complexity (radon/xenon, informational)"
  if have_py radon; then
    ( cd "$PY_DIRS" && python -m radon cc api/ -e "api/tests/*" -n C -s ) \
      > "$REPORT_DIR/radon.txt" 2>&1
    note "Blocks ranked C or worse: $(grep -c '^\s*[A-Z] ' "$REPORT_DIR/radon.txt" 2>/dev/null || echo 0). See \`$REPORT_DIR/radon.txt\`. Not gated — see CODE_AUDIT.md."
  else
    note "⚠️ radon not installed — \`pip install radon\` (in requirements-dev.txt)."
  fi
  if have_py xenon; then
    # Lenient thresholds (F = worst rank = never fails): this is a report,
    # not a gate, until the backlog in CODE_AUDIT.md is resorbed.
    ( cd "$PY_DIRS" && python -m xenon api/ -e "api/tests/*" -b F -m F -a F ) \
      > "$REPORT_DIR/xenon.txt" 2>&1
    note "See \`$REPORT_DIR/xenon.txt\`. Not gated — see CODE_AUDIT.md."
  else
    note "⚠️ xenon not installed — \`pip install xenon\` (in requirements-dev.txt)."
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
