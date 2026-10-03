# -*- coding: utf-8 -*-
"""tests/test_install_smoke.py — FSTDD v3.1.1 安装链路冒烟测试

conftest.py 提供 --platform 参数 + 自动 skip 不匹配平台。
节点用法：pytest tests/test_install_smoke.py --platform <name>
或直接跑 run_release_validation.py（自动调这个）。
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"
PY = sys.executable


def _run(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, str(TOOLS / script), *args],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


# ── L1: install_workbuddy_skills.py 冒烟 ──────────────────────

@pytest.mark.workbuddy
@pytest.mark.trae
@pytest.mark.claude_code
@pytest.mark.linux
class TestInstallSmoke:
    def test_install_exit_zero(self, platform):
        """L1-01: install_workbuddy_skills.py --platform {platform} → exit 0"""
        r = _run("install_workbuddy_skills.py", ["--platform", platform])
        assert r.returncode == 0, f"install rc={r.returncode}\nSTDOUT:{r.stdout[-500:]}\nSTDERR:{r.stderr[-500:]}"

    def test_install_output_shows_7_skills(self, platform):
        """L1-02: install stdout 包含 7 个 skill 路径"""
        r = _run("install_workbuddy_skills.py", ["--platform", platform])
        stdout = r.stdout
        # 应该出现至少 7 个 skill 名
        skill_names = ["fstdd", "fstdd-understand", "fstdd-spec", "fstdd-build",
                       "fstdd-deliver", "fstdd-upgrade", "fstdd-fin"]
        found = [n for n in skill_names if n in stdout]
        assert len(found) >= 7, f"只看到 {len(found)}/7 skills: {found}\nSTDOUT: {stdout[:800]}"

    def test_verify_exit_zero(self, platform):
        """L1-03: verify_workbuddy_skills.py --platform {platform} → exit 0"""
        r = _run("verify_workbuddy_skills.py", ["--platform", platform])
        assert r.returncode == 0, f"verify rc={r.returncode}\nSTDOUT:{r.stdout[-500:]}\nSTDERR:{r.stderr[-500:]}"
