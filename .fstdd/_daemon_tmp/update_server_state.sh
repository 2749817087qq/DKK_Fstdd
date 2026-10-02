#!/bin/bash
set -e
# Capture full server listing as JSON-like for reconcile
ssh -i /d/id_ed25519 -o StrictHostKeyChecking=no ubuntu@43.134.236.80 \
  "ls -la /home/ubuntu/fstdd-notices/FSTDD003/ | awk 'NR>3 {print \$6,\$7,\$8,\$9}'" \
  > /tmp/_lst.txt
python3 - <<'PY'
import json, re, datetime
lines = [l.rstrip() for l in open("/tmp/_lst.txt", encoding="utf-8", errors="replace") if l.strip()]
files = []
for l in lines:
    parts = l.split()
    if len(parts) >= 4:
        name = parts[-1]
        if name in (".", ".."): continue
        mtime = " ".join(parts[-4:-1])
        files.append({"mtime": mtime, "name": name})
state = {
    "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "exit": 0,
    "count": len(files),
    "err": "",
    "files": files,
}
import io
with open(r"D:\FSTDD003\.fstdd\_daemon_tmp\server_state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=1)
print("server_state.json updated, count=%d" % len(files))
PY
