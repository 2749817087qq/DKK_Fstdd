#!/usr/bin/env bash
# Step 1: pull FSTDD003 notices from server
set -eu
SSH_KEY=/d/id_ed25519
HOST="ubuntu@43.134.236.80"
REMOTE="ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD003/"
LOCAL=/d/FSTDD003/.fstdd/_notices/FSTDD003/

mkdir -p "$LOCAL"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 -r "$REMOTE"* "$LOCAL"
echo "SCP_EXIT=$?"

echo "=====LANDING====="
ls -1 "$LOCAL" | grep -E '^FSTDD003(收|复)-' | wc -l
echo "---新收---"
ls -1 "$LOCAL" | grep '^FSTDD003收-' | wc -l
echo "---新复---"
ls -1 "$LOCAL" | grep '^FSTDD003复-' | wc -l
