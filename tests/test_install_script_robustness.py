# -*- coding: utf-8 -*-
"""tests/test_install_script_robustness.py

安装工具链健壮性 —— strip_frontmatter / 安全策略模板化 / 超时 / 参数校验 / 源根深度上限 /
金融红线补充。

change: 2026-10-11-share-hardening-audit-fixes
TC: TC-ISR-001..010

全部离线：安装脚本以 FSTDD_OUT 指向临时目录运行（**绝不写全局 skill 目录**）。
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def _load_inst():
    spec = importlib.util.spec_from_file_location(
        "install_workbuddy_skills", TOOLS / "install_workbuddy_skills.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inst = _load_inst()


# ============================================================
# REQ-005 / C7：strip_frontmatter 逐行扫描
# ============================================================
def test_isr001_strip_frontmatter_only_line_exact():
    """TC-ISR-001 / SC-013：只在**行首独立** `---` 处收尾，含 `---` 前缀的行不算。"""
    text = (
        "---\n"
        "title: t\n"
        "--- inline-note\n"
        "description: |\n"
        "  a --- b\n"
        "---\n"
        "BODY-1\n"
        "---\n"
        "BODY-2\n"
    )
    out = inst.strip_frontmatter(text)
    assert out.startswith("BODY-1"), out[:40]
    assert "BODY-2" in out
    assert "description" not in out


def test_isr001b_strip_frontmatter_ignores_longer_rule():
    """TC-ISR-001 补充：`----`（更长横线）不被当成结束标记。"""
    text = "---\na: 1\n----\nb: 2\n---\nBODY\n"
    out = inst.strip_frontmatter(text)
    assert out == "BODY\n", repr(out)


def test_isr002_strip_frontmatter_no_terminator_returns_input():
    """TC-ISR-002 / SC-014：以 `---` 开头但无结束标记 → 原样返回。"""
    text = "---\ntitle: t\nbody without terminator\n"
    assert inst.strip_frontmatter(text) == text


def test_isr002b_strip_frontmatter_non_fm_returns_input():
    """TC-ISR-002 补充：不以 `---` 开头 → 原样返回。"""
    text = "# 标题\n正文\n"
    assert inst.strip_frontmatter(text) == text


# ============================================================
# REQ-006 / C7+C8：安全策略模板化
# ============================================================
def test_isr004_render_template_missing_returns_empty():
    """TC-ISR-004 / SC-016：模板缺失 → 返回空串（调用方回落原常量）。"""
    assert inst._render_template("definitely_missing_template", {}) == ""


def test_isr004b_render_template_renders_existing():
    """TC-ISR-004 补充：模板存在时渲染出哨兵与变量值。"""
    out = inst._render_template("security_note_deliver",
                                {"sentinel": "SENT", "share_cmd": "CMD"})
    assert out, "模板应能渲染"
    assert "SENT" in out
    assert "CMD" in out


def _load_verify():
    spec = importlib.util.spec_from_file_location(
        "verify_workbuddy_skills", TOOLS / "verify_workbuddy_skills.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_utils():
    spec = importlib.util.spec_from_file_location(
        "fstdd_cli_utils", ROOT / "upstream" / "fstdd" / "cli" / "utils.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verify = _load_verify()
utils = _load_utils()
BASH = shutil.which("bash")


# ============================================================
# REQ-007 / C9：CLI 冒烟超时
# ============================================================
def test_isr005_smoke_timeout_returns_false(monkeypatch):
    """TC-ISR-005 / SC-017：CLI 冒烟超时 → (False, 含「超时」)，不无限阻塞。"""
    seen = {}

    def _boom(cmd, **kw):
        seen["timeout"] = kw.get("timeout")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout"))

    monkeypatch.setattr(verify.subprocess, "run", _boom)
    ok, reason = verify.smoke_test()
    assert ok is False
    assert "超时" in reason
    assert seen.get("timeout") == 30, "冒烟必须带 30s 超时"


# ============================================================
# REQ-007 / C10：install.sh 参数校验
# ============================================================
@pytest.mark.skipif(BASH is None, reason="需要 bash")
def test_isr006_install_sh_missing_py_value_exits_2():
    """TC-ISR-006 / SC-018：`--py` 缺参 → [FAIL] + exit 2。"""
    r = subprocess.run([BASH, str(ROOT / "install.sh"), "--py"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT))
    assert r.returncode == 2, (r.returncode, r.stdout[-400:], r.stderr[-200:])
    assert "[FAIL]" in (r.stdout + r.stderr)


@pytest.mark.skipif(BASH is None, reason="需要 bash")
def test_isr006b_install_sh_platform_missing_value_exits_2():
    """TC-ISR-006 补充：`--platform` 后接另一选项 → exit 2。"""
    r = subprocess.run([BASH, str(ROOT / "install.sh"), "--platform", "--yes"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT))
    assert r.returncode == 2, (r.returncode, r.stdout[-400:])


@pytest.mark.skipif(BASH is None, reason="需要 bash")
def test_isr007_install_sh_unknown_arg_warns(tmp_path):
    """TC-ISR-007 / SC-019：未知参数 → [WARN] 含「未知参数」且不中断（exit 0）。

    FSTDD_OUT 指向临时目录 ⇒ **绝不写全局 skill 目录**。
    """
    env = dict(os.environ)
    env["FSTDD_OUT"] = str(tmp_path / "out")
    env["FSTDD_PY"] = sys.executable
    r = subprocess.run([BASH, str(ROOT / "install.sh"), "--nope", "--yes"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT), env=env)
    out = r.stdout + r.stderr
    assert "[WARN]" in out
    assert "未知参数" in out
    assert r.returncode == 0, out[-600:]


# ============================================================
# REQ-008 / C6：源根查找深度上限
# ============================================================
def test_isr008_source_root_depth_limit(tmp_path):
    """TC-ISR-008 / SC-020：超深度上限 → 抛含深度信息的 RuntimeError，不无限循环。"""
    deep = tmp_path
    for _ in range(8):
        deep = deep / "a"
    deep.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RuntimeError) as ei:
        utils._find_source_root(deep, max_depth=3)
    msg = str(ei.value)
    assert "within 3 levels" in msg
    assert "possible symlink loop" in msg


def test_isr008b_source_root_found_within_limit():
    """TC-ISR-008 补充：正常深度内可正确定位源根（不得因加上限而回归）。"""
    root = utils._find_source_root(ROOT / "upstream" / "fstdd" / "cli")
    assert root == (ROOT / "upstream")


def test_isr003_install_emits_policy_sentinel_isolated(tmp_path):
    """TC-ISR-003 / SC-015：隔离输出目录下安装，产物仍含哨兵且策略段落等价。"""
    out = tmp_path / "skills_out"
    env = dict(os.environ)
    env["FSTDD_OUT"] = str(out)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(TOOLS / "install_workbuddy_skills.py"),
         "--platform", "workbuddy"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr

    deliver = (out / "fstdd-deliver" / "SKILL.md").read_text(encoding="utf-8")
    assert "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1" in deliver
    assert "经验静默回传" in deliver
    assert "--export --publish --silent" in deliver
    assert "FSTDD_NO_SHARE" in deliver

    upgrade = (out / "fstdd-upgrade" / "SKILL.md").read_text(encoding="utf-8")
    assert "升级 / 重装后必做" in upgrade
    assert "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1" in upgrade

    entry = (out / "fstdd" / "SKILL.md").read_text(encoding="utf-8")
    assert "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1" in entry


# ============================================================
# REQ-009 / C11：金融红线补充
# ============================================================
def test_isr009_finance_skill_redline_additions():
    """TC-ISR-009 / SC-021：SKILL.md 含四处新增关键措辞。"""
    content = (ROOT / "skills" / "fstdd-fin" / "SKILL.md").read_text(encoding="utf-8")
    for token in ("费率/限额变更必须版本化配置", "RTO", "RPO", "并发幂等键冲突"):
        assert token in content, f"缺关键措辞: {token}"
    # 只增不改：既有红线措辞必须仍在位（回归护栏）
    for kept in ("无硬编码", "账实相符", "降级不静默"):
        assert kept in content, f"既有红线被破坏: {kept}"


# ============================================================
# REQ-010 / SC-022：不回归
# ============================================================
def test_isr010_two_test_trees_present_and_collectable():
    """TC-ISR-010 / SC-022：全量不回归由 C2 的 `pytest upstream/tests tests` 证明。

    此处固化可判定子集：两棵测试树均存在且含测试文件（防止新测试落到不被收集的位置）。
    """
    for tree in (ROOT / "tests", ROOT / "upstream" / "tests"):
        assert tree.is_dir(), f"测试树缺失: {tree}"
        assert list(tree.glob("test_*.py")), f"{tree} 下无测试文件"
    assert (ROOT / "tests" / "test_share_hardening.py").exists()
    assert (ROOT / "tests" / "test_install_script_robustness.py").exists()
