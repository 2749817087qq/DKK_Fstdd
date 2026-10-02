#!/usr/bin/env bash
# FSTDD003 daemon - step 0: list server-side FSTDD003收-* and local FSTDD003复-*
set -eu
SSH_KEY=/d/id_ed25519
HOST="ubuntu@43.134.236.80"
REMOTE_DIR=/home/ubuntu/fstdd-notices/FSTDD003
LOCAL_DIR=/d/FSTDD003/.fstdd/_notices/FSTDD003

echo "=====SERVER-收====="
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 "$HOST" \
  "ls -1 $REMOTE_DIR/ 2>/dev/null | grep '^FSTDD003收-' || true"

echo "=====LOCAL-复====="
ls -1 "$LOCAL_DIR" 2>/dev/null | grep '^FSTDD003复-' || true

echo "=====LOCAL-收====="
ls -1 "$LOCAL_DIR" 2>/dev/null | grep '^FSTDD003收-' || true
