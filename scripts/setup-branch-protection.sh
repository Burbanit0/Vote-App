#!/usr/bin/env bash
# ── Vote Lab — Branch protection setup ────────────────────────────────────────
# Usage:
#   bash scripts/setup-branch-protection.sh [main|develop|polity|polity-ui|all] [GH_TOKEN]
#   bash scripts/setup-branch-protection.sh              # main and develop, gh CLI
#   bash scripts/setup-branch-protection.sh develop      # develop only, gh CLI
#   bash scripts/setup-branch-protection.sh all <TOKEN>  # main and develop, curl + token
#   bash scripts/setup-branch-protection.sh polity-ui    # one Polity branch, gh CLI
#
# `all` means main and develop only: polity and polity-ui are protected one at a time,
# on purpose, each when its branch exists and its checks are known to report there.
#
# Get a token: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo (or Administration for fine-grained tokens)
#
# Install gh CLI on Windows: winget install --id GitHub.cli --accept-source-agreements
# Then: gh auth login
#
# Required-status-check contexts below are the literal `name:` of each job —
# GitHub matches branch protection against that string, not against a stable
# ID. Renaming a job in any of these workflows must come with an update here
# in the same PR, or protection silently waits forever on a check that no
# longer reports under the old name.

set -euo pipefail

OWNER="Burbanit0"
REPO="Vote-App"
TARGET="${1:-all}"
TOKEN="${2:-}"

# ── Helper: call GitHub API ────────────────────────────────────────────────────
api_call() {
  local method="$1"
  local endpoint="$2"
  local body="$3"

  if command -v gh &>/dev/null && [ -z "$TOKEN" ]; then
    # Use gh CLI (recommended — handles auth automatically)
    echo "$body" | gh api -X "$method" "$endpoint" -H "Accept: application/vnd.github+json" --input -
  elif [ -n "$TOKEN" ]; then
    # Fallback: curl with personal access token
    curl -s -X "$method" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -H "Content-Type: application/json" \
      "https://api.github.com/$endpoint" \
      -d "$body"
  else
    echo "❌ Neither 'gh' CLI nor a GitHub token was found."
    echo ""
    echo "Option A — Install gh CLI (Windows):"
    echo "  winget install --id GitHub.cli --accept-source-agreements"
    echo "  Open a NEW terminal, then: gh auth login"
    echo "  Then re-run this script."
    echo ""
    echo "Option B — Use a personal access token:"
    echo "  bash scripts/setup-branch-protection.sh all <YOUR_GITHUB_TOKEN>"
    echo ""
    echo "Option C — Configure manually via GitHub UI:"
    echo "  Settings → Branches → Add branch ruleset"
    echo "  See CONTRIBUTING.md for the exact settings."
    exit 1
  fi
}

# Same required checks for both branches — main will need everything develop
# needs once a real develop→main release resumes.
#
# Backend CI / Frontend CI / E2E / OpenAPI Contract used to be excluded here:
# each was scoped by a `paths:` filter at the workflow-trigger level, and a
# required check that never even creates a check run (because its workflow
# never triggered) blocks the PR forever — confirmed live when PR #205 (a
# branch-policy.yml + CONTRIBUTING.md fix) got stuck exactly this way. Rather
# than leave them out permanently, each of those 4 workflows now moves the
# `paths:` filter into a job-level `changes` gate (dorny/paths-filter) instead
# of the trigger: the workflow always fires, so the check run always exists,
# and the real job just reports "skipped" (which GitHub treats as passing)
# when nothing relevant changed. That's what makes them safe to require below.
#
# Still excluded, and still for the reason PR #205 taught: mutation-testing.yml
# never runs on pull_request at all (push-to-develop/schedule/dispatch only —
# see its own header comment), so a required check under either of its job
# names would block every PR forever.
REQUIRED_CONTEXTS='[
      "Validate branch source and naming",
      "Semgrep SAST",
      "Secret Scan",
      "Dependencies, Containers & Misconfig",
      "Code Quality (dead code, duplication & complexity)",
      "Dependency Review",
      "CodeQL (javascript-typescript)",
      "CodeQL (python)",
      "Backend: Tests + Coverage + Security",
      "Frontend: Tests + Coverage + Security",
      "Playwright E2E",
      "Playwright/Docker image version sync",
      "Generated artifacts in sync",
      "CI health check"
    ]'

# The high-risk review hold (.github/workflows/human-review.yml) posts this status
# on every PR to polity and develop, red until the owner has reviewed a PR that
# touches a path .mergify.yml protects. Required on those two branches only: it
# never reports on PRs to main or polity-ui, and a required check that never
# reports blocks every PR forever (the PR #205 lesson above).
REVIEW_GATE="High-risk review gate"

# Requiring the gate before the workflow that posts it is live blocks every PR,
# including the one that would bring the workflow in. PRs to a branch run that
# branch's human-review.yml (pull_request_target); `/reviewed` runs develop's
# (issue_comment always runs from the default branch). So both must post it.
require_gate_workflow() {
  local branch workflow
  for branch in develop "$1"; do
    # Fetch first, then search: piping curl into `grep -q` lets grep exit on the
    # first match, curl then dies writing to the closed pipe (exit 23), and
    # pipefail turns a found gate into a false "not posted yet".
    if ! workflow=$(curl -fsSL "https://raw.githubusercontent.com/${OWNER}/${REPO}/${branch}/.github/workflows/human-review.yml"); then
      echo "❌  could not fetch ${branch}'s human-review.yml (missing on that branch, or a network error)."
      exit 1
    fi
    if ! grep -qF "$REVIEW_GATE" <<< "$workflow"; then
      echo "❌  ${branch}'s human-review.yml doesn't post '${REVIEW_GATE}' yet: merge it there first,"
      echo "    or every PR to '$1' would wait forever on a status nothing posts."
      exit 1
    fi
  done
}

