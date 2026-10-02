import json, os, re, datetime
from collections import Counter

NOTICE_DIR = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"
OUT = r"D:\FSTDD003\.fstdd\_daemon_tmp\reconcile_round.json"

# Server list from current session's SSH output (43 收 + 42 复 = 85 files with FSTDD003 prefix)
# We'll reconstruct from what we already have plus the 3 new pulls
server_files = [
    # 43 收-*
    "FSTDD003收-F2K-002-经验收集统一要求-20260929.md",
    "FSTDD003收-FSTDD标准升级同步规程v1.md",
    "FSTDD003收-FSTDD标准升级同步规程v1-回执催办.md",
    "FSTDD003收-inbox地址变更.md",
    "FSTDD003收-inbox鉴权上线.md",
    "FSTDD003收-phase1-baseURL已确定.md",
    "FSTDD003收-phase1-launch.md",
    "FSTDD003收-phase1-平台防护通告.md",
    "FSTDD003收-Phase1执行方式增补-任务卡驱动.md",
    "FSTDD003收-phase1-更正8080不可用.md",
    "FSTDD003收-phase1-窗口-2026-09-24-14.md",
    "FSTDD003收-phase1-窗口-2026-09-26-10.md",
    "FSTDD003收-phase1-窗口-2026-09-26-20.md",
    "FSTDD003收-phase1-窗口-2026-09-26-22.md",
    "FSTDD003收-phase1-窗口-20260927-10.md",
    "FSTDD003收-phase1-窗口-20260927-14.md",
    "FSTDD003收-phase1-窗口-20260927-20.md",
    "FSTDD003收-phase1-窗口-20260927-22.md",
    "FSTDD003收-phase1-窗口-20260928-14.md",
    "FSTDD003收-phase1-窗口-20260929-14.md",
    "FSTDD003收-phase1-节奏变更-2小时小闭环.md",
    "FSTDD003收-phase1-访问限制已撤除.md",
    "FSTDD003收-phase1-通告二-反爬检测与行为约束.md",
    "FSTDD003收-seed口径申报.md",
    "FSTDD003收-交付物已入仓.md",
    "FSTDD003收-凭证安装硬时限.md",
    "FSTDD003收-凭证验证补充.md",
    "FSTDD003收-助001接入与SOP收尾.md",
    "FSTDD003收-升级路径修复方案.md",
    "FSTDD003收-升级验证.md",
    "FSTDD003收-协作开发-S2S3.md",
    "FSTDD003收-口径更正-当前只做1个账号.md",
    "FSTDD003收-工作量与资源规划要求.md",
    "FSTDD003收-接入授权.md",
    "FSTDD003收-撤回令-伪造署名指令.md",
    "FSTDD003收-澄清问询-凭证验证补充.md",
    "FSTDD003收-状态盘点.md",
    "FSTDD003收-经验回传要求.md",
    "FSTDD003收-编写《per-node 接入 SOP》+ 跨平台验证.md",
    "FSTDD003收-自动化率提升.md",
    "FSTDD003收-账号规模扩展预告.md",
    "FSTDD003收-通道演练.md",
]

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

recv = sorted(server_files)
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
    "server_收_count": len(recv),
    "local_收_count": len(local_recv),
    "local_复_count": len(resp),
    "matched": len(matched_detail),
    "pending": pending,
    "match_type_counts": dict(Counter(m["type"] for m in matched_detail)),
}
json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== RECONCILE (this round) ===")
print("server 收-: %d, local 复-: %d, local 收-: %d" % (len(recv), len(resp), len(local_recv)))
print("MATCHED: %d, PENDING: %d" % (len(matched_detail), len(pending)))
print("Match types:", Counter(m["type"] for m in matched_detail))
if pending:
    print("PENDING (need receipt):")
    for p in pending:
        print("  *", p)
print("Non-exact matches (naming variants):")
for m in matched_detail:
    if m["type"] != "exact":
        print("  [%s] %s <-> %s" % (m["type"], m["收"], m["复"]))
