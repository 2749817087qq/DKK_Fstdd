import subprocess, os, re, sys, json
local_dir = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"
def local_files(prefix):
    return sorted(f for f in os.listdir(local_dir) if f.startswith(prefix))
shou = local_files("FSTDD003收-")
fu   = local_files("FSTDD003复-")

# Extract reply_to refs from all 复 files
reply_ref = re.compile(r"reply_to:\s*([^\n]+)")
refs = {}
for f in fu:
    p = os.path.join(local_dir, f)
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except Exception as e:
        txt = ""
    m = reply_ref.search(txt)
    refs[f] = m.group(1).strip() if m else ""

TRAILING = ("要求说明","要求","说明","补发","硬时限","通知","事宜","的","-回执催办","回执催办")
def core(name):
    n = name.replace("FSTDD003收-","").replace("FSTDD003复-","")
    for t in TRAILING:
        if n.endswith(t):
            n = n[: -len(t)]
    return n

matched = {}
unmatched = []
for s in shou:
    s_stem = s.replace("FSTDD003收-","").replace(".md","")
    s_core = core(s)
    found = None; kind = None
    # 1 exact
    if f"FSTDD003复-{s_stem}.md" in fu:
        found = f"FSTDD003复-{s_stem}.md"; kind = "exact"
    else:
        for f in fu:
            f_stem = f.replace("FSTDD003复-","").replace(".md","")
            if s_stem == f_stem or s_stem in f_stem or f_stem in s_stem:
                found = f; kind = "substring"; break
            if core(f) == s_core:
                found = f; kind = "core"; break
    if not found:
        for f in fu:
            if s_stem in refs.get(f,"") or s_stem.replace("FSTDD003收-","") in refs.get(f,"").replace("FSTDD003收-",""):
                found = f; kind = "reply_to"; break
    if found:
        matched[s] = (found, kind)
    else:
        unmatched.append(s)

print(f"Total 收-: {len(shou)}, 复-: {len(fu)}")
print(f"Matched: {len(matched)}, Unmatched: {len(unmatched)}")
for s,(f,k) in matched.items():
    pass  # summary only
from collections import Counter
print("Match kinds:", Counter(v[1] for v in matched.values()))
if unmatched:
    print("UNMATCHED:")
    for u in unmatched: print(" -", u)
else:
    print("ALL RECONCILED")
