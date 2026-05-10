#!/usr/bin/env bash
# ── Vote Lab — Branch protection setup ────────────────────────────────────────
# Usage:
#   bash scripts/setup-branch-protection.sh               # uses gh CLI
#   bash scripts/setup-branch-protection.sh <GH_TOKEN>    # uses curl + token
#
# Get a token: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo (or Administration for fine-grained tokens)
#
# Install gh CLI on Windows: winget install --id GitHub.cli --accept-source-agreements
# Then: gh auth login

set -euo pipefail

OWNER="Burbanit0"
REPO="Vote-App"
TOKEN="${1:-}"

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
    echo "  bash scripts/setup-branch-protection.sh <YOUR_GITHUB_TOKEN>"
    echo ""
    echo "Option C — Configure manually via GitHub UI:"
    echo "  Settings → Branches → Add branch ruleset"
    echo "  See CONTRIBUTING.md for the exact settings."
    exit 1
  fi
}

echo "🔒 Setting up branch protection for ${OWNER}/${REPO}..."
echo ""

# ── Protect: main ─────────────────────────────────────────────────────────────
echo "Protecting 'main'..."

api_call PUT "repos/${OWNER}/${REPO}/branches/main/protection" '{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Branch Policy / validate-source",
      "Tests + Coverage + Security",
      "Tests frontend",
      "Tests backend"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}'

echo "✅  'main' protected."
echo ""

# ── Protect: develop ──────────────────────────────────────────────────────────
echo "Protecting 'develop'..."

api_call PUT "repos/${OWNER}/${REPO}/branches/develop/protection" '{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Branch Policy / validate-source",
      "Tests frontend",
      "Tests backend"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false
}'

echo "✅  'develop' protected."
echo ""
echo "🎉 Branch protection configured!"
echo ""
echo "Rules applied:"
echo "  main    ← develop only  (requires 1 approval + all CI checks)"
echo "  develop ← feature/* fix/* etc. (requires CI checks)"
echo ""
echo "Note: Status checks only appear in GitHub UI after"
echo "      at least one PR has triggered those workflows."
