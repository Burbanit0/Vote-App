#!/usr/bin/env bash
# scripts/sticky_comment.sh — create or update ONE bot comment on a PR.
#
# A workflow that reports on every push would otherwise pile up a comment per
# run. The comment carries a hidden marker; the first run creates it, later
# runs edit it in place.
#
# Usage: sticky_comment.sh OWNER/REPO PR_NUMBER MARKER BODY_FILE
# Needs GH_TOKEN with pull-requests: write.
set -euo pipefail

repo="$1" pr="$2" marker="<!-- $3 -->" body_file="$4"
body="$(printf '%s\n\n%s\n' "$marker" "$(cat "$body_file")")"

id=$(gh api --paginate "repos/$repo/issues/$pr/comments" \
  --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | startswith(\"$marker\"))) | .id" \
  | head -1)

if [ -n "$id" ]; then
  gh api -X PATCH "repos/$repo/issues/comments/$id" -f body="$body" > /dev/null
  echo "Updated comment $id."
else
  gh api -X POST "repos/$repo/issues/$pr/comments" -f body="$body" > /dev/null
  echo "Created the comment."
fi
