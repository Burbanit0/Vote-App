#!/usr/bin/env bash
# Generated doc blocks (S5.4): documentation that restates facts owned by code carries a
# cog block that renders them from the code. This fails when a block and the code
# disagree -- the doc drifted, or someone edited generated text by hand.
#
#   ./scripts/check_generated_docs.sh            # check (what CI runs)
#   ./scripts/check_generated_docs.sh --update   # regenerate the blocks in place
#
# Run from the repository root. Needs cogapp (fast_api_voter/requirements-dev.txt) and
# the backend importable: the blocks import from fast_api_voter/api.
set -euo pipefail

DOCS=(
  docs/plan/polity/polity-llm-reference.md
)

PYTHON="${PYTHON:-python}"
if [[ "${1:-}" == "--update" ]]; then
  "$PYTHON" -m cogapp -r -I fast_api_voter "${DOCS[@]}"
else
  "$PYTHON" -m cogapp --check -I fast_api_voter "${DOCS[@]}"
fi
