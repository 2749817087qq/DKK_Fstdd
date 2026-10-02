#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FSTDD003 daemon helper: local baseline enumeration + recon report.

Safe to run repeatedly. Reads only D:/FSTDD003/.fstdd/_notices/FSTDD003/.
Usage:
  python fstdd003_daemon_recon.py baseline      # local shou/fufu lists
  python fstdd003_daemon_recon.py recon server.json local_list
  python fstdd003_daemon_recon.py frontmatter <file>
"""
import json
import os
import re
import sys
from pathlib import Path

NOTICE_DIR = Path(r"D:\FSTDD003\.fstdd\_notices\FSTDD003")

PREFIX_IN = "FSTDD003\u6536-"   # FSTDD003收-
PREFIX_OUT = "FSTDD003\u590d-"  # FSTDD003复-

TRAILING = ["要求说明", "要求", "说明", "补发", "硬时限", "通知", "事宜", "的"]


def strip_suffix(name):
    """Rule (c): remove trailing modifiers once, then again."""
    core = name
    for _ in range(2):
        changed = False
        for suf in TRAILING:
            if core.endswith(suf) and len(core) > len(suf):
                core = core[: -len(suf)]
                changed = True
                break
        if not changed:
            break
    return core


def same_task(x, y):
    """Return match kind or None."""
    if x == y:
        return "exact"
    if x in y or y in x:
        return "substring"
    if strip_suffix(x) == strip_suffix(y):
        return "stripped"
    return None


def local_lists():
    inbound, outbound, other = [], [], []
    for p in sorted(NOTICE_DIR.iterdir()):
        if p.is_file():
            n = p.name
            if n.startswith(PREFIX_IN):
                inbound.append(n[len(PREFIX_IN):])
            elif n.startswith(PREFIX_OUT):
                outbound.append(n[len(PREFIX_OUT):])
            else:
                other.append(n)
    return inbound, outbound, other


def cmd_baseline(out_path=None):
    inbound, outbound, other = local_lists()
    payload = json.dumps({
        "dir": str(NOTICE_DIR),
        "inbound": inbound,
        "outbound": outbound,
        "other": other,
    }, ensure_ascii=False, indent=1)
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def _load(name_list):
    if name_list == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(name_list).read_text(encoding="utf-8"))
    return data


def json_out(obj, write_path=None):
    payload = json.dumps(obj, ensure_ascii=False, indent=2)
    if write_path and write_path != "-":
        Path(write_path).write_text(payload, encoding="utf-8")
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def reply_to_index():
    """Map inbound filename -> list of replies whose frontmatter reply_to names it.

    reply_to is the authoritative reply-link declared inside the reply file,
    so it resolves naming drift ("窗口" / date format) without over-matching.
    """
    idx = {}
    for p in sorted(NOTICE_DIR.glob(PREFIX_OUT + "*.md")):
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            continue
        m = re.search(r"^reply_to:\s*(.+?)\s*$", head, re.M)
        if not m:
            continue
        for frag in m.group(1).replace("/", " ").split():
            frag = frag.strip("()（），,、;；")
            if frag.startswith(PREFIX_IN):
                idx.setdefault(frag, []).append(p.name)
    return idx


def cmd_recon(server_arg, local_arg):
    server = _load(server_arg)
    local = _load(local_arg) if local_arg else {"inbound": [], "outbound": []}
    server_in = server.get("inbound", [])
    local_out = local.get("outbound", [])
    idx = reply_to_index()

    matched, pending = {}, []
    for x in sorted(server_in):
        kind = None
        key = PREFIX_IN + x
        if key in idx and idx[key]:
            kind = "reply_to"
        else:
            for y in sorted(local_out):
                k = same_task(x, y)
                if k:
                    kind = k
                    break
        if kind:
            matched[x] = kind
        else:
            pending.append(x)

    kinds = {"reply_to": 0, "exact": 0, "substring": 0, "stripped": 0}
    for k in matched.values():
        kinds[k] = kinds.get(k, 0) + 1

    result = {
        "server_inbound_total": len(server_in),
        "local_outbound_total": len(local_out),
        "matched_total": len(matched),
        "matched_by_kind": kinds,
        "pending_total": len(pending),
        "pending": pending,
        "matched_pairs": matched,
        "reply_to_hits": len(idx),
    }
    write_path = sys.argv[4] if len(sys.argv) > 4 else None
    json_out(result, write_path)


def cmd_frontmatter(paths):
    out = {}
    for f in paths:
        p = Path(f)
        if not p.exists():
            out[p.name] = {"error": "missing"}
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        meta = {}
        m = re.match(r"^---\n(.*?)\n---", txt, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
        urgent = (str(meta.get("priority", "")).strip() == "\u6700\u9ad8"
                  or str(meta.get("confidential", "")).strip().lower() == "true")
        out[p.name] = {"meta": meta, "urgent": urgent, "chars": len(txt)}
    json_out(out)


def cmd_server(out_path=None):
    """List remote FSTDD003 notices via ssh.exe, decoding raw UTF-8 bytes."""
    import subprocess
    host = "ubuntu@43.134.236.80"
    key = r"D:\id_ed25519"
    remote_dir = "/home/ubuntu/fstdd-notices/FSTDD003"
    rc = f"ls -1 {remote_dir} 2>/dev/null"
    r0 = subprocess.run(
        ["ssh", "-i", key, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
         host, rc],
        capture_output=True)
    out = r0.stdout.decode("utf-8", errors="replace").splitlines()
    inbound = sorted(n[len(PREFIX_IN):] for n in out if n.startswith(PREFIX_IN))
    outbound = sorted(n[len(PREFIX_OUT):] for n in out if n.startswith(PREFIX_OUT))
    result = {
        "host": host,
        "dir": remote_dir,
        "ssh_exit": r0.returncode,
        "stderr": r0.stderr.decode("utf-8", errors="replace")[-400:],
        "total": len(out),
        "inbound": inbound,
        "outbound": outbound,
    }
    json_out(result, out_path)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if cmd == "baseline":
        cmd_baseline(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "server":
        cmd_server(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "recon":
        cmd_recon(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "-")
    elif cmd == "frontmatter":
        cmd_frontmatter(sys.argv[2:])
    else:
        raise SystemExit(f"unknown cmd {cmd}")


if __name__ == "__main__":
    main()
