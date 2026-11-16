#!/usr/bin/env bash
# The vLLM bump protocol as one script: test a new vllm/vllm-openai tag against the pinned one.
#
#   scripts/vllm_bump_protocol.sh <new-tag> [out-dir]        # from fast_api_voter/, e.g. v0.34.0
#
# What it does, in this order (each step logs its exit code; only the PROBE can stop the chain):
#   PRE   preflight: nothing else on the GPU, the new image is local (PULL=1 pulls it), disk space.
#   B0-B1 serve the NEW tag, then the two-minute PROBE (representative_response, 45 cases, 50 answers).
#         Below PROBE_MIN valid answers the chain STOPS and prints the diagnosis arms (EXP-026): vLLM 0.32
#         and 0.33 both failed here (compact JSON separators, vLLM PR #58067). Nothing else is worth
#         running on a server that fails it. Set FORCE=1 to continue anyway.
#   B2-B10 thinking budget, determinism within and across a restart, three restarts, the live suite,
#         warm-up + two 2-year A/B runs, the full bank.
#   O     the ADR-030 field-order check on the new tag (check_schema_order.py).
#   A     the same steps on the PINNED tag as the control, the same day, same code (so a drift in the model,
#         the bank or the machine does not pass for a vLLM change), then the scorecard.
#   C     the server is stopped (it is stopped at start: this protocol never leaves it running).
#
# Needs the GPU to itself (about 1 h 15 of it) and a Python with the backend's dependencies (PY, default
# .venv/bin/python). The new compose file is the pinned one with the image tag replaced: the pin in the repo
# is NOT edited. Adopting a tag is a separate, reviewed commit (open it as a DRAFT: CI has no GPU).
#
# Everything lands in <out-dir> (default ~/Documents/Dev/polity-runs/vllm-<tag>): chain.log, bank/, ab/, ...
# Run it detached, it outlives a terminal:  setsid nohup scripts/vllm_bump_protocol.sh v0.34.0 > /dev/null 2>&1 &
# To stop it early signal the whole group (bash runs its trap only when the current step ends, so a bare kill of the
# script waits for it):  kill -TERM -<pid>   then   docker compose -f docker-compose.llm.bump-new.yml down
# A SIGKILL or a reboot cannot be trapped: check \`docker ps\` afterwards.
#
# DRY=1 only runs the preflight and writes the two compose files, so the setup can be checked with the GPU idle.
set -u -o pipefail

NEW_TAG="${1:?usage: scripts/vllm_bump_protocol.sh <new-tag, e.g. v0.34.0> [out-dir]}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"          # fast_api_voter/
OUT="${2:-$HOME/Documents/Dev/polity-runs/vllm-$NEW_TAG}"
# The venv lives in one worktree only (the polity one): take the first worktree that has it, or set PY.
if [ -z "${PY:-}" ]; then
  for wt in "$HERE" $(git -C "$HERE" worktree list --porcelain | sed -n 's/^worktree //p'); do
    [ -x "$wt/fast_api_voter/.venv/bin/python" ] && PY="$wt/fast_api_voter/.venv/bin/python" && break
    [ -x "$wt/.venv/bin/python" ] && PY="$wt/.venv/bin/python" && break
  done
fi
PY="${PY:-python3}"
PROBE_MIN="${PROBE_MIN:-45}"                                      # of 50 answers; 0.31.0 gives 48
NEED_GB="${NEED_GB:-45}"                                          # image (~33 GB) + logs
BASE_COMPOSE="$HERE/docker-compose.llm.yml"
OLD_TAG="$(grep -oE 'image: vllm/vllm-openai:v[0-9.]+' "$BASE_COMPOSE" | head -1 | sed 's/.*://')"
CTRL="$HERE/docker-compose.llm.bump-control.yml"                  # beside the original: relative paths hold
NEW="$HERE/docker-compose.llm.bump-new.yml"
cd "$HERE" || exit 1
[[ "$NEW_TAG" =~ ^v[0-9]+(\.[0-9]+)+(rc[0-9]+)?$ ]] || { echo "STOP: '$NEW_TAG' is not a tag like v0.34.0 or v0.34.0rc1"; exit 1; }
mkdir -p "$OUT"

step() { echo; echo "=== $(date -u +%FT%TZ) $*"; }
rc() { echo "--- exit $?"; }
die() { echo "STOP: $*"; exit 1; }

