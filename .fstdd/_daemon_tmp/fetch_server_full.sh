#!/bin/bash
set -e
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/ | awk '{print \$6,\$7,\$8,\$9}'" > /tmp/_ls_full.txt
echo "=== LS_FULL (head -60) ==="
head -60 /tmp/_ls_full.txt
echo "=== LS_COUNTS ==="
grep -c 'FSTDD003收-' /tmp/_ls_full.txt || true
grep -c 'FSTDD003复-' /tmp/_ls_full.txt || true
echo "=== TOTAL ==="
wc -l /tmp/_ls_full.txt
