# -*- coding: utf-8 -*-
"""tests/test_version_nomenclature.py

change: 2026-10-05-upstream-baseline-alignment（capability: version-nomenclature）
TDD 切片 1：活体声明面版本轴显式化（NOTICE / README / fstdd-fin / INSTALL_NOTES）。

版本三轴口径（design.md 决策 1）：
  E = 上游外部项目最新发布（v3.0.5，仅对标锚）
  K = 本仓 vendored 内核（upstream/，当前 3.1.0）
  R = 本仓发行版（当前 3.3.4）

断言原则（test-plan §1.2）：双向 —— 既断言正确轴在位，也断言错误串不存在。
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

NOTICE = ROOT / "NOTICE.md"
README = ROOT / "README.md"
FIN_SKILL = ROOT / "skills" / "fstdd-fin" / "SKILL.md"
INSTALL_NOTES = ROOT / "docs" / "WORKBUDDY_INSTALL_NOTES.md"

# 活体声明面（扫描范围显式列举；刻意不含 upstream/ 上游自有文档与历史/临时区）
LIVE_SURFACES = [NOTICE, README, FIN_SKILL, INSTALL_NOTES]

E_MARKERS = ("上游最新发布", "上游发布", "上游 release")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j]


# ---------------------------------------------------------------------------
# TC-VNOM-001 — NOTICE §1 无自相矛盾的版本声明
# ---------------------------------------------------------------------------
def test_notice_section1_version_axes_no_contradiction():
    """TC-VNOM-001 / SC-001：NOTICE §1 内核轴写 K，E 轴标明「上游最新发布」。"""
    sec = _section(_read(NOTICE), "## 1. 上游项目：FSTDD", "\n## 2. 第三方参考")
    assert "3.1.0" in sec, "NOTICE §1 未写出内核轴 K=3.1.0"
    assert "上游最新发布" in sec, "NOTICE §1 未把 E 轴标明为「上游最新发布」"
    assert "UPSTREAM_BASELINE.md" in sec, "NOTICE §1 未链接基线快照 docs/UPSTREAM_BASELINE.md"
    # 双向：任何出现 3.0.5 的行必须同时带 E 轴标注（不得指称内核）
    for line in sec.splitlines():
        if "3.0.5" in line:
            assert any(m in line for m in E_MARKERS), f"NOTICE §1 中 3.0.5 未标明 E 轴: {line!r}"
    # 错误串不存在
    assert "上游版本号见" not in sec, "NOTICE §1 仍把内核误称「上游版本号」"


# ---------------------------------------------------------------------------
# TC-VNOM-002 — README 头部两轴并列
# ---------------------------------------------------------------------------
def test_readme_head_has_both_axes():
    """TC-VNOM-002 / SC-002：README 头部同时呈现 E 轴徽章与 K 轴徽章。"""
    head = "\n".join(_read(README).splitlines()[:20])
    assert "v3.0.5" in head, "README 头部缺 E 轴数字 v3.0.5"
    assert "3.1.0" in head, "README 头部缺 K 轴数字 3.1.0"
    assert head.count("img.shields.io/badge") >= 3, "README 徽章数不足（应含 E/K 两轴徽章）"
    for line in head.splitlines():
        if "v3.0.5" in line:
            assert "release" in line.lower() or "上游" in line, \
                f"README 中含 v3.0.5 的行未标 E 轴（release/上游）语义: {line!r}"
        if "3.1.0" in line:
            assert "kernel" in line.lower() or "内核" in line, \
                f"README 中含 3.1.0 的行未标 K 轴（kernel/内核）语义: {line!r}"
    # 上游 MIT 署名事实保留
    assert "leonai42/stdd" in head and "MIT" in head, "README 头部丢失上游 MIT 署名"


# ---------------------------------------------------------------------------
# TC-VNOM-003 — fstdd-fin frontmatter 与 sources 用内核轴
# ---------------------------------------------------------------------------
def test_fstdd_fin_frontmatter_uses_kernel_axis():
    """TC-VNOM-003 / SC-003：stdd_version = K(3.1.0)，sources 指向 K 并以 E 溯源。"""
    content = _read(FIN_SKILL)
    fm = _section(content, "---", "\n---\n") if content.startswith("---") else content
    assert re.search(r'^stdd_version:\s*"3\.1\.0"\s*$', fm, re.M), \
        "fstdd-fin 的 stdd_version 未取内核轴 K=3.1.0（且须为纯 [0-9.]+）"
    assert re.search(r'^version:\s*"1\.0\.0"\s*$', fm, re.M), \
        "fstdd-fin 的 version 字段被改动（应保持 1.0.0）"
    assert "3.0.5-fin" not in content, "fstdd-fin 仍含内核轴错写 -fin.2 后缀"
    assert "方法论基底" in content and "3.1.0" in content, "sources 方法论基底未指向内核轴 K"
    for line in content.splitlines():
        if "3.0.5" in line:
            assert any(m in line for m in E_MARKERS), f"fstdd-fin 中 3.0.5 未标明 E 轴: {line!r}"


# ---------------------------------------------------------------------------
# TC-VNOM-004 — 安装说明版本表述按轴落位
# ---------------------------------------------------------------------------
def test_install_notes_version_axes():
    """TC-VNOM-004 / SC-004：INSTALL_NOTES 每处版本按轴落位，无「内核=3.0.5」。"""
    content = _read(INSTALL_NOTES)
    for line in content.splitlines():
        if "3.0.5" in line:
            assert any(m in line for m in E_MARKERS) or "上游" in line, \
                f"INSTALL_NOTES 中 3.0.5 未标明 E 轴: {line!r}"
    assert "V3.0.5 三阶段合一" not in content, \
        "INSTALL_NOTES 仍把内核/方法学形态标为 V3.0.5（歧义版本词）"


# ---------------------------------------------------------------------------
# TC-VNOM-005 — 活体声明面零矛盾定向扫描
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path,forbidden", [
    (NOTICE, "（`3.0.5`）"),                       # 内核注记写 3.0.5
    (NOTICE, "上游版本号见"),                      # 把 K 称「上游版本号」
    (README, "upstream-leonai42%2Fstdd%20v3.0.5"),  # 未标轴徽章原串
    (FIN_SKILL, "3.0.5-fin.2"),                    # stdd_version 错写 E + 后缀
    (FIN_SKILL, "方法论基底: FSTDD V3.0.5"),        # 方法论基底错写 E
    (INSTALL_NOTES, "master 分支，V3.0.5，MIT"),     # 未标轴 E 数字
    (INSTALL_NOTES, "V3.0.5 三阶段合一"),
])
def test_live_surfaces_no_kernel_written_as_e(path, forbidden):
    """TC-VNOM-005 / SC-005：活体声明面「内核写作 3.0.5」定向扫描命中数为 0。"""
    assert path.exists(), f"活体声明面缺失: {path}"
    assert forbidden not in _read(path), \
        f"{path.name} 残留把内核/方法学误写为 E 的串: {forbidden!r}"


def test_scan_scope_is_live_surfaces_only():
    """TC-VNOM-005 范围断言：扫描对象恰为 5 个活体声明面，不含 upstream/ 与历史/临时区。"""
    names = {p.name for p in LIVE_SURFACES}
    assert names == {"NOTICE.md", "README.md", "SKILL.md", "WORKBUDDY_INSTALL_NOTES.md"}
    for p in LIVE_SURFACES:
        assert "upstream" not in p.parts, f"扫描范围误含 upstream/ 上游自有文档: {p}"