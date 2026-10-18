#!/usr/bin/env bash
# Copy a rented session's runs and telemetry back to this machine (plan-rented-gpu-runs.md §10). Safe to repeat
# during the session (rsync sends only what changed); run it once more before terminating the pod.
#
#   scripts/rented/fetch.sh <pod-ip> <ssh-port> <private-key> [destination]
#
# The pod's address and port change on every restart: read them from the pod's ssh.direct, never from an old note.
set -euo pipefail
[ $# -ge 3 ] || { sed -n '2,7p' "$0"; exit 2; }
IP=$1 PORT=$2 KEY=$3 DEST=${4:-$HOME/Documents/Dev/polity-runs/rented}
mkdir -p "$DEST"
rsync -az --partial --info=stats1 -e "ssh -p $PORT -i $KEY -o StrictHostKeyChecking=accept-new" \
  "root@$IP:/workspace/runs/" "$DEST/"
echo "fetched into $DEST"; ls "$DEST"
