#!/usr/bin/env bash
# Launch the full run (30 simulated years by default, population 500, 75 chamber seats, LLM engine), detached from this
# terminal and from any editor (OBS-014), with the machine kept awake and a free-disk floor (OBS-016).
#
#   scripts/launch_full_run.sh                 DRY RUN: pre-flight and the commands --go would run; starts nothing
#   scripts/launch_full_run.sh --go            start it (refuses if the pre-flight fails)
#   scripts/launch_full_run.sh --go --resume   continue an interrupted run (same RUN_ID)
#
# The run is RELAXED with 12 workers (the owner does not rely on byte-identity): the record is the call log, plus the
# prompts (POLITY_LOG_PROMPTS), the vLLM server log and a GPU/progress sample every minute, all beside the run.
# Environment: PY (python with the backend deps), YEARS (default 30; 2 is the timing probe), RUN_ID, OUT, SEED, WORKERS
# (12), REPRO (relaxed|strict), VOTE_MODE, DISK_FLOOR_GB (8). Why these defaults: docs/plan/polity/plan-full-run.md.
set -euo pipefail
cd "$(dirname "$0")/.." # fast_api_voter/

PY=$(command -v "${PY:-python}")
YEARS=${YEARS:-30} SEED=${SEED:-42} WORKERS=${WORKERS:-12} REPRO=${REPRO:-relaxed} FLOOR=${DISK_FLOOR_GB:-8}
RUN_ID=${RUN_ID:-full-${YEARS}y-p500-seed$SEED-$(date -u +%Y%m%d)}
OUT=${OUT:-$HOME/Documents/Dev/polity-runs/full}
UNIT=polity-$RUN_ID LOG=$OUT/$RUN_ID.log RUN_DIR=$OUT/$RUN_ID/run/$RUN_ID
GO=0 RESUME=()
for arg in "$@"; do
  case $arg in --go) GO=1 ;; --resume) RESUME=(--resume) ;; *) echo "unknown argument: $arg" >&2; exit 2 ;; esac
done

RUN=(scripts/run_polity_flagship.py --engine llm --years "$YEARS" --population 500 --seats 75 --seed "$SEED"
  --max-batch-replays 2 --workers "$WORKERS" --reproducibility "$REPRO" --run-id "$RUN_ID" --output-dir "$OUT"
  ${VOTE_MODE:+--vote-mode "$VOTE_MODE"} "${RESUME[@]}")
# SIGTERM (systemctl stop, or the disk watchdog) makes the runner write its digest, so the run stays resumable.
MAIN=(systemd-run --user --unit "$UNIT" --collect --working-directory "$PWD" --setenv "PATH=$PATH"
  --setenv PYTHONUNBUFFERED=1 --setenv POLITY_LOG_PROMPTS=1 --property "StandardOutput=append:$LOG"
  --property "StandardError=append:$LOG" --property TimeoutStopSec=300 -- systemd-inhibit --what=sleep:idle:shutdown
  --who="polity full run" --why="$RUN_ID" --mode=block "$PY" "${RUN[@]}")
# The helper units stop with the run (BindsTo). No ${...} in their bodies: systemd expands it in command lines.
BIND=(--collect --property "BindsTo=$UNIT.service" --property "After=$UNIT.service")
WATCH=(systemd-run --user --unit "$UNIT-diskwatch" "${BIND[@]}" --property "StandardOutput=append:$LOG" -- bash -c '
  while systemctl --user is-active --quiet "$0"; do
    free=$(df --output=avail -BG "$1" | tail -1 | tr -dc 0-9)
    if [ "$free" -lt "$2" ]; then
      echo "disk floor: $free GiB free < $2 GiB, stopping the run cleanly (resume with --go --resume)"
      systemctl --user stop "$0"; exit
    fi
    sleep 60
  done' "$UNIT.service" "$OUT" "$FLOOR")
# The vLLM server's own log: acceptance length, KV usage, waiting and preempted requests. Docker rotates it; this keeps it.
SERVERLOG=(systemd-run --user --unit "$UNIT-serverlog" "${BIND[@]}" --property "StandardOutput=append:$OUT/$RUN_ID.vllm.log"
  --property "StandardError=append:$OUT/$RUN_ID.vllm.log" -- docker logs -f --tail 0 vllm-polity)
# One JSON line a minute: the GPU (utilisation, memory, temperature, power, clock) and the run's progress.json.
TELEMETRY=(systemd-run --user --unit "$UNIT-telemetry" "${BIND[@]}" --property "StandardOutput=append:$OUT/$RUN_ID.telemetry.jsonl" -- bash -c '
  while systemctl --user is-active --quiet "$0"; do
    gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw,clocks.sm --format=csv,noheader,nounits 2>/dev/null | tr -d " ")
    progress=$(jq -c . "$1" 2>/dev/null || echo null)
    jq -cn --arg t "$(date -u +%FT%TZ)" --arg gpu "$gpu" --argjson p "$progress" "{t:\$t,gpu:\$gpu,progress:\$p}"
    sleep 60
  done' "$UNIT.service" "$RUN_DIR/progress.json")
UNITS=(MAIN WATCH SERVERLOG TELEMETRY)

echo "== pre-flight"
if ! "$PY" scripts/prepare_full_run.py --run-id "$RUN_ID" --output-dir "$OUT" --seed "$SEED" --years "$YEARS" \
  --workers "$WORKERS" --reproducibility "$REPRO" "${RESUME[@]}"; then
  [ "$GO" = 1 ] && { echo "refusing to start: pre-flight failed" >&2; exit 1; }
fi

if [ "$GO" != 1 ]; then
  echo -e "\n== DRY RUN, nothing started. --go would run, in this order:"
  for name in "${UNITS[@]}"; do
    declare -n unit=$name; echo; printf '  %q' "${unit[@]}"; echo
  done
  exit 0
fi

mkdir -p "$OUT"
# run_metadata.json records the server's image and version but not its command line (so not EAGLE-3): keep the inspect,
# one per launch, so a resume after a server change is captured too.
docker inspect vllm-polity > "$OUT/$RUN_ID.server.$(date -u +%Y%m%dT%H%M%SZ).json"
for name in "${UNITS[@]}"; do
  declare -n unit=$name; "${unit[@]}"
done
cat <<EOF

Started $UNIT (helpers: diskwatch, serverlog, telemetry)
  status   : systemctl --user status $UNIT
  run log  : tail -f $LOG
  beside it: $RUN_ID.vllm.log (server), $RUN_ID.telemetry.jsonl (GPU + progress, every minute) and
             $RUN_ID.server.<time>.json (docker inspect: image and full command line) in $OUT,
             and in $RUN_DIR: llm_calls.jsonl (what the model said), llm_prompts.jsonl (what it was asked)
  alive?   : $PY scripts/check_run_liveness.py $RUN_DIR
             (never kill a run for silence alone: an election tick is legitimately silent for about an hour at pop 500)
  watch    : ~/Documents/Dev/polity-runs/polity-ui.sh start, then http://localhost:3000/polity (root "full")
  stop     : systemctl --user stop $UNIT   (SIGTERM: the digest is written; continue with --go --resume)
EOF