healthy() {
  local t0=$SECONDS
  for _ in $(seq 1 "${HEALTH_TRIES:-240}"); do
    [ -n "$(docker ps --filter name='^vllm-polity$' --format '{{.Names}}')" ] \
      && curl -sf localhost:8000/health >/dev/null && { echo "healthy after $((SECONDS - t0)) s"; return 0; }
    sleep 2
  done
  echo "NOT HEALTHY after $((SECONDS - t0)) s"; docker logs --tail 40 vllm-polity 2>&1; return 1
}
serverinfo() {
  docker inspect vllm-polity --format '{{.Config.Image}} {{.Image}}'
  docker logs vllm-polity 2>&1 | grep -E "Initializing a V1 LLM engine|speculative_config=|KV cache|Maximum concurrency|will be removed|deprecat|Traceback|ERROR" | cut -c1-400 | tail -14
}
serve() { docker compose -f "$1" up -d --force-recreate 2>&1 | tail -1; healthy && { serverinfo || true; }; }  # info only: a grep with no match must not fail the serve
# a server that does not come up ends the chain (the trap stops it): an hour of steps against nothing is worse
must_serve() { serve "$1" || die "the server did not come up ($1)"; }
restart_vllm() { docker compose -f "$1" restart vllm 2>&1 | tail -1; healthy || die "no healthy server after the restart"; }
ab() { "$PY" scripts/check_vllm_speculation_ab.py "$1" "$2" "$OUT/ab/$1" 2>&1 | grep -E "AB_RESULT|Error|Traceback"; rc; }
bank() { "$PY" scripts/run_bakeoff.py --label "$1" --out "$OUT/bank" "${@:2}" > "$OUT/$1.log" 2>&1; rc; tail -5 "$OUT/$1.log"; }
# valid answers among the response_sweep rows of a bank session, "valid/total"
probe_valid() {
  "$PY" - "$OUT/bank/$1/results.jsonl" <<'PY'
import json, sys
try:
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
except OSError:
    print("none"); sys.exit(0)
sweep = [r for r in rows if r.get("family") == "response_sweep"]
print(f"{sum(1 for r in sweep if r.get('valid'))}/{len(sweep)}")
PY
}

# --- compose files: the pinned one is the control, the new one is the same with the tag swapped ---
[ -n "$OLD_TAG" ] || die "no vllm/vllm-openai tag found in $BASE_COMPOSE"
cp "$BASE_COMPOSE" "$CTRL"
sed "s#vllm/vllm-openai:$OLD_TAG#vllm/vllm-openai:$NEW_TAG#" "$BASE_COMPOSE" > "$NEW"
grep -q "vllm/vllm-openai:$NEW_TAG" "$NEW" || die "tag swap failed in $NEW"
echo "pinned $OLD_TAG (control: $CTRL), testing $NEW_TAG ($NEW), output $OUT"
[ "$OLD_TAG" != "$NEW_TAG" ] || die "the new tag is the pinned one"

step PRE preflight
docker info >/dev/null 2>&1 || die "docker is not reachable"
others="$(docker ps --format '{{.Names}} {{.Image}}' | grep -i vllm || true)"
[ -z "$others" ] || die "a vLLM container is running ($others): the GPU is shared with other sessions, stop it only if you know nothing uses it"
! (exec 3<>/dev/tcp/127.0.0.1/8000) 2>/dev/null || die "something already listens on :8000"
exec 9>"${TMPDIR:-/tmp}/vllm_bump_protocol.lock"; flock -n 9 || die "another run of this protocol is in progress"
used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)"
[ "${used:-99999}" -lt 2000 ] || die "the GPU has ${used} MiB in use: something else is on it"
free_gb="$(df -BG --output=avail /var/lib/docker | tail -1 | tr -dc 0-9)"
if ! docker image inspect "vllm/vllm-openai:$NEW_TAG" >/dev/null 2>&1; then
  if [ "${PULL:-0}" = 1 ]; then
    [ "$free_gb" -ge "$NEED_GB" ] || die "only ${free_gb} GB free, need ${NEED_GB}"
    docker pull "vllm/vllm-openai:$NEW_TAG" 2>&1 | tail -2
  else
    die "image vllm/vllm-openai:$NEW_TAG is not local: docker pull it, or PULL=1"
  fi
