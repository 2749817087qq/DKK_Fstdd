#!/usr/bin/env bash
# Pull FSTDD003 notices via scp -o BatchMode with timeout
set -euo pipefail
mkdir -p /tmp/fstdd003_pull
cd /tmp/fstdd003_pull
scp -i /d/id_ed25519 -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=10 -B ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD003/* ./
echo "PULL_OK"
