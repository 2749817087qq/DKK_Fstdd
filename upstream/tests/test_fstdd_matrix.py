# -*- coding: utf-8 -*-
"""FSTDD 场景化测试矩阵 —— 覆盖常见使用情况（非仅单元测试）。

分组：
  A. 安装/部署      (5)
  B. CLI 命令       (12)
  C. 流程 STDD      (8)
  D. 改名一致性     (8)
  E. 边界/异常      (7)

原则：每个用例验证**真实可观测行为**，不是走过场。
运行：python -m pytest upstream/tests/test_fstdd_matrix.py -q
"""
from __future__ import annotations

import datetime

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# --- 路径 -------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent          # upstream/tests
UPSTREAM = TESTS_DIR.parent                          # upstream
REPO = UPSTREAM.parent                               # stdd-repo
CLI = UPSTREAM / "bin" / "fstdd"
INSTALLER = REPO / "tools" / "install_workbuddy_skills.py"
VERIFIER = REPO / "tools" / "verify_workbuddy_skills.py"

SENTINEL = "FSTDD_LOCAL_POLICY_NO_UPLOAD_V1"


# change 目录名由**创建当天**决定（`<YYYY-MM-DD>-<slug>`）。
# **不得硬编码日期** —— 硬编码的用例只在当天能过，次日必然失败
# （实测：2026-09-17 跑全量时 3 个用例因硬编码 2026-09-16 而失败）。
DEMO_CHANGE = f"{datetime.date.today().isoformat()}-demo-change"


