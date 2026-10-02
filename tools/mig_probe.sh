#!/bin/bash
KEY='D:/FSTDD003/.fstdd/_notices/FSTDD003/FSTDD003-ssh-key'
[ -f "$KEY" ] || KEY='C:/Users/Administrator/.ssh/fstdd003-key'

ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL fstdd003@43.134.236.80 'bash -s' <<'REMOTE'
set +e
echo "=== COUNTS ==="
echo "FSTDD003_SHOU=$(ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '^FSTDD003收-' | wc -l)"
echo "FSTDD003_FU=$(ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '^FSTDD003复-' | wc -l)"
echo "OTHER_SHOU=$(ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '收-' | grep -v '^FSTDD003' | wc -l)"
ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '收-' | grep -v '^FSTDD003'
echo
echo "=== FSTDD003-SHOU-LIST ==="
ls /home/ubuntu/fstdd-notices/FSTDD003/ | grep '^FSTDD003收-' | sort
echo
echo "=== INBOX ==="
ls -la /home/ubuntu/fstdd-inbox/FSTDD003/ 2>&1
echo
echo "=== WRITABLE-TEST-NOTICES ==="
touch /home/ubuntu/fstdd-notices/FSTDD003/_fstdd003_write_probe && ls -la /home/ubuntu/fstdd-notices/FSTDD003/_fstdd003_write_probe && rm /home/ubuntu/fstdd-notices/FSTDD003/_fstdd003_write_probe && echo WRITABLE_OK
echo "=== WRITABLE-TEST-INBOX ==="
touch /home/ubuntu/fstdd-inbox/FSTDD003/_fstdd003_write_probe && ls -la /home/ubuntu/fstdd-inbox/FSTDD003/_fstdd003_write_probe && rm /home/ubuntu/fstdd-inbox/FSTDD003/_fstdd003_write_probe && echo INBOX_WRITABLE_OK
echo
echo "=== CAN-DEL-KEY-COPY ==="
ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key 2>&1
rm -v /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key 2>&1
ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key 2>&1
echo "=== CAN-DEL-KEY-PUB-COPY ==="
ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key.pub 2>&1
rm -v /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key.pub 2>&1
ls -la /home/ubuntu/fstdd-notices/FSTDD003/FSTDD003-ssh-key.pub 2>&1
echo
echo "=== DENY-TESTS ==="
ls /home/fstdd007 2>&1
ls /home/ubuntu/fstdd-collab-dev 2>&1
ls /home/ubuntu/fstdd-k-memory 2>&1
echo "=== HEALTH ==="
curl -s -m 5 http://127.0.0.1:8787/health
echo
echo "=== DATE ==="
date -u '+%Y-%m-%dT%H:%M:%S%z'
REMOTE
