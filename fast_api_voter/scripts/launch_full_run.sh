#!/usr/bin/env bash
# Launch the full run (30 simulated years by default, population 500, 75 chamber seats, LLM engine), detached from this
# terminal and from any editor (OBS-014), with the machine kept awake and a free-disk floor (OBS-016).
#
#   scripts/launch_full_run.sh                 DRY RUN: pre-flight and the commands --go would run; starts nothing
#   scripts/launch_full_run.sh --go            start it (refuses if the pre-flight fails)
#   scripts/launch_full_run.sh --go --resume   continue an interrupted run (same RUN_ID)
#
# Environment: PY (python with the backend deps), YEARS (default 30; 2 is the timing probe), RUN_ID, OUT, SEED,
# WORKERS, REPRO (strict|relaxed), VOTE_MODE, DISK_FLOOR_GB (default 8). The choices behind the defaults are in docs/plan/polity/plan-full-run.md.
set -euo pipefail
cd "$(dirname "$0")/.." # fast_api_voter/

PY=$(command -v "${PY:-python}")
YEARS=${YEARS:-30} SEED=${SEED:-42} WORKERS=${WORKERS:-1} REPRO=${REPRO:-strict} FLOOR=${DISK_FLOOR_GB:-8}
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
  --setenv PYTHONUNBUFFERED=1 --property "StandardOutput=append:$LOG" --property "StandardError=append:$LOG"
  --property TimeoutStopSec=300 -- systemd-inhibit --what=sleep:idle:shutdown --who="polity full run"
  --why="$RUN_ID" --mode=block "$PY" "${RUN[@]}")
# No ${...} in the watchdog body: systemd expands it in command lines. It stops with the run (BindsTo).
WATCH=(systemd-run --user --unit "$UNIT-diskwatch" --collect --property "StandardOutput=append:$LOG"
  --property "BindsTo=$UNIT.service" --property "After=$UNIT.service" -- bash -c '
  while systemctl --user is-active --quiet "$0"; do
    free=$(df --output=avail -BG "$1" | tail -1 | tr -dc 0-9)
    if [ "$free" -lt "$2" ]; then
      echo "disk floor: $free GiB free < $2 GiB, stopping the run cleanly (resume with --go --resume)"
      systemctl --user stop "$0"; exit
    fi
    sleep 60
  done' "$UNIT.service" "$OUT" "$FLOOR")

echo "== pre-flight"
if ! "$PY" scripts/prepare_full_run.py --run-id "$RUN_ID" --output-dir "$OUT" --seed "$SEED" --years "$YEARS" \
  --workers "$WORKERS" --reproducibility "$REPRO" "${RESUME[@]}"; then
  [ "$GO" = 1 ] && { echo "refusing to start: pre-flight failed" >&2; exit 1; }
fi

if [ "$GO" != 1 ]; then
  echo -e "\n== DRY RUN, nothing started. --go would run:"
  printf '  %q ' "${MAIN[@]}"; echo -e "\n"
  printf '  %q ' "${WATCH[@]}"; echo
  exit 0
fi

mkdir -p "$OUT"
"${MAIN[@]}"
"${WATCH[@]}"
cat <<EOF

Started $UNIT (log: $LOG)
  status : systemctl --user status $UNIT
  log    : tail -f $LOG
  alive? : $PY scripts/check_run_liveness.py $RUN_DIR
           (never kill a run for silence alone: an election tick is legitimately silent for about an hour at pop 500)
  watch  : ~/Documents/Dev/polity-runs/polity-ui.sh start, then http://localhost:3000/polity (root "full")
  stop   : systemctl --user stop $UNIT   (SIGTERM: the digest is written; continue with --go --resume)
EOF
