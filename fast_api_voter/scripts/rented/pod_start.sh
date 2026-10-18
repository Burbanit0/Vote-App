#!/usr/bin/env bash
# The rented pod's entry point (plan-rented-gpu-runs.md §10): ssh locked down, the backend's Python environment on the
# persistent disk, the telemetry sampler and the run chain in the background, then vLLM in the foreground.
# Run by the pod's start command after it has checked the repo out at POLITY_SHA; idempotent, so a pod restart
# resumes the runs from their checkpoints. Nothing here talks to anything but 127.0.0.1.
#
# Environment (set on the pod): PUBLIC_KEY (Runpod injects it), ALLOW_FROM (optional: the one address sshd accepts),
# MODEL_REPO, MODEL_REVISION, SERVED_NAME, MAX_MODEL_LEN (32768), and for the runs, chain.sh's variables.
set -euo pipefail
WS=/workspace
REPO=$WS/Vote-App
# 1. ssh: key only, root by key only, optionally one source address (runbook §3.2, §8)
mkdir -p /root/.ssh /run/sshd /etc/ssh/sshd_config.d
grep -qxF "$PUBLIC_KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
{ echo "PasswordAuthentication no"; echo "PermitRootLogin prohibit-password"
  [ -n "${ALLOW_FROM:-}" ] && echo "AllowUsers root@$ALLOW_FROM"; } > /etc/ssh/sshd_config.d/10-lock.conf
ssh-keygen -A >/dev/null && sshd -t && /usr/sbin/sshd
# 2. Python 3.14 and the backend's locked dependencies, once per lock file (uv fetches its own Python)
LOCK=$REPO/fast_api_voter/requirements.lock.txt
STAMP=$WS/venv/.lock-$(sha256sum "$LOCK" | cut -c1-16)
if [ ! -f "$STAMP" ]; then
  command -v uv >/dev/null || pip install -q uv
  uv venv -q --python 3.14 "$WS/venv" && VIRTUAL_ENV=$WS/venv uv pip install -q -r "$LOCK" && touch "$STAMP"
fi
# 3. telemetry and the runs, detached: they wait for vLLM themselves and survive this script's exec
mkdir -p "$WS/runs"
setsid nohup "$WS/venv/bin/python" "$REPO/fast_api_voter/scripts/rented/telemetry.py" >> "$WS/runs/telemetry.log" 2>&1 &
if [ -n "${RUN_LABEL:-}" ]; then
  setsid nohup bash "$REPO/fast_api_voter/scripts/rented/chain.sh" >> "$WS/runs/$RUN_LABEL.chain.log" 2>&1 &
fi
# 4. vLLM, bound to the loopback only: it has no authentication (runbook §8). Flags of docker-compose.llm-h100.yml.
exec vllm serve "$MODEL_REPO" --revision "$MODEL_REVISION" --served-model-name "$SERVED_NAME" \
  --reasoning-parser qwen3 --structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}' \
  --max-model-len "${MAX_MODEL_LEN:-32768}" --gpu-memory-utilization 0.90 \
  --host 127.0.0.1 --port 8000 --seed 42 --enable-prompt-tokens-details
