#!/usr/bin/env bash
# gpu_queue.sh -- the polity GPU sessions of plan-polity-build-order.md §9, one at a time.
#
# Every measurement needs the model server to itself, so these never run in parallel: a session
# sharing the GPU with another measures the contention, not the arm. The queue waits for the
# server to answer, then runs its steps in order, logging the start, the end and the return code
# of each.
#
# It also refuses to start a step when the root filesystem is nearly full. OBS-016: the disk
# filled during an earlier attempt, p500 seed 42 died mid-tick, and every step of the chain that
# followed failed at once on the same write error, logs included. A queue that stops cleanly
# before a step beats one that dies inside it.
#
# Usage, from fast_api_voter/:
#   scripts/gpu_queue.sh                          # every step, in order
#   scripts/gpu_queue.sh sweep                    # one step
#   scripts/gpu_queue.sh thinking-sampling sweep  # what a resume after an interruption looks like
#   scripts/gpu_queue.sh --list
#
# A step that is already complete resumes rather than repeats: run_bakeoff.py picks up from its
# session's results.jsonl, which is how the 2026-09-14 power-off and the 2026-09-15 Docker
# restart were recovered without re-running what had already been measured.
#
# Environment:
#   POLITY_PYTHON      interpreter (default: fast_api_voter/.venv/bin/python). Point it at a
#                      pinned worktree's venv to keep the queue's code still while other work
#                      continues elsewhere.
#   GPU_QUEUE_LOG      log file (default: fast_api_voter/gpu_queue.log, gitignored)
#   VLLM_URL           model server (default: http://localhost:8000)
#   VLLM_MODEL_MATCH   what /v1/models must mention before starting (default: qwen3)
#   MIN_FREE_GB        free space on / below which a step is refused (default: 10)
#   WAIT_FOR_SERVER    seconds between polls, 0 to fail immediately (default: 30)
set -u

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${POLITY_PYTHON:-$ROOT/.venv/bin/python}"
LOG="${GPU_QUEUE_LOG:-$ROOT/gpu_queue.log}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
VLLM_MODEL_MATCH="${VLLM_MODEL_MATCH:-qwen3}"
WAIT_FOR_SERVER="${WAIT_FOR_SERVER:-30}"

ALL_STEPS=(control vote-grammar budgets thinking-sampling sweep)

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  echo "Steps: ${ALL_STEPS[*]}"
}

log() { echo "$(date -Is) $*" >>"$LOG"; }

free_gb() { df -BG --output=avail / | tail -1 | tr -dc '0-9'; }

# Run one command as a queue step: refuse it on a nearly-full disk, log what it did.
step() {
  local free
  free="$(free_gb)"
  if [ "$free" -lt "$MIN_FREE_GB" ]; then
    log "STOP: ${free} GB free on / (< ${MIN_FREE_GB}) before: $*"
    exit 3
  fi
  log "START ($free GB free) $*"
  "$@" >>"$LOG" 2>&1
  local rc=$?
  log "END rc=$rc $*"
  return $rc
}

bakeoff() { step "$PY" scripts/run_bakeoff.py "$@"; }

# S2.2's control session, which S1.2-S1.4 also compare against as their no-arm session.
run_control() { bakeoff --label qwen3-8b-awq-control; }

# S1.2: the vote_cast grammar.
run_vote_grammar() { bakeoff --label qwen3-8b-awq-vote-grammar --arm vote_grammar --families vote_first_choice; }

# S1.3: the arms run only if the server honours thinking_token_budget at all.
run_budgets() {
  if ! step "$PY" scripts/check_thinking_token_budget.py; then
    log "SKIP: the budgets, the precondition did not hold"
    return 0
  fi
  bakeoff --label qwen3-8b-awq-budget-4096 --arm thinking_budget_4096 --families vote_first_choice chamber_poles
  bakeoff --label qwen3-8b-awq-budget-2048 --arm thinking_budget_2048 --families vote_first_choice chamber_poles
}

# S1.4: Qwen's recommended thinking settings against temperature 0.
run_thinking_sampling() {
  bakeoff --label qwen3-8b-awq-thinking-sampling --arm thinking_sampling --families vote_first_choice chamber_poles
}

# S2.1: the concurrency sweep under the server's current KV cache setting.
run_sweep() { step "$PY" scripts/run_concurrency_sweep.py run --label "${SWEEP_LABEL:-kv-auto}" --workers 1 4 8 12; }

run_step() {
  case "$1" in
    control) run_control ;;
    vote-grammar) run_vote_grammar ;;
    budgets) run_budgets ;;
    thinking-sampling) run_thinking_sampling ;;
    sweep) run_sweep ;;
    *) echo "unknown step: $1 (known: ${ALL_STEPS[*]})" >&2; exit 2 ;;
  esac
}

wait_for_server() {
  until curl -sf -m 5 "$VLLM_URL/v1/models" | grep -q "$VLLM_MODEL_MATCH"; do
    if [ "$WAIT_FOR_SERVER" -eq 0 ]; then
      log "STOP: no server answering at $VLLM_URL"
      exit 4
    fi
    sleep "$WAIT_FOR_SERVER"
  done
}

case "${1:-}" in
  -h | --help) usage; exit 0 ;;
  --list) printf '%s\n' "${ALL_STEPS[@]}"; exit 0 ;;
esac

steps=("$@")
[ ${#steps[@]} -eq 0 ] && steps=("${ALL_STEPS[@]}")
for name in "${steps[@]}"; do
  case " ${ALL_STEPS[*]} " in *" $name "*) ;; *) echo "unknown step: $name (known: ${ALL_STEPS[*]})" >&2; exit 2 ;; esac
done

cd "$ROOT" || exit 1
wait_for_server
log "server answering at $VLLM_URL; queue: ${steps[*]}"
for name in "${steps[@]}"; do run_step "$name"; done
log "QUEUE DONE (${steps[*]})"
