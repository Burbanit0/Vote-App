#!/usr/bin/env bash
# scripts/check_python_lockfile_freshness.sh — the compiled lockfiles must
# still match the direct pins in requirements.txt/requirements-dev.txt.
#
# fast_api_voter/requirements.lock.txt and requirements-dev.lock.txt (added
# for real transitive-dependency reproducibility, see PLAN_CI_STRUCTURAL_GAPS.md
# item 2.C) are generated once with `uv pip compile` and then committed — they
# are NOT re-verified by re-running `uv pip compile` and diffing, on purpose:
# that would re-resolve every transitive dependency against PyPI's CURRENT
# state, and flag "stale" on every run where some unrelated transitive
# package published a new patch upstream, even with zero change to this
# repo's own requirements files. That's noise, not signal.
#
# What actually needs catching is narrower: a direct pin in requirements.txt
# or requirements-dev.txt changed (bumped, added, removed) and nobody
# regenerated the lockfile to match. This script checks exactly that — every
# `pkg==X.Y.Z` line in the source files must appear with the identical
# version in the corresponding lockfile. It says nothing about whether the
# lockfile's *transitive* pins are current; that's a separate, deliberately
# unaddressed question (see the plan doc).
#
# Usage:
#   ./scripts/check_python_lockfile_freshness.sh
#
# Exit 0: every direct pin matches. Exit 1: printed which pin(s) drifted and
# the exact regeneration command to fix it.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT/fast_api_voter"

python3 - <<'PY'
import re
import sys

PIN_RE = re.compile(r'^([A-Za-z0-9_.\-]+)(\[[a-z,]+\])?==([0-9A-Za-z.\-+]+)')

# PEP 503: package names are compared case-insensitively with runs of
# -, _, . all treated as equivalent. requirements.txt spells some packages
# with underscores (e.g. prometheus_client) while `uv pip compile`'s output
# uses the canonicalized hyphen form (prometheus-client) -- same package,
# same version, not real drift. Without this, every run would falsely flag
# every such package as stale.
def normalize(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def parse_pins(path):
    pins = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = PIN_RE.match(line)
            if m:
                pins[normalize(m.group(1))] = m.group(3)
    return pins


CHECKS = [
    ('requirements.txt', 'requirements.lock.txt'),
    ('requirements.txt', 'requirements-dev.lock.txt'),
    ('requirements-dev.txt', 'requirements-dev.lock.txt'),
]

problems = []
for src, lock in CHECKS:
    src_pins = parse_pins(src)
    lock_pins = parse_pins(lock)
    for name, version in src_pins.items():
        lock_version = lock_pins.get(name)
        if lock_version != version:
            problems.append(
                f"{name}: {src} pins {version}, but {lock} has "
                f"{lock_version or 'no matching entry'}"
            )

if problems:
    print("Python lockfiles are stale:", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Regenerate with (from fast_api_voter/):", file=sys.stderr)
    print("  uv pip compile requirements.txt -o requirements.lock.txt", file=sys.stderr)
    print("  uv pip compile requirements.txt requirements-dev.txt -o requirements-dev.lock.txt", file=sys.stderr)
    sys.exit(1)

print("Python lockfiles match the direct pins in requirements.txt/requirements-dev.txt.")
PY
