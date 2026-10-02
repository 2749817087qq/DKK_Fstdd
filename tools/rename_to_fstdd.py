# -*- coding: utf-8 -*-
"""Fstdd 改名替换引擎（切片 S1：标识层）。

核心设计：**单次扫描替换**。

上一版手工改名失败的根因不是粗心，而是算法缺陷：逐条 `str.replace` 顺序执行时，
前一条的输出会进入后一条的输入域 —— `STDD_SRC → FSTDD_SRC` 之后，
规则 `STDD → FSTDD` 又在自己的产物上匹配一次，产出 `FFSTDD_SRC`。

本实现用一条正则 alternation + `re.sub(callback)`：**对原串只扫描一遍**，
替换结果不再进入匹配域，从算法上根除自匹配。

用法：
    python tools/rename_to_fstdd.py --dry-run   # 预览（默认）
    python tools/rename_to_fstdd.py --apply     # 实际写入
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 排除目录：upstream/（另属切片 S2）、.git、数据目录、缓存
EXCLUDE_DIRS = {"upstream", ".git", ".stdd", ".fstdd", "__pycache__", ".claude"}

# 参与改名的扩展名
EXTS = {".md", ".py", ".sh", ".ps1", ".yaml", ".yml", ".txt", ".json", ".toml"}

# 不参与改名的文件：
#   rename_to_fstdd.py  — 本替换脚本自身
#   verify_rename.py    — 断言脚本，内含被检测字符串的字面量与检测逻辑，
#                         一旦被替换即失去检测能力（实测踩过：其内 FFSTDD_ 字样
#                         曾导致 TC-001 误判为通过）
EXCLUDE_FILES = {"rename_to_fstdd.py", "verify_rename.py"}

# 替换规则 —— **顺序敏感，长串必须在短串之前**。
# 每条是 (正则模式, 替换值, 标签)。用正则而非字面量，便于加边界。
#
# ⚠️ 左边界 (?<![A-Za-z]) 不可省：
#   它保证「已经改好的名字」不会被再次匹配。实测缺少它时引擎**非幂等**：
#     'FSTDD_SRC'        -> 'FFSTDD_SRC'
#     'fstdd-understand' -> 'ffstdd-understand'
#   即规则 STDD→FSTDD 会命中自己产物里的 STDD。这与上次失败的成因同类
#   （规则自匹配），只是从「规则之间」变成了「规则与既有产物之间」。
# 右边界只在短串规则上需要（见最后一条），长串规则天然不会误伤。
_L = r"(?<![A-Za-z])"

RULES: list[tuple[str, str, str]] = [
    # 1) skill 名（长串优先）
    (_L + r"stdd-understand", "fstdd-understand", "skill 名"),
    (_L + r"stdd-spec", "fstdd-spec", "skill 名"),
    (_L + r"stdd-build", "fstdd-build", "skill 名"),
    (_L + r"stdd-deliver", "fstdd-deliver", "skill 名"),
    (_L + r"stdd-upgrade", "fstdd-upgrade", "skill 名"),
    (_L + r"stdd-fin", "fstdd-fin", "skill 名"),
    (_L + r"stdd-slice", "fstdd-slice", "触发词"),
    (_L + r"stdd-verify", "fstdd-verify", "触发词"),
    # 2) 项目名
    (r"DKKstdd-experiences", "Fstdd-experiences", "仓库名"),
    (r"DKKstdd", "Fstdd", "仓库名"),
    # 3) 环境变量（长串优先于裸 STDD）
    (_L + r"STDD_LOCAL_POLICY", "FSTDD_LOCAL_POLICY", "哨兵"),
    (_L + r"STDD_SRC", "FSTDD_SRC", "环境变量"),
    (_L + r"STDD_OUT", "FSTDD_OUT", "环境变量"),
    (_L + r"STDD_PY", "FSTDD_PY", "环境变量"),
    (_L + r"STDD_CLI", "FSTDD_CLI", "环境变量"),
    # 4) CLI 路径
    (r"bin/stdd", "bin/fstdd", "CLI 入口"),
    (r"bin\\stdd", "bin\\fstdd", "CLI 入口"),
    # 5) 方法论名（大写，须在环境变量规则之后）—— 加左边界防自匹配
    (_L + r"STDD", "FSTDD", "方法论名"),
    # 6) 小写独立标识 —— 左右边界保护，且排除路径片段
    (r"(?<![\w./\\-])stdd(?![\w-])", "fstdd", "独立标识"),
]

# 编译为**单条** alternation（顺序即优先级，Python re 取最先匹配的分支）
_PATTERN = re.compile("|".join(f"(?:{p})" for p, _, _ in RULES))
_LABEL = {i: label for i, (_, _, label) in enumerate(RULES)}


def _repl(m: re.Match) -> str:
    """按命中的分支取替换值 —— 关键是直接返回，不重新进入匹配。"""
    for i, (pat, new, _) in enumerate(RULES):
        if re.fullmatch(pat, m.group(0)):
            return new
    return m.group(0)


def apply_text(text: str) -> tuple[str, dict]:
    """对文本执行单次扫描替换，返回 (新文本, 统计)。"""
    stats: dict[str, int] = {}
    # 统计：先数各规则命中数（仅用于报告，不影响替换）
    for pat, _, label in RULES:
        n = len(re.findall(pat, text))
        if n:
            stats[label] = stats.get(label, 0) + n
    new = _PATTERN.sub(_repl, text)
    return new, stats


def iter_targets():
    for p in sorted(REPO.rglob("*")):
        if not p.is_file() or p.suffix not in EXTS:
            continue
        rel = p.relative_to(REPO)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.name in EXCLUDE_FILES:
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认仅预览）")
    args = ap.parse_args()

    print("=" * 62)
    print(f" Fstdd 改名（切片 S1）— {'写入模式' if args.apply else '预览模式'}")
    print("=" * 62)

    changed = 0
    total_hits = 0
    for p in iter_targets():
        src = p.read_text(encoding="utf-8", errors="replace")
        out, stats = apply_text(src)
        if out == src:
            continue
        hits = sum(stats.values())
        changed += 1
        total_hits += hits
        detail = ", ".join(f"{k}×{v}" for k, v in sorted(stats.items()))
        print(f"  {p.relative_to(REPO)}")
        print(f"      {hits} 处：{detail}")
        if args.apply:
            p.write_text(out, encoding="utf-8", newline="\n")

    print()
    print(f"共 {changed} 个文件，{total_hits} 处替换")
    if not args.apply:
        print("[预览] 未写入。加 --apply 执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