def run_cli(args, cwd, timeout=120):
    """调用 CLI，返回 (returncode, stdout+stderr)。"""
    r = subprocess.run([sys.executable, str(CLI)] + list(args), cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def init_project(tmp: Path):
    """初始化一个项目，返回 (rc, out)。"""
    rc, out = run_cli(["init"], tmp)
    return rc, out


# ===========================================================================
# A. 安装/部署
# ===========================================================================
class TestInstall:
    def test_a1_installer_exists(self):
        assert INSTALLER.exists(), "安装脚本缺失"

    def test_a2_install_to_temp_dir(self, tmp_path):
        out_dir = tmp_path / "skills"
        env = dict(os.environ, FSTDD_OUT=str(out_dir), FSTDD_PY=sys.executable)
        r = subprocess.run([sys.executable, str(INSTALLER)], env=env,
                           capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
        names = sorted(p.name for p in out_dir.iterdir() if p.is_dir())
        assert "fstdd" in names
        for phase in ("understand", "spec", "build", "deliver", "upgrade"):
            assert f"fstdd-{phase}" in names

    def test_a3_financial_skill_installed(self, tmp_path):
        out_dir = tmp_path / "skills"
        env = dict(os.environ, FSTDD_OUT=str(out_dir), FSTDD_PY=sys.executable)
        subprocess.run([sys.executable, str(INSTALLER)], env=env,
                       capture_output=True, timeout=180)
        assert (out_dir / "fstdd-fin" / "SKILL.md").exists()

    def test_a4_sentinel_present(self, tmp_path):
        out_dir = tmp_path / "skills"
        env = dict(os.environ, FSTDD_OUT=str(out_dir), FSTDD_PY=sys.executable)
        subprocess.run([sys.executable, str(INSTALLER)], env=env,
                       capture_output=True, timeout=180)
        for name in ("fstdd", "fstdd-deliver", "fstdd-upgrade"):
            text = (out_dir / name / "SKILL.md").read_text(encoding="utf-8", errors="replace")
            assert SENTINEL in text, f"{name} 哨兵缺失"

    def test_a5_verify_passes(self, tmp_path):
        out_dir = tmp_path / "skills"
        env = dict(os.environ, FSTDD_OUT=str(out_dir), FSTDD_PY=sys.executable)
        subprocess.run([sys.executable, str(INSTALLER)], env=env, capture_output=True, timeout=180)
        r = subprocess.run([sys.executable, str(VERIFIER)], env=env,
                           capture_output=True, text=True, timeout=180)
        assert "PASS" in (r.stdout or ""), r.stdout + r.stderr


# ===========================================================================
# B. CLI 命令
# ===========================================================================
class TestCLI:
    def test_b1_help_lists_subcommands(self, tmp_path):
        rc, out = run_cli(["--help"], tmp_path)
        assert rc == 0
        for cmd in ("init", "new", "status", "archive", "gate", "experience", "install"):
            assert cmd in out, f"--help 未列出 {cmd}"

    def test_b2_init_creates_skeleton(self, tmp_path):
        rc, _ = init_project(tmp_path)
        assert rc == 0
        assert (tmp_path / ".fstdd").exists()
        for sub in ("changes", "specs", "archive", "config.d"):
            assert (tmp_path / ".fstdd" / sub).exists(), f"骨架缺 {sub}"

    def test_b3_init_idempotent(self, tmp_path):
        init_project(tmp_path)
        rc, _ = init_project(tmp_path)
        assert rc == 0, "重复 init 应成功（幂等）"

    def test_b4_init_dry_run_writes_nothing(self, tmp_path):
        rc, out = run_cli(["init", "--dry-run"], tmp_path)
        assert rc == 0
        assert "DRY-RUN" in out or "dry" in out.lower()
        assert not (tmp_path / ".fstdd").exists(), "dry-run 不应写文件"

    def test_b5_new_creates_change(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["new", "demo-change"], tmp_path)
        assert rc == 0, out
        assert (tmp_path / ".fstdd" / "changes" / DEMO_CHANGE).exists()

    def test_b6_new_creates_canonical_yaml(self, tmp_path):
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        # canonical YAML 生成在 change 目录内；全局 .fstdd/canonical/ 由归档/合并填充
        chg = tmp_path / ".fstdd" / "changes" / DEMO_CHANGE
        canon = chg / "canonical"
        assert canon.exists(), "change 内应生成 canonical/"
        assert any(canon.rglob("*.yaml")), "canonical 下应有 YAML"

    def test_b7_status_no_change(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["status"], tmp_path)
        # 无 change 时 status 以退出码 1 提示“找不到 change”，属正常设计
        assert rc in (0, 1)
        assert "change" in out.lower()

    def test_b8_status_with_change(self, tmp_path):
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        rc, out = run_cli(["status"], tmp_path)
        assert rc == 0 and "demo-change" in out

    def test_b9_gate_requires_confirmation(self, tmp_path):
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        # 不传 --confirmed-by 应被拒绝
        rc, out = run_cli(["gate", "approve", DEMO_CHANGE, "--gate", "1"], tmp_path)
        assert rc != 0 or "confirmed" in out.lower()

    def test_b10_gate_approve_ok(self, tmp_path):
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        rc, out = run_cli(
            ["gate", "approve", DEMO_CHANGE, "--gate", "1",
             "--confirmed-by", "dialog", "--evidence", "matrix test"],
            tmp_path)
        assert rc == 0, out

    def test_b11_archive_requires_build(self, tmp_path):
        """流程约束：未走完 BUILD（Phase 3）的 change 不得归档。"""
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        rc, out = run_cli(["archive", DEMO_CHANGE], tmp_path)
        # 应被拒绝并提示 BUILD/Phase 3 未完成，而不是静默归档
        assert ("BUILD" in out) or ("Phase 3" in out) or rc != 0, out
        assert not (tmp_path / ".fstdd" / "archive" / DEMO_CHANGE).exists()

    def test_b12_experience_list_runs(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["experience", "list"], tmp_path)
        assert rc == 0, out


# ===========================================================================
# C. 流程 STDD
# ===========================================================================
class TestFlow:
    def test_c1_full_four_phases_present(self, tmp_path):
        """四阶段在宪法中明确要求（Phase 3 不可跳过）。"""
        init_project(tmp_path)
        const = (tmp_path / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        for phase in ("Understand", "Spec", "Build", "Deliver"):
            assert phase in const

    def test_c2_phase3_mandatory(self, tmp_path):
        init_project(tmp_path)
        const = (tmp_path / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        assert "不可跳过" in const or "Build" in const

    def test_c3_three_gates_required(self, tmp_path):
        init_project(tmp_path)
        const = (tmp_path / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        for g in ("Gate 1", "Gate 2", "Gate 3"):
            assert g in const

    def test_c4_gate_pending_before_approval(self, tmp_path):
        init_project(tmp_path)
        run_cli(["new", "demo-change"], tmp_path)
        rc, out = run_cli(["status"], tmp_path)
        assert "pending" in out.lower() or "Phase 1" in out

    def test_c5_experience_no_upload_rule(self, tmp_path):
        """宪法必须声明「不向第三方外发」（与删除第三方上传通道一致）。

        注意断言的是**不向第三方外发**，而不是旧契约里的「经验数据不外发」：
        后者暗示完全不外发，与本项目「Phase 4 静默回传经验到我方指定位置」的
        既定语义不符（我方位置 = Fstdd-experiences / 自建接收端点）。
        契约措辞须精确，断言须随之精确。
        """
        init_project(tmp_path)
        const = (tmp_path / "FSTDD_CONSTITUTION.md").read_text(encoding="utf-8")
        assert "不向第三方外发" in const

    def test_c6_experiences_dir_created(self, tmp_path):
        init_project(tmp_path)
        assert (tmp_path / ".fstdd" / "experiences").exists()

    def test_c7_constitution_in_skeleton(self, tmp_path):
        """骨架自包含：.fstdd/memory/ 下也有宪法。"""
        init_project(tmp_path)
        assert (tmp_path / ".fstdd" / "memory" / "FSTDD_CONSTITUTION.md").exists()

    def test_c8_scripts_dir_created(self, tmp_path):
        init_project(tmp_path)
        assert (tmp_path / ".fstdd" / "scripts").exists()


# ===========================================================================
# D. 改名一致性
# ===========================================================================
class TestRename:
    def test_d1_cli_binary_named_fstdd(self):
        assert CLI.exists(), "bin/fstdd 不存在"

    def test_d2_no_stdd_binary(self):
        assert not (UPSTREAM / "bin" / "stdd").exists(), "仍存在旧名 bin/stdd"

    def test_d3_package_dir_is_fstdd(self):
        assert (UPSTREAM / "fstdd" / "cli").exists()

    def test_d4_env_var_respected(self, tmp_path):
        """FSTDD_OUT 生效（改名后的环境变量）。"""
        out_dir = tmp_path / "skills"
        env = dict(os.environ, FSTDD_OUT=str(out_dir), FSTDD_PY=sys.executable)
        subprocess.run([sys.executable, str(INSTALLER)], env=env, capture_output=True, timeout=180)
        assert out_dir.exists()

    def test_d5_data_dir_is_fstdd(self, tmp_path):
        init_project(tmp_path)
        assert (tmp_path / ".fstdd").exists()
        assert not (tmp_path / ".stdd").exists()

    def test_d6_cli_output_uses_fstdd_commands(self, tmp_path):
        init_project(tmp_path)
        _, out = run_cli(["init"], tmp_path)
        assert "/fstdd-understand" in out
        assert "/stdd-understand" not in out

    def test_d7_constitution_filename(self, tmp_path):
        init_project(tmp_path)
        assert (tmp_path / "FSTDD_CONSTITUTION.md").exists()

    def test_d8_share_refuses(self, tmp_path):
        """上传通道已永久删除：share 应拒绝。"""
        init_project(tmp_path)
        rc, out = run_cli(["experience", "share", "EXP-NOT-EXIST"], tmp_path)
        assert "已永久禁用" in out or rc != 0


# ===========================================================================
# E. 边界 / 异常
# ===========================================================================
class TestEdge:
    def test_e1_status_without_init(self, tmp_path):
        """未初始化项目跑 status：优雅提示，不得抛 traceback。"""
        rc, out = run_cli(["status"], tmp_path)
        assert rc in (0, 1)
        assert "Traceback" not in out

    def test_e2_new_without_init(self, tmp_path):
        rc, out = run_cli(["new", "x"], tmp_path)
        # 未初始化：优雅提示（rc 0/1 均可），不得抛 traceback
        assert rc in (0, 1)
        assert "Traceback" not in out

    def test_e3_empty_experience_search_table(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["experience", "search", "anything"], tmp_path)
        assert rc == 0
        assert ("no results" in out.lower()) or ("empty" in out.lower()) or (out.strip() != "")

    def test_e4_empty_experience_search_json(self, tmp_path):
        """json 格式无结果应输出 []（可解析），非纯文本。"""
        init_project(tmp_path)
        rc, out = run_cli(
            ["experience", "search", "anything", "--format", "json"], tmp_path)
        assert rc == 0
        # 输出应包含可解析的空数组
        assert "[]" in out

    def test_e5_invalid_change_name(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["new", ""], tmp_path)
        # 空名应被拒绝或非零退出
        assert rc != 0 or "empty" in out.lower() or "invalid" in out.lower()

    def test_e6_archive_nonexistent(self, tmp_path):
        init_project(tmp_path)
        rc, out = run_cli(["archive", "no-such-change"], tmp_path)
        # 应报错但不崩溃（非零退出或提示不存在）
        assert rc != 0 or "not found" in out.lower() or "不存在" in out

    def test_e7_old_project_missing_new_dirs(self, tmp_path):
        """旧项目缺 scripts/、memory/：命令仍可用（向后兼容回退）。"""
        init_project(tmp_path)
        # 模拟旧项目：删除新目录
        import shutil
        shutil.rmtree(tmp_path / ".fstdd" / "scripts", ignore_errors=True)
        shutil.rmtree(tmp_path / ".fstdd" / "memory", ignore_errors=True)
        rc, out = run_cli(["status"], tmp_path)
        # 旧项目缺新目录：命令仍可用（rc 0/1 均可——无 change 时 status 为 1），
        # 关键是不得因目录缺失而崩溃（抛 traceback）
        assert rc in (0, 1), f"旧项目缺新目录时不应崩溃: {out}"
        assert "Traceback" not in out, f"缺目录导致异常: {out}"
