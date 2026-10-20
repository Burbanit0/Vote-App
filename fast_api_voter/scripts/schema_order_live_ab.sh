#!/usr/bin/env bash
# ADR-030, stage 2: a candidate WIRE_ORDER against production's, in live runs, after check_schema_order.py chose it.
#
# Usage (from anywhere; needs the vLLM server's GPU and nothing else on it -- check docker ps / nvidia-smi first):
#   scripts/schema_order_live_ab.sh <control worktree> <candidate worktree> <out dir> [years] [seeds]
#   e.g. scripts/schema_order_live_ab.sh ~/Dev/Vote-App-ctl ~/Dev/Vote-App-order ~/polity-runs/order-live 8 "$(seq -s ' ' 1 10)"
# The two worktrees must differ only in WIRE_ORDER (the control is origin/polity, or a branch of it with the table to
# compare against). Two arms, ctl and new, and every seed of both run at once on one server (20 sweeps for the
# default 10 seeds), so each seed's two runs see the same load and are exchangeable if the order changes nothing.
# The report's sign-flip test needs that: never let an older run stand in for an arm; odd seeds start ctl first,
# even seeds new first. With too few seeds the report cannot test some measures and says which
# (schema_order_live_report.testable); 10 seeds detect a shift of 1.5 standard deviations of the per-seed
# difference about 9 times in 10. A seed already complete in an arm is skipped on a resume.
# Then:
#   python scripts/schema_order_live_report.py <out dir>
# The server is left as it was found (stopped if it was stopped). Run it detached (setsid nohup ... &). For scale:
# 9 sweeps took about two hours at 4 years and 6 h 51 min at 8 years (2026-10-20); 20 sweeps on the same server
# take longer.
set -u
CTL=${1:?control worktree}/fast_api_voter
NEW=${2:?candidate worktree}/fast_api_voter
OUT=${3:?out dir}
YEARS=${4:-4}
SEEDS=${5:-"1 2 3 4 5 6 7 8 9 10"}
PY=${PYTHON:-$CTL/.venv/bin/python}
[ -x "$PY" ] || PY=$(command -v python3)
COMPOSE=$CTL/docker-compose.llm.yml
mkdir -p "$OUT"
was_running=$(docker ps -q --filter name=vllm-polity)

healthy() { for _ in $(seq 1 240); do curl -sf localhost:8000/health >/dev/null && return 0; sleep 2; done; return 1; }
vllm_ready() {
  for _ in $(seq 1 90); do
    [ "$(docker inspect vllm-polity --format '{{.State.Health.Status}}' 2>/dev/null)" = healthy ] && return 0
    docker start vllm-polity >/dev/null 2>&1; sleep 10
  done; return 1
}
done_seed() { "$PY" -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(d.get('outcome')!='completed')" \
  "$OUT/$1/sweep-${YEARS}y-p100-seed$2/run/sweep-${YEARS}y-p100-seed$2/digest.json" 2>/dev/null; }
run_seed() {  # arm, worktree, seed
  for attempt in $(seq 1 20); do
    done_seed "$1" "$3" && { echo "$1 seed $3 done $(date -u +%FT%TZ)"; return 0; }
    vllm_ready || { echo "$1 seed $3: vLLM will not come up"; return 1; }
    echo "$1 seed $3 attempt $attempt $(date -u +%FT%TZ)"
    (cd "$2" && PYTHONPATH="$2" "$PY" scripts/run_polity_seed_sweep.py --engine llm --profile exploration --years "$YEARS" \
       --population 100 --seats 15 --output-dir "$OUT/$1" --seeds "$3" --resume-sweep >> "$OUT/$1-seed$3.log" 2>&1)
    sleep 15
  done
}

echo "START $(date -u +%FT%TZ) ctl=$(git -C "$CTL" rev-parse --short HEAD) new=$(git -C "$NEW" rev-parse --short HEAD)"
[ -n "$was_running" ] || { docker compose -f "$COMPOSE" up -d 2>&1 | tail -1; healthy || exit 1; }
echo "vllm: $(docker inspect vllm-polity --format '{{.Config.Image}}')"
for s in $SEEDS; do
  # Alternate which arm starts first, so start order cannot push new - ctl the same way in every seed.
  if [ $((s % 2)) -eq 1 ]; then
    run_seed ctl "$CTL" "$s" & sleep 5
    run_seed new "$NEW" "$s" & sleep 5
  else
    run_seed new "$NEW" "$s" & sleep 5
    run_seed ctl "$CTL" "$s" & sleep 5
  fi
done
wait
echo "RUNS_DONE $(date -u +%FT%TZ)"
[ -n "$was_running" ] || docker compose -f "$COMPOSE" down 2>&1 | tail -1
echo "CHAIN_DONE $(date -u +%FT%TZ)"
