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
# regenerated the lockfile to match. This script checks that — every
# `pkg==X.Y.Z` line in the source files must appear with the identical
# version in the corresponding lockfile — and, since issue #692, that the lockfiles are
# hash-pinned: every pin has `--hash` lines, and every `install -r <lockfile>` in a workflow
# or Dockerfile passes `--require-hashes`. (It does not check that a hash belongs to its
# version: a bumped direct pin already fails the version check above, and only a network
# recompile could check the rest.) It says nothing about whether the
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
import os
import re
import sys

# The extras charset (inside []) allowed only lowercase letters and commas
# at first -- too narrow: a future direct pin with a digit/hyphen/underscore
# in an extra name (e.g. `pkg[extra-two]==1.0.0`) would fail this whole
# anchored match, silently vanishing from parse_pins() with no error. Widened
# to match PEP 508's actual extra-name grammar (letters, digits, `-`, `_`, `.`).
PIN_RE = re.compile(r'^([A-Za-z0-9_.\-]+)(\[[A-Za-z0-9_.\-,]+\])?==([0-9A-Za-z.\-+]+)')

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

# Hash pinning (issue #692): every lockfile pin carries --hash lines, and every install from a
# lockfile passes --require-hashes, so a swapped or re-uploaded release is refused, not installed.
def unhashed(path):
    bad, name, hashed = [], None, False
    with open(path) as f:
        for line in list(f) + ['end==0']:
            m = PIN_RE.match(line.strip())
            if m:
                if name and not hashed:
                    bad.append(name)
                name, hashed = m.group(1), False
            elif '--hash=' in line:
                hashed = True
    return bad


for lock in ('requirements.lock.txt', 'requirements-dev.lock.txt'):
    for name in unhashed(lock):
        problems.append(f"{name}: {lock} has no --hash for it (compile with --generate-hashes)")

INSTALL_RE = re.compile(r'install\b.*-r\s+\S*requirements(-dev)?\.lock\.txt')


def scan_targets():
    """Workflows, the ci-local Dockerfiles, and the Dockerfiles in the repo root and here.

    Bounded on purpose: no walk of the whole tree (node_modules, .git). Where the checkout is
    not whole (the ci-local container only COPYs what its tests read), a missing directory is
    skipped, so this half of the check only runs in a real checkout.
    """
    for top in ('../.github', '../ci-local'):
        for dirpath, _, names in os.walk(top):
            for fname in names:
                yield os.path.join(dirpath, fname)
    for top in ('..', '.'):
        for fname in os.listdir(top):
            yield os.path.join(top, fname)


for path in scan_targets():
    if not path.endswith(('.yml', '.yaml', '.Dockerfile')) and os.path.basename(path) != 'Dockerfile':
        continue
    if not os.path.isfile(path):
        continue
    for n, line in enumerate(open(path, errors='replace'), 1):
        if INSTALL_RE.search(line) and not line.lstrip().startswith('#') and '--require-hashes' not in line:
            problems.append(f"{path}:{n} installs from a lockfile without --require-hashes")

if problems:
    print("Python lockfiles are stale:", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Regenerate with (from fast_api_voter/):", file=sys.stderr)
    print("  uv pip compile --python-platform linux --python-version 3.14 requirements.txt --generate-hashes -o requirements.lock.txt", file=sys.stderr)
    print("  uv pip compile --python-platform linux --python-version 3.14 requirements.txt requirements-dev.txt -c requirements.lock.txt --generate-hashes -o requirements-dev.lock.txt", file=sys.stderr)
    sys.exit(1)

print("Python lockfiles match the direct pins in requirements.txt/requirements-dev.txt.")
PY
