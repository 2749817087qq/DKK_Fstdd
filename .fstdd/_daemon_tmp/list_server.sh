#!/bin/bash
set -e
OUT="/d/FSTDD003/.fstdd/_daemon_tmp/server_listing_full.txt"
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
    "ls -la /home/ubuntu/fstdd-notices/FSTDD003/" > "$OUT"
echo "ssh_exit=$?"
echo "lines=$(wc -l < $OUT)"
echo "count_shou=$(grep -c 'FSTDD003收-' $OUT || true)"
echo "count_fu=$(grep -c 'FSTDD003复-' $OUT || true)"
echo "count_kreply=$(grep -c '^.*K-reply' $OUT || true)"
