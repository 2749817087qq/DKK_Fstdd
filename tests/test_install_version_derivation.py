# -*- coding: utf-8 -*-
"""tests/test_install_version_derivation.py

change: 2026-10-05-upstream-baseline-alignment（capability: version-nomenclature）
TDD 切片 2：适配层版本字段派生去硬编码（tools/install_workbuddy_skills.py）。

断言范围（design.md 决策 3）：
  - 生成 skill 的 **frontmatter** version ← R(3.3.4)、stdd_version ← K(3.1.0)
  - 来源**横幅**与 module **docstring** 去硬编码
  - 不约束上游正文（upstream/.fstdd/skills/*.md 内既有的 V3.0.5 属上游内容，禁改区）
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "tools" / "install_workbuddy_skills.py"
VERIFY = ROOT / "tools" / "verify_workbuddy_skills.py"
PROJECT_YAML = ROOT / ".fstdd" / "config.d" / "project.yaml"
VERSION_YAML = ROOT / ".fstdd" / "version.yaml"


def _repo_version() -> str:
    """R 轴：从机器可读源读，不硬编码。"""
    for line in PROJECT_YAML.read_text(encoding="utf-8").splitlines():
        if line.startswith("stdd_version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise AssertionError("project.yaml 缺 stdd_version")


def _kernel_version() -> str:
    """K 轴：从机器可读源读。"""
    for line in VERSION_YAML.read_text(encoding="utf-8").splitlines():
        if line.startswith("upstream_version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise AssertionError("version.yaml 缺 upstream_version")


def _frontmatter(text: str) -> str:
    """取第一个 --- 到第二个 --- 之间的 frontmatter 块。"""
    assert text.startswith("---"), "生成 skill 未以 frontmatter 起始"
    end = text.index("\n---", 3)
    return text[:end]


def _banner(text: str) -> str:
    """取正文头部横幅（以 `> 本 skill 来自开源项目` 起的所有连续引用行）。"""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("> 本 skill 来自开源项目"))
    out = []
    for ln in lines[start:]:
        if not ln.startswith(">"):
            break
        out.append(ln)
    return "\n".join(out)


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """在临时 FSTDD_OUT 下实跑安装脚本，返回 (输出目录, 安装结果)。"""
    out = tmp_path_factory.mktemp("skills_out")
    env = dict(os.environ, FSTDD_OUT=str(out))
    r = subprocess.run(
        [sys.executable, str(INSTALL), "--platform", "workbuddy"],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return out, r


# ---------------------------------------------------------------------------
# TC-VNOM-006 — 生成 frontmatter 版本字段派生
# ---------------------------------------------------------------------------
def test_generated_frontmatter_derives_version_axes(installed):
    """TC-VNOM-006 / SC-006：version ← R、stdd_version ← K（纯 [0-9.]+），无 3.0.5。"""
    out, r = installed
    assert r.returncode == 0, f"安装脚本退出码 {r.returncode}\n{r.stdout}\n{r.stderr}"
    fm = _frontmatter((out / "fstdd-understand" / "SKILL.md").read_text(encoding="utf-8"))
    assert re.search(rf'^version:\s*"{re.escape(_repo_version())}"\s*$', fm, re.M), \
        f"生成 frontmatter 的 version 未取发行版轴 R={_repo_version()}"
    m = re.search(r'^stdd_version:\s*"([^"]+)"\s*$', fm, re.M)
    assert m, "生成 frontmatter 缺 stdd_version"
    assert m.group(1) == _kernel_version(), \
        f"stdd_version 未取内核轴 K={_kernel_version()}（实际 {m.group(1)}）"
    # EXP-2026-0013：声明形态须被实现口径覆盖 —— K 必须是纯 [0-9.]+
    assert re.fullmatch(r"[0-9.]+", m.group(1)), \
        f"stdd_version 形态非纯 [0-9.]+：{m.group(1)!r}"
    assert "3.0.5" not in fm, "生成 frontmatter 仍出现字面量 3.0.5"


# ---------------------------------------------------------------------------
# TC-VNOM-007 — 来源横幅与 docstring 去硬编码
# ---------------------------------------------------------------------------
def test_banner_and_docstring_dehardcoded(installed):
    """TC-VNOM-007 / SC-007：横幅用 K、保留 URL 与绝对路径适配；脚本无硬编码 3.0.5。"""
    out, _ = installed
    banner = _banner((out / "fstdd-understand" / "SKILL.md").read_text(encoding="utf-8"))
    assert _kernel_version() in banner, f"横幅未用内核轴 K={_kernel_version()}"
    assert "3.0.5" not in banner, "横幅仍写死 3.0.5"
    assert "https://github.com/leonai42/stdd" in banner, "横幅丢失上游源仓库 URL"
    assert (ROOT / "upstream").as_posix() in banner, "横幅丢失静态资源绝对路径适配"
    assert "bin/fstdd" in banner, "横幅丢失 CLI 绝对路径适配"

    src = INSTALL.read_text(encoding="utf-8")
    assert "3.0.5" not in src, "安装脚本源码仍含硬编码 3.0.5（docstring 或常量）"


# ---------------------------------------------------------------------------
# TC-VNOM-008 — install + verify 端到端 PASS
# ---------------------------------------------------------------------------
def test_install_then_verify_pass(installed):
    """TC-VNOM-008 / SC-008：安装退出码 0 + 校验器 PASS；生成戳与哨兵不变。"""
    out, r = installed
    assert r.returncode == 0, f"安装退出码 {r.returncode}\n{r.stdout}\n{r.stderr}"

    env = dict(os.environ, FSTDD_OUT=str(out))
    v = subprocess.run(
        [sys.executable, str(VERIFY), "--platform", "workbuddy"],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert v.returncode == 0, f"校验器退出码 {v.returncode}\n{v.stdout}\n{v.stderr}"
    assert "[PASS]" in v.stdout, f"校验器未输出 [PASS]\n{v.stdout}"

    deliver = (out / "fstdd-deliver" / "SKILL.md").read_text(encoding="utf-8")
    assert f"生成自 stdd-repo@{_repo_version()}" in deliver, "生成戳未保持 REPO_VERSION"
    assert "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1" in deliver, "fstdd-deliver 哨兵缺失"
    assert "--silent" in deliver and "FSTDD_NO_SHARE" in deliver, "静默回传策略块不完整"