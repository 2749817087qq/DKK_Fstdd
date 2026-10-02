# -*- coding: utf-8 -*-
"""TC-CONST-001..005 + TC-TMPL-001 — 宪法条款与模板双源一致性。

对应 `.fstdd/changes/2026-09-17-time-baseline/test-plan.md` 功能 5/6。
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = REPO_ROOT / "FSTDD_CONSTITUTION.md"
CONSTITUTION_COPY = REPO_ROOT / ".fstdd" / "memory" / "FSTDD_CONSTITUTION.md"


# --------------------------------------------------------------------------- #
# TC-CONST-001 — 存在 ### 7. 时间基线（编号连续）；含建立基线 / 观测时刻 / 违规后果
# --------------------------------------------------------------------------- #

def test_const_001_section7_time_baseline():
    text = CONSTITUTION.read_text(encoding="utf-8")
    sections = re.findall(r"^### (\d+)\. (.+)$", text, re.MULTILINE)
    nums = [int(n) for n, _ in sections]
    assert nums == list(range(1, 8)), f"章节编号不连续: {nums}"
    title = {int(n): t for n, t in sections}[7]
    assert "时间基线" in title, f"第 7 节标题不含「时间基线」: {title}"

    m = re.search(r"^### 7\. .+?\n(.*?)(?=^### |\Z)", text,
                  re.MULTILINE | re.DOTALL)
    body = m.group(1)
    assert "基线" in body and "establish" in body, "条款未要求建立基线"
    assert "观测时刻" in body, "条款未要求证据带观测时刻"
    assert "违规" in body or "后果" in body, "条款未明确违规后果"


# --------------------------------------------------------------------------- #
# TC-CONST-002 — 至少 1 处 Gate 检查实际执行基线检查（可触发、可观察）
# --------------------------------------------------------------------------- #

def test_const_002_validate_executes_baseline_check(tmp_path, monkeypatch,
                                                    capsys):
    """validate 对缺基线的 change 输出基线警告（warning 级，不使校验失败）。"""
    change = tmp_path / ".fstdd" / "changes" / "demo-change"
    change.mkdir(parents=True)
    (change / ".fstdd.yaml").write_text(
        "change: demo-change\nphases:\n  understand:\n    status: completed\n",
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    from fstdd.cli.commands import validate
    with pytest.raises(SystemExit) as ei:
        validate.cmd_validate(SimpleNamespace(name="demo-change"))
    out = capsys.readouterr().out
    # 基线检查确实被执行并输出（其他校验错误导致的退出码与基线无关）
    assert "基线: 未建立" in out, "validate 未执行基线检查"
    assert "警告" in out, "基线提示必须是 warning 级"
    assert ei.value.code == 1  # 退出码来自缺文件等错误，不是基线


# --------------------------------------------------------------------------- #
# TC-CONST-003 — 宪法两份逐字节一致（测试断言覆盖）
# --------------------------------------------------------------------------- #

def test_const_003_two_copies_byte_identical():
    a = CONSTITUTION.read_bytes()
    b = CONSTITUTION_COPY.read_bytes()
    assert a == b, (
        "宪法两份副本不一致 —— 只更新了一份。"
        f"（{len(a)}B vs {len(b)}B）"
    )


# --------------------------------------------------------------------------- #
# TC-CONST-004 — 第 7 节每项「必须」都有可执行检查
# --------------------------------------------------------------------------- #

def test_const_004_each_must_has_executable_check():
    """第 7 节的每个「必须」都映射到已实现的可执行检查（文件/函数存在）。"""
    text = CONSTITUTION.read_text(encoding="utf-8")
    m = re.search(r"^### 7\. .+?\n(.*?)(?=^### |\Z)", text,
                  re.MULTILINE | re.DOTALL)
    body = m.group(1)
    musts = [ln for ln in body.splitlines() if "必须" in ln]
    assert len(musts) >= 2, "第 7 节至少应有 2 项「必须」"

    # 每项「必须」映射到一个已实现的检查载体
    checks = {
        "观测时刻": REPO_ROOT / "tools" / "check_timestamps.py",
        "时效": REPO_ROOT / "tools" / "check_timestamps.py",
        "基线": REPO_ROOT / "upstream" / "fstdd" / "cli" / "commands" / "baseline.py",
        "巡检": REPO_ROOT / "upstream" / "fstdd" / "cli" / "commands" / "baseline.py",
        "无法测量": REPO_ROOT / "upstream" / "fstdd" / "cli" / "commands" / "baseline.py",
    }
    for ln in musts:
        hit = [k for k in checks if k in ln]
        assert hit, f"「必须」项无映射检查: {ln.strip()}"
        for k in hit:
            assert checks[k].exists(), f"检查载体不存在: {checks[k]}"


# --------------------------------------------------------------------------- #
# TC-CONST-005 — 宪法与 skill 流程描述一致（Gate 前自检清单提及基线检查）
# --------------------------------------------------------------------------- #

def test_const_005_skill_gate_checklist_mentions_baseline():
    skill = (REPO_ROOT / "upstream" / ".claude" / "skills" / "stdd-build"
             / "SKILL.md")
    text = skill.read_text(encoding="utf-8")
    assert "基线" in text, "stdd-build 的 Gate 自检清单未提基线检查"
    # 与宪法一致：宪法第 7 节存在（已由 TC-CONST-001 覆盖），skill 不得反向冲突
    assert "时间基线" in text or "baseline establish" in text or \
           "baseline show --check" in text, \
           "skill 清单未给出与宪法一致的基线检查入口"


# --------------------------------------------------------------------------- #
# TC-TMPL-001 — upstream/.fstdd/templates/** 与 .fstdd/templates/** 逐文件一致
# --------------------------------------------------------------------------- #

def test_tmpl_001_dual_source_templates_identical():
    src = REPO_ROOT / ".fstdd" / "templates"
    mirror = REPO_ROOT / "upstream" / ".fstdd" / "templates"
    src_files = {p.relative_to(src) for p in src.rglob("*") if p.is_file()}
    mirror_files = {p.relative_to(mirror) for p in mirror.rglob("*")
                    if p.is_file()}
    assert src_files == mirror_files, (
        f"模板文件集合不一致: 仅源 {src_files - mirror_files} / "
        f"仅镜像 {mirror_files - src_files}"
    )
    for rel in sorted(src_files):
        a = (src / rel).read_bytes()
        b = (mirror / rel).read_bytes()
        assert a == b, f"模板双源不一致: {rel}"
