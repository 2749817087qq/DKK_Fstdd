#!/bin/bash
set -e
SRC="/d/FSTDD003/.fstdd/_notices/FSTDD003/FSTDD003复-轮询汇总-20260930-00.md"
DST="/home/ubuntu/fstdd-notices/FSTDD003/"
scp -i /d/id_ed25519 -o StrictHostKeyChecking=no "$SRC" "ubuntu@43.134.236.80:${DST}"
echo "scp_exit=$?"
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
    "ls -la /home/ubuntu/fstdd-notices/FSTDD003/ | grep '轮询汇总-20260930-00' || true"
