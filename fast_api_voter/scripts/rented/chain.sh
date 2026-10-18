#!/usr/bin/env bash
# The runs of one rented session (plan-rented-gpu-runs.md §10): every seed of SEEDS in parallel against the pod's own
# vLLM, each retried from its checkpoint (--resume) until its digest says completed. Safe to start again after a pod
# restart: finished seeds are skipped, the others resume. Writes $OUT/CHAIN_DONE when every seed has completed.
#
# Environment: RUN_LABEL (required), SEEDS ("1 2 3"), YEARS (30), POPULATION (500), SEATS (75), PROFILE (exploration),
# WORKERS (24), SERVED_NAME (the model name vLLM serves), ENGINE (llm; "deterministic" for a dry run without vLLM),
# BASE_URL (http://127.0.0.1:8000/v1), PY (/workspace/venv/bin/python), REPO (/workspace/Vote-App), OUT.
set -u
: "${RUN_LABEL:?RUN_LABEL is required}"
SEEDS=${SEEDS:-1 2 3} YEARS=${YEARS:-30} POPULATION=${POPULATION:-500} SEATS=${SEATS:-75} PROFILE=${PROFILE:-exploration}
WORKERS=${WORKERS:-24} ENGINE=${ENGINE:-llm} BASE_URL=${BASE_URL:-http://127.0.0.1:8000/v1}
PY=${PY:-/workspace/venv/bin/python} REPO=${REPO:-/workspace/Vote-App} OUT=${OUT:-/workspace/runs/$RUN_LABEL}
cd "$REPO/fast_api_voter"
mkdir -p "$OUT"
vllm_ready() {  # up to 30 minutes: a first start downloads the weights
  [ "$ENGINE" != llm ] && return 0
  for _ in $(seq 1 180); do
    "$PY" -c "import sys,urllib.request; urllib.request.urlopen(sys.argv[1], timeout=5)" "${BASE_URL%/v1}/health" 2>/dev/null && return 0
    sleep 10
  done
  return 1
}
completed() {
  "$PY" -c "import json,sys; sys.exit(json.load(open(sys.argv[1])).get('outcome') != 'completed')" \
    "$OUT/seed$1/run/seed$1/digest.json" 2>/dev/null
}
run_seed() {
  for attempt in $(seq 1 30); do
    completed "$1" && { echo "seed $1 done $(date -Is)"; return 0; }
    vllm_ready || { echo "seed $1: vLLM not answering on $BASE_URL"; return 1; }
    resume=(); [ -f "$OUT/seed$1/run/seed$1/checkpoint.json" ] && resume=(--resume)
    echo "seed $1 attempt $attempt ${resume[*]} $(date -Is)"
    POLITY_LOG_PROMPTS=1 PYTHONUNBUFFERED=1 "$PY" scripts/run_polity_flagship.py --engine "$ENGINE" \
      --years "$YEARS" --population "$POPULATION" --seats "$SEATS" --seed "$1" --profile "$PROFILE" \
      --max-batch-replays 2 --workers "$WORKERS" --reproducibility relaxed \
      ${SERVED_NAME:+--model "$SERVED_NAME"} --base-url "$BASE_URL" \
      --run-id "seed$1" --output-dir "$OUT" "${resume[@]}" >> "$OUT/seed$1.log" 2>&1
    sleep 15
  done
  return 1
}
echo "START $(date -Is) $(git rev-parse --short HEAD) seeds=[$SEEDS] years=$YEARS population=$POPULATION seats=$SEATS"
for s in $SEEDS; do run_seed "$s" & sleep 5; done
wait
for s in $SEEDS; do completed "$s" || { echo "INCOMPLETE $(date -Is): seed $s"; exit 1; }; done
date -Is > "$OUT/CHAIN_DONE" && echo "CHAIN_DONE $(date -Is)"
