#!/bin/bash
set -e
scp -i /d/id_ed25519 -o StrictHostKeyChecking=no \
  ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD003/* \
  /d/FSTDD003/.fstdd/_notices/FSTDD003/
echo "=== SCP_EXIT $? ==="
ls /d/FSTDD003/.fstdd/_notices/FSTDD003/ | grep '^FSTDD003收-' | wc -l
ls /d/FSTDD003/.fstdd/_notices/FSTDD003/ | grep '^FSTDD003复-' | wc -l
