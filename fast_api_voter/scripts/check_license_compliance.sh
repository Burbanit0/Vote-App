#!/usr/bin/env bash
# check_license_compliance.sh — gate production dependency licenses against
# an allow-list (Lot 6.7, PLAN_SOLIDITE_TECHNIQUE.md).
#
# Must run in an ISOLATED venv containing ONLY requirements.txt, not the
# combined dev+prod environment the rest of CI shares: this repo's own dev
# tooling (pylint/refurb for Lot 6.3, semgrep) pulls in GPL/LGPL packages
# that are never distributed with the app — allow-listing them here would
# defeat the point of the check, and running it in-place in the shared venv
# would flag them as false positives every time. Dev-only license risk is a
# separate, much lower-stakes question this check deliberately does not
# answer (see PLAN_SOLIDITE_TECHNIQUE.md §6.7 for the manual sweep that did).
set -euo pipefail

cd "$(dirname "$0")/.."  # fast_api_voter/

VENV_DIR="$(mktemp -d)"
trap 'rm -rf "$VENV_DIR"' EXIT

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt
"$VENV_DIR/bin/pip" install --quiet pip-licenses

# Permissive licenses actually in use by production dependencies today
# (checked 2026-09, 43 packages) — MIT/BSD/Apache/MPL-2.0/PSF-2.0/ISC variants,
# spelled out because pip-licenses doesn't normalize SPDX vs. classifier-text
# forms of the same license (e.g. "MIT" vs. "MIT License").
"$VENV_DIR/bin/pip-licenses" --allow-only="\
MIT;MIT License;MIT-0;\
BSD License;BSD-2-Clause;BSD-3-Clause;3-Clause BSD License;\
Apache Software License;Apache-2.0;Apache License 2.0;\
Apache Software License; MIT License;Apache-2.0 OR BSD-2-Clause;MIT OR Apache-2.0;\
Mozilla Public License 2.0 (MPL 2.0);MPL-2.0;\
PSF-2.0;Python Software Foundation License;\
BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0;\
ISC;Apache-2.0 AND BSD-2-Clause"
