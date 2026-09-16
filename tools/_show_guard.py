# -*- coding: utf-8 -*-
"""临时脚本：打印项目里 Guard hook 的 matcher 与 command（验证是否为绝对路径调用）。"""
import json
from pathlib import Path

for sub in (".claude", ".codebuddy"):
    p = Path.cwd() / sub / "settings.local.json"
    if not p.exists():
        print(f"[{sub}] 未生成")
        continue
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[{sub}] 读取失败: {exc}")
        continue
    hooks = d.get("hooks", {}).get("PreToolUse", [])
    if not hooks:
        print(f"[{sub}] 无 PreToolUse hook")
        continue
    for h in hooks:
        print(f"[{sub}] matcher = {h.get('matcher')}")
        for hh in h.get("hooks", []):
            print(f"   command = {hh.get('command')}")