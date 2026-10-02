import os, re

LOCAL = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"

def ls_files(prefix):
    return sorted(n for n in os.listdir(LOCAL) if n.startswith(prefix) and n.endswith(".md"))

recv = ls_files("FSTDD003收-")
reply = ls_files("FSTDD003复-")

def topic(name, tag):
    return name[len(tag):-3]

recv_t = [topic(n, "FSTDD003收-") for n in recv]
reply_t = [topic(n, "FSTDD003复-") for n in reply]

# Additional modifiers per this round's observed naming convention
SUFFIX_STRIP = ["要求说明", "要求", "说明", "补发", "硬时限", "通知", "事宜", "的"]
MIDDLE_STRIP = ["窗口", "任务", "回执"]  # also can appear mid-name

def normalize(t):
    t = t.strip()
    changed = True
    while changed:
        changed = False
        for s in SUFFIX_STRIP:
            if t.endswith(s) and len(t) > len(s):
                t = t[:-len(s)]; changed = True; break
    # also drop a "窗口-" or "-窗口" fragment
    t = re.sub(r"[-_]窗口[-_]?", "-", t).strip("-")
    return t

def reply_to_hint(path):
    """Some 复 files carry reply_to: FSTDD003收-<...>.md frontmatter; use as authoritative hint."""
    try:
        with open(os.path.join(LOCAL, path), encoding="utf-8", errors="ignore") as f:
            head = f.read(1500)
        m = re.search(r"reply_to:\s*FSTDD003收-([^\s\"']+)\.md", head)
        if m: return m.group(1)
    except Exception:
        pass
    return None

def match(x, reply_names):
    for yn in reply_names:
        yt = topic(yn, "FSTDD003复-")
        # authoritative: reply_to in frontmatter
        if reply_to_hint(yn) == x:
            return yn, "reply_to"
        if x == yt:
            return yn, "exact"
        if x in yt or yt in x:
            return yn, "substring"
        nx = normalize(x); ny = normalize(yt)
        if nx and ny and (nx == ny or nx in ny or ny in nx):
            return yn, "normalized"
    return None, None

# per-round audit output
matched_by_kind = {}
unmatched = []
for r in recv_t:
    rn, kind = match(r, reply)
    if rn is None:
        unmatched.append(r)
    else:
        matched_by_kind.setdefault(kind, []).append((r, topic(rn, "FSTDD003复-")))

print(f"TOTAL  收-={len(recv)}  复-={len(reply)}")
for k, items in matched_by_kind.items():
    print(f"[{k}] {len(items)}")
    for r, y in items:
        if k != "reply_to" and r != y:
            print(f"     收-{r} <-> 复-{y}")
print(f"\nUNMATCHED (needs 回执): {len(unmatched)}")
for u in unmatched:
    print(f"  - 收-{u}")
