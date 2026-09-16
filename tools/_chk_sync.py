# -*- coding: utf-8 -*-
"""临时脚本：检查本地与 D 盘稳定副本的 guard.py 是否都含 Guard 修复。"""
from pathlib import Path

local = Path(r"C:/Users/Administrator/WorkBuddy AI/2026-09-14-18-36-54/stdd-repo/upstream/fstdd/cli/commands/guard.py")
dstab = Path(r"D:/Programs/DKK_Fstdd/upstream/fstdd/cli/commands/guard.py")

for name, p in (("本地 stdd-repo", local), ("D 盘稳定副本", dstab)):
    if not p.exists():
        print(f"[{name}] 文件不存在: {p}")
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    print(f"[{name}]")
    print(f"   含 _write_guard_settings : {'_write_guard_settings' in t}")
    print(f"   含 codebuddy 分支        : {'.codebuddy' in t}")
    bare = '"stdd guard check' in t
    print(f"   仍含裸 stdd guard 命令   : {bare}")
