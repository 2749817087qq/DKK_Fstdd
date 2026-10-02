#!/bin/bash
set -e
# Pull only the 3 new files missed by prior rounds
for f in \
  "FSTDD003收-F2K-002-经验收集统一要求-20260929.md" \
  "FSTDD003收-FSTDD标准升级同步规程v1.md" \
  "K-reply-FSTDD003-催办-2026-09-29.md"
do
  echo "=== FETCHING $f ==="
  scp -i /d/id_ed25519 -o StrictHostKeyChecking=no \
    "ubuntu@43.134.236.80:/home/ubuntu/fstdd-notices/FSTDD003/$f" \
    /d/FSTDD003/.fstdd/_notices/FSTDD003/
  echo "exit=$?"
done
echo "=== FINAL LOCAL LIST (sorted by mtime desc) ==="
ls -lt /d/FSTDD003/.fstdd/_notices/FSTDD003/ | head -20
