#!/usr/bin/env bash
# ── Vote Lab — Branch protection setup ─────────────────────────────────────
# Run once as admin (requires gh CLI authenticated with repo admin rights):
#   bash scripts/setup-branch-protection.sh
#
# The script sets up branch protection rules for 'main' and 'develop'
# so that the CI workflow "Branch Policy / validate-source" must pass
# before any merge is allowed.

set -euo pipefail

OWNER="Burbanit0"
REPO="Vote-App"

echo "🔒 Setting up branch protection for ${OWNER}/${REPO}..."
echo ""

# ── Protect: main ─────────────────────────────────────────────────────────
# Rules:
#   - Only 'develop' can merge (enforced by branch-policy.yml CI check)
#   - Require the "Branch Policy" check to pass
#   - Require the frontend + backend CI checks to pass
#   - No direct push for anyone (including admins)
#   - Require PR + at least 1 approval
#   - No force push, no deletion

echo "Protecting 'main'..."
gh api -X PUT "repos/${OWNER}/${REPO}/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
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
  "allow_deletions": false,
  "block_creations": false
}
JSON

echo "✅  'main' protected."
echo ""

# ── Protect: develop ──────────────────────────────────────────────────────
# Rules:
#   - Only feature/*, fix/*, hotfix/*, etc. can merge (enforced by CI)
#   - Require the "Branch Policy" check to pass
#   - Require CI checks to pass
#   - No direct push
#   - PR required, no approval mandatory (solo project — adjust as needed)

echo "Protecting 'develop'..."
gh api -X PUT "repos/${OWNER}/${REPO}/branches/develop/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
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
    "dismiss_stale_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false
}
JSON

echo "✅  'develop' protected."
echo ""

echo "🎉 Branch protection configured."
echo ""
echo "What's enforced:"
echo "  main   ← develop only  (CI + 1 approval + enforce_admins)"
echo "  develop ← feature/* fix/* hotfix/* refactor/* chore/* docs/* test/* ci/* perf/* (CI)"
echo ""
echo "Next steps:"
echo "  1. Open a PR to validate the 'Branch Policy' check appears"
echo "  2. Once visible, it will be required automatically"
