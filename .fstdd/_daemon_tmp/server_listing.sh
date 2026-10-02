#!/bin/bash
set -e
mkdir -p /d/FSTDD003/.fstdd/_daemon_tmp
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/" > /d/FSTDD003/.fstdd/_daemon_tmp/server_listing.txt
echo "ssh_exit=$?"
echo "count_shou=$(grep -c 'FSTDD003收-' /d/FSTDD003/.fstdd/_daemon_tmp/server_listing.txt)"
echo "count_fu=$(grep -c 'FSTDD003复-' /d/FSTDD003/.fstdd/_daemon_tmp/server_listing.txt)"
echo "count_total=$(wc -l < /d/FSTDD003/.fstdd/_daemon_tmp/server_listing.txt)"
