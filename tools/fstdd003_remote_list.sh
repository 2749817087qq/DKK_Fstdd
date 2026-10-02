#!/bin/bash
# FSTDD003 daemon: remote notices listing helper.
# Usage (Git Bash): bash /d/FSTDD003/tools/fstdd003_remote_list.sh [subdir]
# Emits ASCII-only stdout (UTF-8 filenames json-escaped) so PowerShell piping is safe.

HOST="ubuntu@43.134.236.80"
KEY="/d/id_ed25519"
OPTS="-o StrictHostKeyChecking=no"
SUB="${1:-FSTDD003}"
DIR="/home/ubuntu/fstdd-notices/$SUB"
TAG="$(printf '%s' "$SUB" | LC_ALL=C sed 's/[^A-Za-z0-9]/_/g')"

ESC() {
  python3 -c '
import sys, json
for line in sys.stdin:
    line = line.strip()
    if line:
        print(json.dumps(line, ensure_ascii=True))
'
}

ssh -i "$KEY" $OPTS "$HOST" "
D='$DIR'
echo 'DIR_EXISTS=\$(test -d \"\$D\" && echo YES || echo NO)'
echo 'TOTAL=\$(ls -1a \"\$D\" 2>/dev/null | wc -l)'
echo 'COUNT_TAG=\$(ls -1 \"\$D\" 2>/dev/null | grep -c '^$TAG')"
echo 'COUNT_REPLY=\$(ls -1 \"\$D\" 2>/dev/null | grep -c '^$TAG')'
echo '--- INBOUND ---'
ls -1 \"\$D\" 2>/dev/null | grep '收-' | ESC_placeholder
echo '--- OUTBOUND ---'
ls -1 \"\$D\" 2>/dev/null | grep '复-' | ESC_placeholder
echo '--- NEWEST_15 ---'
ls -1t \"\$D\" 2>/dev/null | head -15 | ESC_placeholder
echo '--- TIMES_NEWEST_15 ---'
ls -1t --time-style=+%Y-%m-%dT%H:%M:%S \"\$D\" 2>/dev/null | head -15 | awk '{print \$1}' | tr '\n' ' '
echo
echo '--- DONE ---'
" | ESC

echo "===SCRIPT_DONE==="
