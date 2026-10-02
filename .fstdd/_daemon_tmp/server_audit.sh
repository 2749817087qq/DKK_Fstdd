#!/bin/bash
set -e
# Capture server listing, save to tmp on Windows path
SSH_OUT="/tmp/_lst.txt"
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/" > "$SSH_OUT"
echo "=== SSH EXIT $? ==="
echo "=== TOTAL LINES: $(wc -l < $SSH_OUT) ==="
echo "=== GREP COUNTS ==="
echo "收-* count: $(grep -c 'FSTDD003收-' $SSH_OUT || true)"
echo "复-* count: $(grep -c 'FSTDD003复-' $SSH_OUT || true)"
echo "=== NEWEST 10 (by mtime, descending) ==="
ls -la /d/FSTDD003/.fstdd/_notices/FSTDD003/ | sort -k 6,7 | tail -20
