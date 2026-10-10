#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate 检查项 `upstream-patches` — 参考实现（P3 BUILD 切片 3）
================================================================
对应 spec: specs/spec-validate-upstream-patches.md（决策 D-1：结构级）

行为：
  SC-1 登记表存在、表头完整、行可解析 → 通过；表体为空 → 通过并提示「登记项为 0」
  SC-2 登记行指向的文件不存在 → 失败(1)，指明缺失路径
  SC-3 登记表缺失或表头不完整 → 失败(1)，提示先登记
  非行为（T3.4 锁定）：不扫描 upstream/ 找「未登记修改」，不比对哈希（D-2 切出）

退出码：0=通过 / 1=检查失败 / 2=用法错误
接入方式（仓库侧按实读调整）：upstream/fstdd/ 的 validate 命令组以子进程调用本脚本，
或将其逻辑内联为同构检查函数；接口契约 = 退出码 + stdout 末行 [PASS]/[FAIL]。
"""
import argparse
import re
import sys
from pathlib import Path

REGISTRY = "docs/UPSTREAM_PATCHES.md"
# 规范列名（spec-patches-registry SC-2）；第 5 列接受两种写法
CANONICAL_HEADER = ["#", "文件", "行号", "修改原因", "关联上游issue或PR", "登记日期", "登记人", "预期回退版本"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


HEADER_ALIAS = {"关联上游issue/pr": _norm("关联上游issue或PR")}


def parse_registry(text: str):
    """返回 (header_cells, rows) ；rows = 去分隔线/空行后的表格行（List[List[str]]）。"""
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 1:
        return None, None
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    rows, seen_sep = [], False
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            seen_sep = True
            continue
        if seen_sep:
            rows.append(cells)
    return header, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    reg = repo / REGISTRY

    if not reg.is_file():
        print(f"[FAIL] 登记表缺失：{REGISTRY}。修改 upstream/ 前必须先登记。")
        return 1

    header, rows = parse_registry(reg.read_text(encoding="utf-8", errors="replace"))
    norm_header = [HEADER_ALIAS.get(_norm(h), _norm(h)) for h in (header or [])]
    if norm_header != [_norm(c) for c in CANONICAL_HEADER]:
        print(f"[FAIL] 登记表表头不完整或不规范，应为 8 列：{' | '.join(CANONICAL_HEADER)}")
        return 1

    if not rows:
        print(f"[PASS] 登记表结构正常（登记项为 0）")
        return 0

    missing = []
    for i, cells in enumerate(rows, 1):
        if len(cells) != len(CANONICAL_HEADER):
            print(f"[FAIL] 第 {i} 行列数 {len(cells)} ≠ 8")
            return 1
        path = cells[1]
        if not (repo / path).exists():
            missing.append(path)
    if missing:
        for p in missing:
            print(f"[FAIL] 登记的文件不存在：{p}")
        return 1
    print(f"[PASS] 登记表结构正常（登记项 {len(rows)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