# Requiring "CI health check" on a branch before that branch's ci-health.yml
# runs on PRs to it blocks every PR forever (the PR #205 lesson above). PRs run
# the workflow from their own merge commit, so the branch's copy is the one that
# must list it under pull_request.
require_ci_health_on() {
  local workflow
  if ! workflow=$(curl -fsSL "https://raw.githubusercontent.com/${OWNER}/${REPO}/$1/.github/workflows/ci-health.yml"); then
    echo "❌  could not fetch $1's ci-health.yml (missing on that branch, or a network error)."
    exit 1
  fi
  if ! awk '/^  pull_request:/{f=1} f && /branches:/{print; exit}' <<< "$workflow" | grep -qE "branches: \[(.*[ ,])?$1([ ,].*)?\]"; then
    echo "❌  $1's ci-health.yml doesn't run on PRs to $1 yet: merge that first,"
    echo "    or every PR to '$1' would wait forever on 'CI health check'."
    exit 1
  fi
}

# The required-contexts list for one branch, as compact JSON: the one place it is
# decided, read both by the protect_* functions below and by
# scripts/check_ci_health.py (--print-contexts), so the drift check can never
# expect something other than what this script applies.
#   main:      REQUIRED_CONTEXTS.
#   develop:   + the review gate.
#   polity:    + the review gate. "CI health check" too, now that ci-health.yml
#              runs on PRs to polity.
#   polity-ui: less "CI health check": ci-health.yml doesn't run on PRs to it,
#              and a required check that never reports blocks every PR
#              forever (the PR #205 lesson above).
# Computed here, not at the top, so the main target never needs jq.
contexts_for() {
  case "$1" in
    main)           printf '%s' "$REQUIRED_CONTEXTS" | jq -c . ;;
    develop|polity) printf '%s' "$REQUIRED_CONTEXTS" | jq -c --arg g "$REVIEW_GATE" '. + [$g]' ;;
    polity-ui)      printf '%s' "$REQUIRED_CONTEXTS" | jq -c 'map(select(. != "CI health check"))' ;;
    *) echo "contexts_for: unknown branch '$1'" >&2; return 1 ;;
  esac
}

protect_polity_branch() {
  local branch="$1"
  local POLITY_CONTEXTS
  if [ "$branch" = polity ]; then
    require_gate_workflow polity
    require_ci_health_on polity
  fi
  POLITY_CONTEXTS=$(contexts_for "$branch")
  echo "Protecting '${branch}'..."
  api_call PUT "repos/${OWNER}/${REPO}/branches/${branch}/protection" "{
    \"required_status_checks\": {
      \"strict\": true,
      \"contexts\": ${POLITY_CONTEXTS}
    },
    \"enforce_admins\": false,
    \"required_pull_request_reviews\": {
      \"required_approving_review_count\": 0,
      \"dismiss_stale_reviews\": false
    },
    \"restrictions\": null,
    \"required_linear_history\": false,
    \"allow_force_pushes\": false,
    \"allow_deletions\": false
  }"
  echo "✅  '${branch}' protected."
}

protect_main() {
  echo "Protecting 'main'..."
  api_call PUT "repos/${OWNER}/${REPO}/branches/main/protection" "{
    \"required_status_checks\": {
      \"strict\": true,
      \"contexts\": ${REQUIRED_CONTEXTS}
    },
    \"enforce_admins\": true,
    \"required_pull_request_reviews\": {
      \"required_approving_review_count\": 1,
      \"dismiss_stale_reviews\": true,
      \"require_last_push_approval\": true
    },
    \"restrictions\": null,
    \"required_linear_history\": true,
    \"allow_force_pushes\": false,
    \"allow_deletions\": false
  }"
  echo "✅  'main' protected."
}

protect_develop() {
  local DEVELOP_CONTEXTS
  require_gate_workflow develop
  DEVELOP_CONTEXTS=$(contexts_for develop)
  echo "Protecting 'develop'..."
  api_call PUT "repos/${OWNER}/${REPO}/branches/develop/protection" "{
    \"required_status_checks\": {
      \"strict\": true,
      \"contexts\": ${DEVELOP_CONTEXTS}
    },
    \"enforce_admins\": false,
    \"required_pull_request_reviews\": {
      \"required_approving_review_count\": 0,
      \"dismiss_stale_reviews\": false
    },
    \"restrictions\": null,
    \"required_linear_history\": false,
    \"allow_force_pushes\": false,
    \"allow_deletions\": false
  }"
  echo "✅  'develop' protected."
}

# Print a branch's required contexts and exit, touching nothing (for
# scripts/check_ci_health.py's drift check): --print-contexts <branch>.
if [ "$TARGET" = --print-contexts ]; then
  contexts_for "${2:?usage: $0 --print-contexts <main|develop|polity|polity-ui>}"
  exit
fi

echo "🔒 Setting up branch protection for ${OWNER}/${REPO} (target: ${TARGET})..."
echo ""

case "$TARGET" in
  main)    protect_main ;;
  develop) protect_develop ;;
  polity|polity-ui) protect_polity_branch "$TARGET" ;;
  all)     protect_main; echo ""; protect_develop ;;
  *) echo "❌ Unknown target '$TARGET' — use main, develop, polity, polity-ui, or all (= main and develop)"; exit 1 ;;
esac

echo ""
echo "🎉 Branch protection configured!"
echo ""
echo "Note: a required check only appears as satisfiable in the GitHub UI"
echo "      after at least one PR has triggered that workflow."