fi
docker image inspect "vllm/vllm-openai:$OLD_TAG" >/dev/null 2>&1 || die "the control image $OLD_TAG is not local"
"$PY" -c "import api.domain.polity.config" || die "PY=$PY cannot import the backend (use the polity worktree's .venv)"
echo "preflight ok: GPU ${used} MiB used, ${free_gb} GB free, images present"
[ "${DRY:-0}" = 1 ] && { echo "DRY=1: stopping here"; exit 0; }

exec > >(tee -a "$OUT/chain.log") 2>&1

# Whatever ends the run (a failed step, Ctrl-C, a kill), the GPU is handed back: the server was stopped at start.
# The tracked results files two steps rewrite are saved to $OUT and restored, so the worktree stays clean.
CLEAN_AT_START=""
for f in scripts/check_thinking_token_budget_results.md scripts/check_schema_order_results.md; do
  git diff --quiet -- "$f" 2>/dev/null && CLEAN_AT_START="$CLEAN_AT_START $f"
done
cleanup() {
  trap - EXIT
  docker compose -f "$NEW" down >/dev/null 2>&1; docker compose -f "$CTRL" down >/dev/null 2>&1
  docker compose -f "$HERE/docker-compose.llm.bump-arm.yml" down >/dev/null 2>&1
  docker rmi "vllm-probe:$NEW_TAG-sep" >/dev/null 2>&1
  for f in $CLEAN_AT_START; do   # only the files that were clean before the run: never discard someone's edits
    if ! git diff --quiet -- "$f" 2>/dev/null; then cp "$f" "$OUT/$(basename "$f" .md).new-run.md"; git checkout -- "$f"; fi
  done
  echo "cleanup done $(date -u +%FT%TZ)"
}
trap cleanup EXIT
trap 'echo INTERRUPTED; exit 130' INT TERM HUP

step B0 serve "$NEW_TAG"; must_serve "$NEW"
step B1 PROBE response_sweep on "$NEW_TAG"; bank probe-new --families response_sweep
ok="$(probe_valid probe-new)"; echo "PROBE: $ok valid (stop below $PROBE_MIN of 50)"
probe_failed() { case "$1" in [0-9]*/[0-9]*) [ "${1%%/*}" -lt "$PROBE_MIN" ];; *) true;; esac; }  # no result counts as a fail
if probe_failed "$ok" && [ "${FORCE:-0}" != 1 ]; then
  # The one-variable arm that explained 0.33 (EXP-026): the same image with the compact-JSON line undone.
  # ARM=0 skips it. If it passes, the cause is the same line and only the pin decision is left.
  if [ "${ARM:-1}" = 1 ]; then
    step B1b ARM separators restored on "$NEW_TAG" "(build, serve, probe: about 6 minutes)"
    ARM_DIR="$OUT/arm-separators"; mkdir -p "$ARM_DIR"
    cat > "$ARM_DIR/Dockerfile" <<DOCKER
FROM vllm/vllm-openai:$NEW_TAG
RUN f=\$(python3 -c "import vllm,os;print(os.path.join(os.path.dirname(vllm.__file__),'v1/structured_output/backend_xgrammar.py'))") \\
 && python3 - "\$f" <<'PYEOF'
import sys
p = sys.argv[1]; s = open(p).read()
old = 'separators = (",", ":") if self.disable_any_whitespace else None'
assert s.count(old) == 1, "the separators line is not where it was: read the new backend_xgrammar.py"
open(p, "w").write(s.replace(old, "separators = None  # probe: 0.31 behaviour"))
PYEOF
DOCKER
    if docker build -q -t "vllm-probe:$NEW_TAG-sep" "$ARM_DIR" > "$ARM_DIR/build.log" 2>&1; then
      sed "s#vllm/vllm-openai:$NEW_TAG#vllm-probe:$NEW_TAG-sep#" "$NEW" > "$HERE/docker-compose.llm.bump-arm.yml"
      serve "$HERE/docker-compose.llm.bump-arm.yml" || echo "ARM server did not come up"
      bank probe-arm-sep --families response_sweep
      echo "ARM separators restored: $(probe_valid probe-arm-sep) valid  (stock $NEW_TAG: $ok, $OLD_TAG: see EXP-026, 48/50)"
      docker compose -f "$HERE/docker-compose.llm.bump-arm.yml" down 2>&1 | tail -1
      docker rmi "vllm-probe:$NEW_TAG-sep" >/dev/null 2>&1
    else
      echo "ARM not built (see $ARM_DIR/build.log): $(tail -3 "$ARM_DIR/build.log")"
    fi
  fi
  cat <<EOF

