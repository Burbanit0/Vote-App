#!/usr/bin/env bash
# Generated doc blocks (S5.4): documentation that restates facts owned by code carries a
# cog block that renders them from the code. This fails when a block and the code
# disagree -- the doc drifted, or someone edited generated text by hand.
#
#   ./scripts/check_generated_docs.sh            # check (what CI runs)
#   ./scripts/check_generated_docs.sh --update   # regenerate the blocks in place
#   ./scripts/check_generated_docs.sh [--update] DOC...   # only these docs (fast-gate)
#
# Run from the repository root. Needs cogapp (fast_api_voter/requirements-dev.txt) and
# the backend importable: the blocks import from fast_api_voter/api, and the CI
# counts from scripts/ci_facts.py.
set -euo pipefail

# Keep in step with openapi-contract.yml's path filter (scripts/tests/test_ci_facts.py
# checks it): a doc the filter misses never gets checked on the PR that drifts it.
DOCS=(
  docs/plan/polity/polity-llm-reference.md
  CONTRIBUTING.md
  .claude/skills/voter-ci/SKILL.md
)

PYTHON="${PYTHON:-python}"
MODE=(--check)
if [[ "${1:-}" == "--update" ]]; then MODE=(-r); shift; fi
if [ "$#" -gt 0 ]; then DOCS=("$@"); fi
"$PYTHON" -m cogapp "${MODE[@]}" -I fast_api_voter -I scripts "${DOCS[@]}"
