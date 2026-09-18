# -*- coding: utf-8 -*-
"""TC-GRD-001..005 — 裸 except 哨兵（--check 模式）：白名单外新增即红、
哨兵自身失效 fail-loud、同文件重复语句不误报、失效条目提示刷新。

哨兵 = tools/audit_silent_except.py --check。
设计要点（B3 教训）：检查器自己失效（表缺失/不可读）必须 exit 1 且说明原因，
绝不允许「检查器没跑成 = 检查通过」。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "tools" / "audit_silent_except.py"


def _load():
    spec = importlib.util.spec_from_file_location("audit_silent_except", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _table_path() -> Path:
    for base in ("changes", "archive"):
        p = (REPO / ".fstdd" / base / "2026-09-18-silent-failure-audit"
             / "audit" / "except-points.yaml")
        if p.is_file():
            return p
    raise FileNotFoundError("审计表不存在")


def _make_repo(tmp_path: Path, code: str) -> Path:
    """构造最小假仓库：一个含吞异常点的源码文件 + 空包结构。"""
    (tmp_path / "upstream" / "fstdd").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    (tmp_path / "upstream" / "fstdd" / "m.py").write_text(code, encoding="utf-8")
    return tmp_path


def _table_for(points: list[dict]) -> Path:
    return {"meta": {"title": "t"}, "points": points}


# --------------------------------------------------------------------------- #
# TC-GRD-001 — 当前仓库全点白名单覆盖：--check 通过
# --------------------------------------------------------------------------- #

def test_grd_001_check_passes_on_current_repo():
    mod = _load()
    ok, msgs = mod.check(repo=REPO, table_path=_table_path())
    assert ok, f"哨兵在干净仓库误报: {msgs}"
    assert not [m for m in msgs if "未覆盖" in m], msgs


# --------------------------------------------------------------------------- #
# TC-GRD-002 — 新增裸 except（白名单外）→ 红，且点名位置
# --------------------------------------------------------------------------- #

def test_grd_002_new_bare_except_fails_loud(tmp_path):
    mod = _load()
    repo = _make_repo(tmp_path, "def f():\n    try:\n        x = 1\n    except Exception:\n        pass\n")
    table = tmp_path / "t.yaml"
    table.write_text(yaml.safe_dump(_table_for([]), allow_unicode=True), encoding="utf-8")
    ok, msgs = mod.check(repo=repo, table_path=table)
    assert not ok, "白名单外新增裸 except 必须判红"
    joined = "\n".join(msgs)
    assert "m.py" in joined and "未覆盖" in joined, msgs


# --------------------------------------------------------------------------- #
# TC-GRD-003 — 已修复（记录存在但实况消失）→ 放行 + 提示刷新，不误红
# --------------------------------------------------------------------------- #

def test_grd_003_fixed_point_warns_but_passes(tmp_path):
    mod = _load()
    code = "def f():\n    return 1\n"  # 实况已无吞异常点
    repo = _make_repo(tmp_path, code)
    table = tmp_path / "t.yaml"
    table.write_text(yaml.safe_dump(_table_for([
        {"id": "EA-901", "file": "upstream/fstdd/m.py", "line": 4,
         "stmt": "pass", "handler": "except Exception:",
         "classification": "意外吞错", "severity": "p2", "response": "加警告",
         "detection_path": True, "justification": "t"},
    ]), allow_unicode=True), encoding="utf-8")
    ok, msgs = mod.check(repo=repo, table_path=table)
    assert ok, f"已修复点不应判红: {msgs}"
    assert any("失效" in m or "刷新" in m for m in msgs), f"缺刷新提示: {msgs}"


# --------------------------------------------------------------------------- #
# TC-GRD-004 — 哨兵自身失效（表缺失/不可读）→ fail-loud，绝不允许默过
# --------------------------------------------------------------------------- #

def test_grd_004_missing_table_fails_loud(tmp_path):
    mod = _load()
    repo = _make_repo(tmp_path, "def f():\n    return 1\n")
    ok, msgs = mod.check(repo=repo, table_path=tmp_path / "不存在.yaml")
    assert not ok, "表缺失必须判红（fail-loud）"
    assert any("表" in m for m in msgs), msgs


def test_grd_004b_corrupt_table_fails_loud(tmp_path):
    mod = _load()
    repo = _make_repo(tmp_path, "def f():\n    return 1\n")
    bad = tmp_path / "bad.yaml"
    bad.write_text("::: not yaml :::", encoding="utf-8")
    ok, msgs = mod.check(repo=repo, table_path=bad)
    assert not ok, "表不可解析必须判红（fail-loud）"


# --------------------------------------------------------------------------- #
# TC-GRD-005 — 同文件多个相同语句（pass×N）按行号就近匹配，不误报
# --------------------------------------------------------------------------- #

def test_grd_005_duplicate_stmt_matched_by_line(tmp_path):
    mod = _load()
    code = (
        "def a():\n    try:\n        x\n    except Exception:\n        pass\n"
        "\n"
        "def b():\n    try:\n        y\n    except Exception:\n        pass\n"
    )
    repo = _make_repo(tmp_path, code)
    table = tmp_path / "t.yaml"
    # 只记录第二处（模拟第一处已修复）：行号 4 失效、11 有效
    table.write_text(yaml.safe_dump(_table_for([
        {"id": "EA-902", "file": "upstream/fstdd/m.py", "line": 11,
         "stmt": "pass", "handler": "except Exception:",
         "classification": "合理容错", "severity": None, "response": "放行",
         "detection_path": False, "justification": "t"},
    ]), allow_unicode=True), encoding="utf-8")
    ok, msgs = mod.check(repo=repo, table_path=table)
    assert not ok, "行 4 的白名单外 pass 必须判红（行 11 已覆盖不算数）"
    assert any("line 4" in m or ":4" in m for m in msgs), msgs
