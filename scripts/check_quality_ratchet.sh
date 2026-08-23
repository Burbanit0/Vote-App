#!/usr/bin/env bash
# scripts/check_quality_ratchet.sh — the code-quality debt may shrink, never grow.
#
# audit.yml's `code-quality` job runs vulture, radon, knip and jscpd, all with
# `continue-on-error: true`. That was the right call when they were added (the
# repo had never done a cleanup pass), but a signal that can never fail is a
# signal nobody reads — it decays into decoration, which is how the e2e suite
# rotted for two months.
#
# The middle ground is a ratchet: record today's counts, then fail only when a
# count INCREASES. Existing debt is grandfathered, new debt is not. No tool is
# re-run here — this reads the .txt files the job already `tee`s, so the ratchet
# costs zero extra CI seconds.
#
# It also fails when a count DROPS, on purpose: a baseline that only a human
# remembers to lower never gets lowered, and the ratchet loosens by one finding
# every time someone cleans up. `--update` rewrites the file for you, so the fix
# is one command, not a hand-edited JSON.
#
# Usage:
#   ./scripts/check_quality_ratchet.sh            # check (CI)
#   ./scripts/check_quality_ratchet.sh --update   # accept current counts as the new baseline
#
# MEASURE THE BASELINE ON AN UP-TO-DATE BRANCH. CI runs these tools on the
# PR's merge result, so a branch cut before someone else's merge produces
# counts CI will not reproduce. The first version of this file was measured on a
# branch one merge behind and disagreed with CI by exactly one finding — the new
# file the missing merge had added. Rebase on develop before --update.
#
# Expects, relative to the repo root (produced by the code-quality job):
#   fast_api_voter/vulture.txt  fast_api_voter/radon.txt
#   voter-app/knip.txt          jscpd.txt

set -euo pipefail

# The report prints ✅/🔴/🟢. Python defaults its stdout encoding to the console
# codepage, which is cp1252 under Git Bash on Windows — every run there died on a
# UnicodeEncodeError instead of reporting. Linux CI never saw it.
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BASELINE=".github/quality-baseline.json"
UPDATE=0
[[ "${1:-}" == "--update" ]] && UPDATE=1

# jscpd and knip colourise their output even when piped; the counts live inside
# the escape sequences, so strip them before matching.
strip_ansi() { sed -r 's/\x1B\[[0-9;]*[mGKHF]//g'; }

# A missing file means the tool's step never ran (a broken install, a renamed
# path). Counting that as "0 findings" would let the ratchet pass green while
# measuring nothing at all — the failure mode this script exists to prevent.
require() {
  [[ -f "$1" ]] || {
    echo "🔴 $1 is missing — the code-quality job did not produce it." >&2
    echo "   Refusing to report a passing ratchet on absent data." >&2
    exit 1
  }
}

require fast_api_voter/vulture.txt
require fast_api_voter/radon.txt
require voter-app/knip.txt
require jscpd.txt

# vulture: one finding per line.
vulture=$(strip_ansi < fast_api_voter/vulture.txt | grep -cve '^[[:space:]]*$' || true)

# radon (`cc -n C`): indented entries like "    F 34:0 _generate_rows - D (21)".
# The bare filename headers between them are not findings.
radon=$(strip_ansi < fast_api_voter/radon.txt | grep -cE '^[[:space:]]+[CMF] [0-9]+:[0-9]+ ' || true)

# knip: sum its own section counts ("Unused exports (47)") rather than counting
# entry lines — the entry format changes between knip versions, the headers don't.
knip=$(strip_ansi < voter-app/knip.txt \
  | grep -oE '^[A-Za-z].*\(([0-9]+)\)$' \
  | sed -E 's/.*\(([0-9]+)\)$/\1/' \
  | awk '{s+=$1} END {print s+0}')

# jscpd: its own summary line, "Found 49 clones."
jscpd=$(strip_ansi < jscpd.txt | sed -nE 's/^Found ([0-9]+) clones\..*/\1/p' | tail -1)
jscpd=${jscpd:-0}

if [[ $UPDATE -eq 1 ]]; then
  python -c "
import json, sys
json.dump({'vulture': $vulture, 'radon_c_plus': $radon, 'knip': $knip, 'jscpd_clones': $jscpd},
          open('$BASELINE', 'w'), indent=2)
open('$BASELINE', 'a').write('\n')
"
  echo "✅ Baseline updated: vulture=$vulture radon=$radon knip=$knip jscpd=$jscpd"
  exit 0
fi

[[ -f "$BASELINE" ]] || {
  echo "🔴 $BASELINE is missing. Create it with: $0 --update" >&2
  exit 1
}

# One python call does the compare + the report: the exit code and the table have
# to agree, and splitting them across bash and python is how they drift apart.
python - "$BASELINE" "$vulture" "$radon" "$knip" "$jscpd" <<'PY'
import json, sys

baseline_path, *counts = sys.argv[1:]
vulture, radon, knip, jscpd = (int(c) for c in counts)

with open(baseline_path) as f:
    base = json.load(f)

rows = [
    ("vulture (Python dead code)",        "vulture",      vulture),
    ("radon (functions ranked C or worse)", "radon_c_plus", radon),
    ("knip (TS dead code / unused deps)", "knip",         knip),
    ("jscpd (duplicate clones)",          "jscpd_clones", jscpd),
]

grown, shrunk = [], []
print(f"{'tool':<38} {'baseline':>9} {'now':>6} {'delta':>7}")
print("-" * 63)
for label, key, now in rows:
    was = base[key]
    delta = now - was
    mark = "🔴" if delta > 0 else ("🟢" if delta < 0 else "  ")
    print(f"{label:<38} {was:>9} {now:>6} {delta:>+7} {mark}")
    if delta > 0:
        grown.append((label, was, now))
    elif delta < 0:
        shrunk.append((label, was, now))
print()

if grown:
    print("🔴 Code-quality debt increased:", file=sys.stderr)
    for label, was, now in grown:
        print(f"   {label}: {was} → {now}", file=sys.stderr)
    print("", file=sys.stderr)
    print("   These tools are non-blocking on their own, but the total may not grow.", file=sys.stderr)
    print("   Fix the new findings, or — if a finding is a false positive — silence it", file=sys.stderr)
    print("   at the source (.vulture_whitelist.py, voter-app/knip.json, .jscpd.json)", file=sys.stderr)
    print("   rather than raising the baseline.", file=sys.stderr)
    sys.exit(1)

if shrunk:
    print("🟢 Debt went down — lock it in so the ratchet cannot loosen again:", file=sys.stderr)
    for label, was, now in shrunk:
        print(f"   {label}: {was} → {now}", file=sys.stderr)
    print("", file=sys.stderr)
    print("   Run ./scripts/check_quality_ratchet.sh --update and commit", file=sys.stderr)
    print(f"   {baseline_path} with this change.", file=sys.stderr)
    sys.exit(1)

print("✅ Code-quality debt held at the baseline.")
PY