PROBE FAILED on $NEW_TAG ($ok). This is the 0.32 / 0.33 failure unless the raw outputs say otherwise:
  1. Look at the answers: \`grep -c '"shifts": \[\]' $OUT/bank/probe-new/results.jsonl\`-style. Every answer
     "stance":1 or 2 with "shifts":[] is the compact-JSON collapse (docs/exploration/EXP-026).
  2. Check upstream first: does StructuredOutputsConfig now have a separators setting, or is PR #58067
     reverted? \`docker run --rm vllm/vllm-openai:$NEW_TAG python3 -c "import vllm.config as c; print(c.StructuredOutputsConfig.__dataclass_fields__.keys())"\`
  3. One-variable arms, 2 minutes each, as in EXP-026: no EAGLE-3 (drop --speculative-config), and the
     separators line restored (backend_xgrammar.py: separators = None). docs/exploration/EXP-026 has both Dockerfiles.
  4. The pin stays on $OLD_TAG (owner's call). Re-run with FORCE=1 to run the rest anyway.
EOF
  echo "CHAIN_STOPPED_AT_PROBE $(date -u +%FT%TZ)"; exit 2
fi

step B2 thinking budget; "$PY" scripts/check_thinking_token_budget.py 2>&1 | tail -8; rc
mkdir -p "$OUT/thinking-new"
mv scripts/check_thinking_token_budget_results.calls.jsonl scripts/check_thinking_token_budget_results.json scripts/llm_calls_summary.json "$OUT/thinking-new/" 2>/dev/null
git diff --stat scripts/check_thinking_token_budget_results.md   # byte-identical when the budget is honoured
step B3 determinism within the run; "$PY" scripts/check_vllm_batching_determinism.py --save "$OUT/det-new.json" 2>&1 | tail -15; rc
step B4 restart then determinism across it; restart_vllm "$NEW"
"$PY" scripts/check_vllm_batching_determinism.py --compare "$OUT/det-new.json" 2>&1 | tail -15; rc
for i in 1 2 3; do step B5.$i restart $i; restart_vllm "$NEW"
  curl -s localhost:8000/v1/models | head -c 200; echo; done
serverinfo
step B6 live suite; POLITY_VLLM_LIVE=1 POLITY_VLLM_URL=http://localhost:8000/v1 timeout 3600 "$PY" -m pytest api/tests/test_polity_vllm_live.py -o addopts="" -q -rfxXs --tb=short -p no:logging > "$OUT/live-new.log" 2>&1; rc; tail -15 "$OUT/live-new.log"
step B7 warm-up 1y; ab W-new 1
step B8 A/B 2y, first; ab D1 2
step B9 A/B 2y, second; ab D2 2
step B10 bank on the new tag; bank bank-new

step O1 field order isolation; "$PY" scripts/check_schema_order.py isolation 2>&1 | tail -5; rc
step O2 field order run; "$PY" scripts/check_schema_order.py run --out "$OUT/order" --restart-between-controls "docker compose -f $NEW restart vllm" > "$OUT/order-run.log" 2>&1; rc; tail -5 "$OUT/order-run.log"
step O3 field order decide; "$PY" scripts/check_schema_order.py decide --out "$OUT/order" > "$OUT/order-decide.log" 2>&1; rc; tail -25 "$OUT/order-decide.log"

step A0 serve the pinned $OLD_TAG as control; must_serve "$CTRL"
step A1 PROBE on $OLD_TAG; bank probe-control --families response_sweep
echo "control PROBE: $(probe_valid probe-control) valid"
step A2 warm-up 1y; ab W-ctl 1
step A3 control A/B 2y, first; ab C1 2
step A4 control A/B 2y, second; ab C2 2
step A5 bank on $OLD_TAG; bank bank-control
step A6 scorecard; "$PY" scripts/bakeoff_report.py "$OUT/bank" --control bank-control 2>&1 | tail -8; rc

step C0 stop the server, it was stopped at start; docker compose -f "$CTRL" down 2>&1 | tail -2
echo; echo "CHAIN_DONE $(date -u +%FT%TZ)"
