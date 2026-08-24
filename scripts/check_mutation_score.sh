#!/usr/bin/env bash
# scripts/check_mutation_score.sh — fail when the backend mutation score drops.
#
# Coverage counts lines executed; a mutation score counts lines whose behaviour
# is actually pinned by an assertion. mutmut reports that score and has no
# threshold option of its own, so the gate lives here.
#
# It reads mutmut's own final progress line rather than re-running anything:
#
#   1761/1761  🎉 1130 🫥 0  ⏰ 10  🤔 0  🙁 621  🔇 0  🧙 0
#   └ done/total    killed        timeout    suspicious  survived
#
# score = killed / total. Timeouts are NOT counted as kills: a mutant that hangs
# the suite may well be a mutant no assertion would have caught, and counting it
# as a win would let the score drift upward on flakiness alone.
#
# Usage:
#   ./scripts/check_mutation_score.sh <mutmut-run.log> <min-percent>
#
# The log is whatever `mutmut run` printed — tee it in CI, since the score is not
# recoverable from `mutmut results` (which lists only the survivors).

set -euo pipefail

export PYTHONIOENCODING=utf-8

LOG="${1:?usage: $0 <mutmut-run.log> <min-percent>}"
MIN="${2:?usage: $0 <mutmut-run.log> <min-percent>}"

[[ -f "$LOG" ]] || {
  echo "🔴 $LOG not found — mutmut did not produce a log." >&2
  echo "   Refusing to report a passing score on absent data." >&2
  exit 1
}

python - "$LOG" "$MIN" <<'PY'
import re
import sys

log_path, minimum = sys.argv[1], float(sys.argv[2])

# mutmut redraws the progress bar with \r, so the whole run is often one "line".
raw = open(log_path, encoding="utf-8", errors="replace").read().replace("\r", "\n")

# Anchor on the counters, not on the emoji spacing, which mutmut has changed
# between releases: <done>/<total> … 🎉 <killed> … ⏰ <timeout> … 🙁 <survived>
pattern = re.compile(
    r"(?P<done>\d+)/(?P<total>\d+)\s+"
    r"🎉\s*(?P<killed>\d+).*?"
    r"⏰\s*(?P<timeout>\d+).*?"
    r"🙁\s*(?P<survived>\d+)"
)
matches = list(pattern.finditer(raw))
if not matches:
    print("🔴 No mutmut progress line found in the log.", file=sys.stderr)
    print("   Either the run crashed before starting, or mutmut changed its", file=sys.stderr)
    print("   output format and this script needs updating. Not guessing.", file=sys.stderr)
    sys.exit(1)

m = matches[-1]  # the final redraw is the complete one
total = int(m["total"])
killed = int(m["killed"])
survived = int(m["survived"])
timeout = int(m["timeout"])

if total == 0:
    print("🔴 mutmut reported 0 mutants — nothing was measured.", file=sys.stderr)
    sys.exit(1)

score = 100.0 * killed / total

print(f"{'mutants':<12}{total:>7}")
print(f"{'killed':<12}{killed:>7}")
print(f"{'survived':<12}{survived:>7}")
print(f"{'timeout':<12}{timeout:>7}")
print("-" * 19)
print(f"{'score':<12}{score:>6.1f}%   (floor {minimum:.0f}%)")
print()

if score < minimum:
    print(f"🔴 Backend mutation score {score:.1f}% is below the {minimum:.0f}% floor.", file=sys.stderr)
    print("", file=sys.stderr)
    print("   A drop means new code arrived that no assertion pins, or an", file=sys.stderr)
    print("   existing assertion was weakened. Inspect the survivors with:", file=sys.stderr)
    print("     cd fast_api_voter && python -m mutmut results", file=sys.stderr)
    print("     python -m mutmut show <mutant-id>", file=sys.stderr)
    print("", file=sys.stderr)
    print("   Raise the floor in mutation-testing.yml only when the score has", file=sys.stderr)
    print("   genuinely improved — never to get a red run green.", file=sys.stderr)
    sys.exit(1)

print(f"✅ Backend mutation score {score:.1f}% holds above the {minimum:.0f}% floor.")
PY
