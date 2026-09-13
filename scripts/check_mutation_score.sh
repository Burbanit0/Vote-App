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
# UPDATE (2026-09-13): replaced the hand-maintained floor (a bare percentage
# in mutation-testing.yml, raised by memory "only when the score has
# genuinely improved") with a baseline file, .github/mutation-baseline.json
# -- the exact scripts/check_quality_ratchet.sh idiom (record today's
# number, fail on drift, --update to accept a new one), for the same reason
# that ratchet exists: a floor nobody remembers to raise sits below the
# real score forever, and a floor nobody remembers to LOWER after a real
# regression is a floor that was never enforcing anything.
#
# Deliberately NOT the quality ratchet's exact symmetric rule (fail on ANY
# change, up or down) -- mutmut has genuine run-to-run noise the ratchet's
# other tools (vulture/radon/deptry/knip/jscpd) don't: a mutant that hangs
# on one run and completes on the next shifts the timeout/killed counts by
# a handful either way with zero code change (observed directly: two
# back-to-back runs of the exact same commit differed by ~0.1 percentage
# points). Failing on every such wobble would make this gate exactly the
# kind of noisy, ignored signal PLAN_REMEDIATION_CI_CD.md's whole ci-health
# effort exists to prevent. So: fail only on a drop past NOISE_TOLERANCE_PP
# (a real regression), never on a rise -- an improvement is reported and
# suggested for `--update`, not forced.
#
# KNOWN LIMITATION: the tolerance means two separate real regressions, each
# smaller than NOISE_TOLERANCE_PP on its own, can each land as a green "holds
# at baseline" and only the second trips the gate -- against the ORIGINAL
# baseline, not the first regression's commit. This runs on `push` to
# develop, not per-PR, so that's a real (if narrow) gap between commits, not
# just a race within one. If a failure here doesn't look explained by the
# triggering commit alone, check whether the baseline itself is already
# stale from an earlier below-tolerance drop.
#
# Usage:
#   ./scripts/check_mutation_score.sh <mutmut-run.log>              # check (CI)
#   ./scripts/check_mutation_score.sh <mutmut-run.log> --update     # accept current score as the new baseline
#
# MEASURE THE BASELINE ON AN UP-TO-DATE BRANCH, same reason as the quality
# ratchet: CI runs mutmut on the PR's merge result, so a branch cut before
# someone else's merge can disagree with what CI actually measures.

set -euo pipefail

export PYTHONIOENCODING=utf-8

LOG="${1:?usage: $0 <mutmut-run.log> [--update]}"
UPDATE=0
case "${2:-}" in
  "") ;;
  --update) UPDATE=1 ;;
  *)
    echo "🔴 Unrecognized second argument: ${2}" >&2
    echo "   Usage: $0 <mutmut-run.log> [--update]" >&2
    exit 1
    ;;
esac

[[ -f "$LOG" ]] || {
  echo "🔴 $LOG not found — mutmut did not produce a log." >&2
  echo "   Refusing to report a passing score on absent data." >&2
  exit 1
}

# Resolve LOG to an absolute path before the repo-root `cd` below -- otherwise
# a path relative to some OTHER cwd (e.g. run from fast_api_voter/, as the
# mutmut invocation right before this one in the workflow and SKILL.md both
# are) would silently resolve against the wrong directory once we've moved.
LOG="$(cd -- "$(dirname -- "$LOG")" &>/dev/null && pwd)/$(basename -- "$LOG")"

# Same repo-root anchor as check_quality_ratchet.sh, for the same reason:
# BASELINE below is a path relative to the repo root, not to wherever this
# script happens to be invoked from.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR/.."

BASELINE=".github/mutation-baseline.json"
NOISE_TOLERANCE_PP=0.3

python - "$LOG" "$BASELINE" "$UPDATE" "$NOISE_TOLERANCE_PP" <<'PY'
import json
import re
import sys

log_path, baseline_path, update, tolerance = sys.argv[1], sys.argv[2], sys.argv[3] == "1", float(sys.argv[4])

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
done = int(m["done"])
total = int(m["total"])
killed = int(m["killed"])
survived = int(m["survived"])
timeout = int(m["timeout"])

if total == 0:
    print("🔴 mutmut reported 0 mutants — nothing was measured.", file=sys.stderr)
    sys.exit(1)

# A crash or kill partway through (this pipeline's had both -- see the
# numpy/mutmut 3.7.0 in-process-crash history in pyproject.toml's
# [tool.mutmut] notes) still leaves a real progress line behind, just one
# where done < total. Scoring killed/TOTAL against an incomplete run would
# understate the score using the FULL population as the denominator and
# report a false regression -- worse, it would look identical to a real one.
if done != total:
    print(f"🔴 mutmut only processed {done}/{total} mutants -- the run did not finish.", file=sys.stderr)
    print("   Scoring a partial run against the full mutant population would", file=sys.stderr)
    print("   silently understate the score and report a false regression.", file=sys.stderr)
    print("   Find out why the run stopped short and re-run it. Not guessing.", file=sys.stderr)
    sys.exit(1)

score = 100.0 * killed / total

print(f"{'mutants':<12}{total:>7}")
print(f"{'killed':<12}{killed:>7}")
print(f"{'survived':<12}{survived:>7}")
print(f"{'timeout':<12}{timeout:>7}")
print("-" * 19)
print(f"{'score':<12}{score:>6.2f}%")
print()

if update:
    json.dump({"score": round(score, 2), "killed": killed, "total": total}, open(baseline_path, "w"), indent=2)
    open(baseline_path, "a").write("\n")
    print(f"✅ Baseline updated: {score:.2f}% ({killed}/{total})")
    sys.exit(0)

try:
    with open(baseline_path) as f:
        base = json.load(f)
except FileNotFoundError:
    sys.stdout.flush()
    print(f"🔴 {baseline_path} is missing. Create it with: ./scripts/check_mutation_score.sh <log> --update", file=sys.stderr)
    sys.exit(1)

baseline_score = base["score"]
delta = score - baseline_score
print(f"{'baseline':<12}{baseline_score:>6.2f}%   ({base['killed']}/{base['total']})")
print(f"{'delta':<12}{delta:>+6.2f}pp")
print()

if delta < -tolerance:
    sys.stdout.flush()
    print(f"🔴 Backend mutation score {score:.2f}% dropped from the {baseline_score:.2f}% baseline "
          f"(more than the {tolerance}pp noise tolerance).", file=sys.stderr)
    print("", file=sys.stderr)
    print("   A drop means new code arrived that no assertion pins, or an", file=sys.stderr)
    print("   existing assertion was weakened. Inspect the survivors with:", file=sys.stderr)
    print("     cd fast_api_voter && python -m mutmut results", file=sys.stderr)
    print("     python -m mutmut show <mutant-id>", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"   Update the baseline ({baseline_path}) only after fixing the real", file=sys.stderr)
    print("   gap, or with a documented reason if the drop is genuinely accepted --", file=sys.stderr)
    print("   never just to get a red run green.", file=sys.stderr)
    sys.exit(1)

if delta > tolerance:
    print(f"🟢 Backend mutation score improved to {score:.2f}% (baseline {baseline_score:.2f}%).")
    print(f"   Lock it in: ./scripts/check_mutation_score.sh {log_path} --update, and commit {baseline_path}.")
else:
    print(f"✅ Backend mutation score {score:.2f}% holds at the {baseline_score:.2f}% baseline.")
PY
