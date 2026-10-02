#!/bin/bash
set -e
echo "=== 1. Server side: current round receipt ==="
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003复-轮询汇总-20260930-00.md"

echo ""
echo "=== 2. Server counts ==="
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep -c '^FSTDD003收-'; ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep -c '^FSTDD003复-'; ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep -c '^K-reply'"

echo ""
echo "=== 3. Server-side K-reply-催办-2026-09-29 still present? ==="
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/K-reply-FSTDD003-催办-2026-09-29.md"

echo ""
echo "=== 4. Local receipts inventory (tail) ==="
ls -la /d/FSTDD003/.fstdd/_notices/FSTDD003/FSTDD003复-轮询汇总-20260930-00.md /d/FSTDD003/.fstdd/_notices/FSTDD003/FSTDD003复-批处理-20260929.md

echo ""
echo "=== 5. Share log (dedup source of truth) ==="
if [ -f /d/FSTDD003/.fstdd/_fstdd003_share_log.json ]; then
  /c/Users/Administrator/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe -c "import json;d=json.load(open(r'/d/FSTDD003/.fstdd/_fstdd003_share_log.json'));print('submitted_total:',len(d) if isinstance(d,list) else len(d.get('submitted',[]) or d))"
fi
