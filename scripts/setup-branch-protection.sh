#!/usr/bin/env bash
# ── Vote Lab — Branch protection setup ────────────────────────────────────────
# Usage:
#   bash scripts/setup-branch-protection.sh [main|develop|all] [GH_TOKEN]
#   bash scripts/setup-branch-protection.sh              # both branches, gh CLI
#   bash scripts/setup-branch-protection.sh develop      # develop only, gh CLI
#   bash scripts/setup-branch-protection.sh all <TOKEN>  # both, curl + token
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
# needs once a real develop→main release resumes. Excluded on purpose:
# - mutation-testing.yml: never runs on pull_request (see CONTRIBUTING.md's
#   workflow table), so a required check under that name would block forever.
# - Backend CI / Frontend CI / E2E / OpenAPI Contract: all scoped by `paths:`
#   to fast_api_voter/**, voter-app/**, or the generated-artifacts set. A PR
#   that touches none of those (docs, CI config, this script) never triggers
#   them, and a required check that never reports blocks the PR forever —
#   confirmed live when PR #205 (a branch-policy.yml + CONTRIBUTING.md fix)
#   got stuck exactly this way. They still gate normally on the PRs that do
#   trigger them; they're just not in branch protection's required list.
REQUIRED_CONTEXTS='[
      "Validate branch source and naming",
      "Semgrep SAST",
      "Secret Scan",
      "Dependencies, Containers & Misconfig",
      "Code Quality (dead code, duplication & complexity)"
    ]'

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
  echo "Protecting 'develop'..."
  api_call PUT "repos/${OWNER}/${REPO}/branches/develop/protection" "{
    \"required_status_checks\": {
      \"strict\": true,
      \"contexts\": ${REQUIRED_CONTEXTS}
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

echo "🔒 Setting up branch protection for ${OWNER}/${REPO} (target: ${TARGET})..."
echo ""

case "$TARGET" in
  main)    protect_main ;;
  develop) protect_develop ;;
  all)     protect_main; echo ""; protect_develop ;;
  *) echo "❌ Unknown target '$TARGET' — use main, develop, or all"; exit 1 ;;
esac

echo ""
echo "🎉 Branch protection configured!"
echo ""
echo "Note: a required check only appears as satisfiable in the GitHub UI"
echo "      after at least one PR has triggered that workflow."
