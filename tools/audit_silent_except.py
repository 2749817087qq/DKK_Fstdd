# -*- coding: utf-8 -*-
"""audit_silent_except.py — 裸 except 吞异常扫描器（silent-failure-audit Slice 1）。

只读扫描 upstream/fstdd 与 tools 下的 Python 源码，找出「except 捕获后
静默吞掉（pass / continue / return 空值）」的点。审计表
（audit/except-points.yaml）基于本扫描器产出；测试用同一扫描器做零漂移校验。

用法:
    python tools/audit_silent_except.py            # 人类可读摘要
    python tools/audit_silent_except.py --json     # 完整 JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = ("upstream/fstdd", "tools")

# except 子句：裸 except / except Exception / except BaseException（可选捕获为 e 再不用）
_SWALLOW = re.compile(r"^\s*except\s*(?:Exception|BaseException)\s*:?\s*$")
# 吞掉的第一条语句（块内允许空行与注释）
_TRIVIAL = re.compile(r"^\s*(?:pass|continue|return\s+(?:None|\[\]|\{\}|False|0|''|\"\"))\s*$")


def scan(roots=DEFAULT_ROOTS, repo: Path = REPO) -> list[dict]:
    """扫描吞异常点，返回 [{file, line, stmt, handler}]（file 为 repo 相对 posix 路径）。"""
    points: list[dict] = []
    for root in roots:
        base = repo / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            rel = p.relative_to(repo).as_posix()
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, ln in enumerate(lines):
                if not _SWALLOW.match(ln):
                    continue
                # 块内第一条实质语句
                for j in range(i + 1, min(i + 4, len(lines))):
                    s = lines[j].strip()
                    if not s or s.startswith("#"):
                        continue
                    if _TRIVIAL.match(lines[j]):
                        points.append({
                            "file": rel,
                            "line": i + 1,
                            "stmt": s,
                            "handler": ln.strip(),
                        })
                    break
    return points


def _default_table(repo: Path) -> Path | None:
    """默认审计表：changes|archive 下任意 audit/except-points.yaml，changes 优先。"""
    hits = []
    for base in ("changes", "archive"):
        d = repo / ".fstdd" / base
        if d.is_dir():
            hits.extend(sorted(d.glob("*/audit/except-points.yaml")))
    return hits[0] if hits else None


def check(repo: Path = REPO, table_path: Path | None = None,
          roots=DEFAULT_ROOTS) -> tuple[bool, list[str]]:
    """哨兵模式：白名单（审计表）外的新增裸 except 判红。

    fail-loud 设计（B3 教训）：表缺失/不可解析 = 判红，绝不允许默过。
    已修复（表有实况无）= 放行但提示刷新。

    Returns (ok, messages)。
    """
    if table_path is None:
        table_path = _default_table(repo)
        if table_path is None:
            return False, ["审计表缺失（.fstdd/changes|archive/*/audit/except-points.yaml 均未找到）"]

    if not table_path.is_file():
        return False, [f"审计表缺失: {table_path}"]
    try:
        data = yaml_safe_load(table_path)
    except Exception as e:  # noqa: BLE001 — 哨兵自身失效必须 fail-loud
        return False, [f"审计表不可解析: {table_path} ({e})"]
    if not isinstance(data, dict) or not isinstance(data.get("points"), list):
        return False, [f"审计表结构非法（缺 points 列表）: {table_path}"]

    from collections import defaultdict

    groups: dict = defaultdict(lambda: {"live": [], "table": []})
    for p in scan(roots=roots, repo=repo):
        key = (p["file"], p["stmt"].strip(), p["handler"].strip())
        groups[key]["live"].append(int(p["line"]))
    for t in data["points"]:
        key = (str(t.get("file", "")), str(t.get("stmt", "")).strip(),
               str(t.get("handler", "")).strip())
        try:
            groups[key]["table"].append(int(t.get("line", 0)))
        except (TypeError, ValueError):
            return False, [f"审计表条目行号非法: {t.get('id', '?')} -> {t.get('line')!r}"]

    LINE_TOL = 5  # 与 test_except_audit 的容差一致
    uncovered: list = []
    stale: list = []
    for (f, s, h), g in groups.items():
        table_lines = sorted(g["table"])
        used: set = set()
        for ll in sorted(g["live"]):
            best = None
            for ti, tl in enumerate(table_lines):
                if ti in used:
                    continue
                d = abs(ll - tl)
                if d <= LINE_TOL and (best is None or d < best[1]):
                    best = (ti, d)
            if best is None:
                uncovered.append(f"未覆盖的吞异常点: {f}:{ll} [{h} -> {s}]"
                                 "（白名单外新增，请分类入册或移除）")
            else:
                used.add(best[0])
        for ti, tl in enumerate(table_lines):
            if ti not in used:
                stale.append(f"失效审计条目（实况已不存在）: {f}:{tl} [{h}] — 请刷新审计表")

    msgs = uncovered + stale
    return (not uncovered), msgs


def yaml_safe_load(path: Path):
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="裸 except 吞异常扫描器")
    ap.add_argument("--json", action="store_true", help="输出完整 JSON")
    ap.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    ap.add_argument("--check", action="store_true",
                    help="哨兵模式：白名单外新增即 exit 1")
    args = ap.parse_args(argv)

    if args.check:
        ok, msgs = check(roots=tuple(args.roots))
        for m in msgs:
            print(m)
        print(f"哨兵结果: {'通过' if ok else '未通过'} ({len(msgs)} 条提示)")
        return 0 if ok else 1

    pts = scan(roots=tuple(args.roots))
    if args.json:
        print(json.dumps(pts, ensure_ascii=False, indent=1))
    else:
        files = {}
        for p in pts:
            files.setdefault(p["file"], []).append(p)
        print(f"吞异常点: {len(pts)} 处 / {len(files)} 个文件")
        for f in sorted(files, key=lambda f: -len(files[f])):
            print(f"  {len(files[f]):3d}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
