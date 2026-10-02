import json, os, re, datetime
from collections import Counter

NOTICE_DIR = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"
STATE = r"D:\FSTDD003\.fstdd\_daemon_tmp\server_state.json"
OUT = r"D:\FSTDD003\.fstdd\_daemon_tmp\reconcile.json"

st = json.load(open(STATE, encoding="utf-8"))
server = [f["name"] for f in st["files"]]
local = sorted(os.listdir(NOTICE_DIR))

def subject(fname):
    m = re.match(r"^FSTDD003[收复]-(.+)\.md$", fname)
    if m:
        return m.group(1)
    return fname

TRAIL = ["要求说明", "要求", "说明", "补发", "硬时限", "通知", "事宜", "回执催办", "的"]

def strip_trail(s):
    core = s
    changed = True
    while changed:
        changed = False
        for t in TRAIL:
            if core.endswith(t) and len(core) > len(t):
                core = core[: -len(t)]
                changed = True
    return core

PREFIX_STRIP = ["窗口-", "phase1-窗口-", "phase1-"]

def norm_date(s):
    s = re.sub(r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", s)
    return s

def strip_prefix(s):
    for p in sorted(PREFIX_STRIP, key=len, reverse=True):
        if s.startswith(p):
            return s[len(p):]
    return s

def canonical(s):
    s = strip_trail(s)
    s = norm_date(s)
    s = strip_prefix(s)
    return s

def match(x, y):
    if x == y:
        return "exact"
    if x in y or y in x:
        return "substr"
    if strip_trail(x) == strip_trail(y):
        return "trail"
    nx, ny = strip_trail(x), strip_trail(y)
    if nx == ny or nx in ny or ny in nx:
        return "trail-substr"
    cx, cy = canonical(x), canonical(y)
    if cx == cy:
        return "canonical"
    if cx and cy and (cx in cy or cy in cx):
        return "canonical-substr"
    return None

recv = sorted(f for f in server if f.startswith("FSTDD003收-"))
resp = sorted(f for f in local if f.startswith("FSTDD003复-"))
local_recv = sorted(f for f in local if f.startswith("FSTDD003收-"))

pending = []
matched_detail = []
for r in recv:
    x = subject(r)
    best = None
    for l in resp:
        y = subject(l)
        m = match(x, y)
        if m:
            best = (l, m)
            break
    if best:
        matched_detail.append({"收": r, "复": best[0], "type": best[1]})
    else:
        pending.append(r)

orphan_resp = [l for l in resp if not any(m["复"] == l for m in matched_detail)]

result = {
    "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "server_total": len(server),
    "server_收": len(recv),
    "server_复": len([f for f in server if f.startswith("FSTDD003复-")]),
    "local_收": len(local_recv),
    "local_复": len(resp),
    "matched": len(matched_detail),
    "pending": pending,
    "matched_detail": matched_detail,
    "orphan_resp": orphan_resp,
    "server_only": sorted(set(server) - set(local)),
    "local_only": sorted(set(local) - set(server)),
}
json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== RECONCILE ===")
print("server total=%d, server 收=%d, server 复=%d, local 收=%d, local 复=%d" %
      (len(server), len(recv), result["server_复"], len(local_recv), len(resp)))
print("matched=%d, PENDING=%d" % (len(matched_detail), len(pending)))
print("--- PENDING (need receipt) ---")
for p in pending:
    print("  *", p)
print("--- MATCH TYPE COUNTS ---")
print(dict(Counter(m["type"] for m in matched_detail)))
print("--- NON-EXACT MATCHES ---")
for m in matched_detail:
    if m["type"] != "exact":
        print("  [%s] %s  <->  %s" % (m["type"], m["收"], m["复"]))
print("--- server_only ---")
for f in result["server_only"]:
    print("  S>", f)
print("--- local_only ---")
for f in result["local_only"]:
    print("  L>", f)
