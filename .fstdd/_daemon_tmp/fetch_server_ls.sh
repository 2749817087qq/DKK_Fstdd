#!/bin/bash
set -e
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '^FSTDD003收-' || true"
