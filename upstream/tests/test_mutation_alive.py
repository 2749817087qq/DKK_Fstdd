# -*- coding: utf-8 -*-
"""TC-MUT-001..005 — 关键检测路径变异测试：注入已知缺陷，断言对应检测真实报红。

哲学（EXP-20260917-B3）：长期零命中的检测逻辑是可疑资产。每个变异体 =
一个应被检测到的缺陷；测试通过 = 检测器对该缺陷真的会红。
每个用例含阴性对照（无缺陷时检测器保持安静），证明是「判别」而非「恒红」。

已知局限（audit 在册，后续 change 修）：
- _check_phase_integrity_guard 当前零调用方（死代码），TC-MUT-002 直接调用
  函数本体证明逻辑存活，接线属后续 change。
- naive last_mod 的僵尸漏检（EA-010 家族）反向锁定：TC-MUT-001 阴性对照
  只覆盖 tz-aware 场景，naive 场景的失效已由审计表分类为「升级 change」。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
sys.path.insert(0, str(UPSTREAM))

from fstdd.cli.commands import guard  # noqa: E402


def run_cli(*args: str, cwd: Path):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_project(tmp_path: Path, git: bool = False) -> tuple[Path, str]:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True)
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", "mut", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())
    if git:
        subprocess.run(["git", "init", "-q"], cwd=str(proj), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(proj), check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=str(proj), check=True)
    return proj, change_id


def read_state(proj: Path, change_id: str) -> dict:
    return yaml.safe_load(
        (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").read_text(encoding="utf-8")
    )


def write_state(proj: Path, change_id: str, state: dict) -> None:
    (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").write_text(
        yaml.safe_dump(state, allow_unicode=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# TC-MUT-001 — 僵尸检测（status CLI 端到端）：8 天未动的 change 必须上榜
# --------------------------------------------------------------------------- #

def test_mut_001_zombie_detected_end_to_end(tmp_path):
    """变异体：非活跃 change 停滞 8 天必须上榜。

    实测发现（本测试抓获）：_show_zombie_changes 豁免当前活跃 change
    （status.py current_name 排除）——单 change 项目的水线僵尸永远不报。
    该覆盖缺口已计入审计发现（响应=升级 change），本用例用双 change
    锁定「非活跃必报」的现存正确行为。
    """
    proj, stale_id = make_project(tmp_path)
    stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="seconds")
    state = read_state(proj, stale_id)
    state["last_modified"] = stale
    write_state(proj, stale_id, state)

    # 再建一个新鲜 change（成为活跃，僵尸扫描只扫非活跃）
    rc, _, err = run_cli("new", "mut2", cwd=proj)
    assert rc == 0, f"new 第二个 change 失败: {err}"
    active_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir()
                     if p.is_dir() and p.name != stale_id)

    rc, out, err = run_cli("status", cwd=proj)
    assert rc == 0, f"status 失败: {err}"
    assert "僵尸" in out and stale_id in out, f"僵尸 change 未被检出:\n{out}"

    # 阴性对照：新鲜活跃 change 不上榜（判别力证明）
    assert active_id not in out.split("僵尸")[1], "新鲜 change 被误报为僵尸"


# --------------------------------------------------------------------------- #
# TC-MUT-002 — 滞后检测（_check_phase_integrity_guard 直接调用）：
# Build 完成 25h 未进 DELIVER 必须告警
# --------------------------------------------------------------------------- #

def test_mut_002_build_lag_warned(tmp_path):
    proj, change_id = make_project(tmp_path)
    ago25h = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(timespec="seconds")
    state = read_state(proj, change_id)
    state["phases"] = {
        "spec": {"status": "completed", "completed_at": ago25h},
        "build": {"status": "completed", "completed_at": ago25h},
        "deliver": {"status": "pending"},
    }
    write_state(proj, change_id, state)

    warnings = guard._check_phase_integrity_guard(proj)
    joined = "\n".join(warnings)
    assert "Build完成" in joined and change_id in joined, f"滞后未告警: {warnings}"

    # 阴性对照：刚完成的 Build 不告警
    proj2, change_id2 = make_project(tmp_path / "fresh")
    state2 = read_state(proj2, change_id2)
    state2["phases"] = {
        "spec": {"status": "completed", "completed_at": ago25h},
        "build": {"status": "completed",
                  "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "deliver": {"status": "pending"},
    }
    write_state(proj2, change_id2, state2)
    assert not guard._check_phase_integrity_guard(proj2), "新鲜 Build 被误报滞后"


# --------------------------------------------------------------------------- #
# TC-MUT-003 — task_type 失配检测：docs 任务改 3 个代码文件必须告警
# --------------------------------------------------------------------------- #

def test_mut_003_task_type_mismatch(tmp_path):
    proj, change_id = make_project(tmp_path, git=True)
    # 提交 3 个代码文件后再修改（git diff 可见）
    for i in range(3):
        (proj / f"mod{i}.py").write_text(f"x = {i}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(proj), check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "add mods"], cwd=str(proj), check=True)
    for i in range(3):
        with open(proj / f"mod{i}.py", "a", encoding="utf-8") as f:
            f.write(f"y = {i}\n")

    mismatch, reason = guard._check_file_type_mismatch(proj, "docs")
    assert mismatch, "docs 任务改 3 个 .py 未判失配"
    assert "task_type='docs'" in reason, reason

    # 阴性对照：code 任务永不失配；无改动也不报
    assert guard._check_file_type_mismatch(proj, "code") == (False, "")
    proj2, _ = make_project(tmp_path / "fresh", git=True)
    assert guard._check_file_type_mismatch(proj2, "docs") == (False, "")


# --------------------------------------------------------------------------- #
# TC-MUT-004 — L2 时效守卫（check_timestamps）：naive 时间戳必须被判违规
# --------------------------------------------------------------------------- #

def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "_chk", REPO / "tools" / "check_timestamps.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mut_004_naive_timestamp_flagged(tmp_path):
    chk = _load_checker()
    proj, change_id = make_project(tmp_path)
    state = read_state(proj, change_id)
    state["created_at"] = "2026-09-18T00:00:00"  # naive 变异体
    write_state(proj, change_id, state)

    violations = chk.scan_change_values(proj)
    assert violations, "naive created_at 未被 L2 守卫检出"
    assert any(v.get("category") == "naive_value" for v in violations), violations

    # 阴性对照：tz-aware 值不判（读回真实状态即 aware）
    proj2, change_id2 = make_project(tmp_path / "fresh")
    violations2 = chk.scan_change_values(proj2)
    naive2 = [v for v in violations2
              if change_id2 in str(v.get("location", "")) and v.get("category") == "naive_value"]
    assert not naive2, f"新鲜 change 被误报 naive: {naive2}"


# --------------------------------------------------------------------------- #
# TC-MUT-005 — validate 基线警告：无基线的 change 必须出「基线: 未建立」
# --------------------------------------------------------------------------- #

def test_mut_005_validate_baseline_warning(tmp_path):
    proj, change_id = make_project(tmp_path)
    rc, out, err = run_cli("validate", change_id, cwd=proj)
    assert rc in (0, 1), f"validate 异常退出: {err}"
    assert "基线: 未建立" in out, f"基线缺失警告未出现:\n{out}"

    # 阴性对照：建立基线后同一检查不再警告
    rc, _, err = run_cli("baseline", "establish", change_id, cwd=proj)
    assert rc == 0, f"baseline establish 失败: {err}"
    rc, out2, err = run_cli("validate", change_id, cwd=proj)
    assert "基线: 未建立" not in out2, "建基线后仍报未建立"
