# -*- coding: utf-8 -*-
"""TC-DFX-001..004 — detection-voice Slice 1：guard 家族失败有声化。

先行断言（RED 目标）：
- DFX-001/002：非 git 环境（git diff returncode != 0）必须 stderr 警告，
  不得静默返回 0 / (False, "")
- DFX-003：_is_zombie 遇 naive last_modified（8 天前）按 UTC 归一后判定为僵尸
- DFX-004：fstdd guard status 输出 Phase Lag 段（F-2 接线端到端）
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
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


def make_project(tmp_path: Path) -> tuple[Path, str]:
    proj = tmp_path / "proj"
    proj.mkdir(parents=True)
    rc, _, err = run_cli("init", cwd=proj)
    assert rc == 0, f"init 失败: {err}"
    rc, _, err = run_cli("new", "dv", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    change_id = next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())
    return proj, change_id


def read_state(proj: Path, change_id: str) -> dict:
    return yaml.safe_load(
        (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").read_text(encoding="utf-8")
    )


def write_state(proj: Path, change_id: str, state: dict) -> None:
    (proj / ".fstdd" / "changes" / change_id / ".fstdd.yaml").write_text(
        yaml.safe_dump(state, allow_unicode=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# DFX-001/002 — git 计数/统计失败必须 stderr 警告（非 git 目录）
# --------------------------------------------------------------------------- #

def test_dfx_001_count_changed_files_warns_outside_git(tmp_path, capfd):
    n = guard._count_changed_files(tmp_path)  # 非 git 仓库 → git diff 失败
    assert n == 0
    err = capfd.readouterr().err
    assert "git" in err.lower() and ("警告" in err or "warn" in err.lower()), \
        f"git 失败未出声: stderr={err!r}"


def test_dfx_002_type_mismatch_warns_outside_git(tmp_path, capfd):
    mismatch, reason = guard._check_file_type_mismatch(tmp_path, "docs")
    assert mismatch is False
    err = capfd.readouterr().err
    assert "git" in err.lower() and ("警告" in err or "warn" in err.lower()), \
        f"统计失败未出声: stderr={err!r}"


# --------------------------------------------------------------------------- #
# DFX-003 — _is_zombie 对 naive last_modified 按 UTC 归一
# --------------------------------------------------------------------------- #

def test_dfx_003_zombie_naive_lastmod_normalized(tmp_path, capfd):
    proj, change_id = make_project(tmp_path)
    stale_naive = (datetime.utcnow() - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S")
    change_dir = proj / ".fstdd" / "changes" / change_id
    state = read_state(proj, change_id)
    state["last_modified"] = stale_naive  # naive 变异体
    write_state(proj, change_id, state)

    assert guard._is_zombie(change_dir) is True, "naive 8 天前 last_mod 未判僵尸"
    err = capfd.readouterr().err
    assert "warn" not in err.lower(), f"naive 归一不应告警: {err!r}"

    # 阴性对照：naive 新鲜值不判
    fresh_naive = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    state["last_modified"] = fresh_naive
    write_state(proj, change_id, state)
    assert guard._is_zombie(change_dir) is False


# --------------------------------------------------------------------------- #
# DFX-004 — F-2 接线：guard status 输出 Phase Lag 段（CLI 端到端）
# --------------------------------------------------------------------------- #

def test_dfx_004_guard_status_shows_phase_lag(tmp_path):
    proj, change_id = make_project(tmp_path)
    ago25h = (datetime.utcnow() - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    state = read_state(proj, change_id)
    state["phases"] = {
        "spec": {"status": "completed", "completed_at": ago25h},
        "build": {"status": "completed", "completed_at": ago25h},
        "deliver": {"status": "pending"},
    }
    write_state(proj, change_id, state)

    rc, out, err = run_cli("guard", "status", cwd=proj)
    combined = out + err
    assert rc == 0, f"guard status 失败: {err}"
    assert "Phase Lag" in combined or "滞后" in combined, \
        f"Phase Lag 段缺失（F-2 未接线）:\n{combined}"
    assert "Build完成" in combined and change_id in combined, combined

    # 阴性对照：新鲜 change 无滞后段内容
    proj2, _ = make_project(tmp_path / "fresh")
    rc, out2, err2 = run_cli("guard", "status", cwd=proj2)
    assert "Phase Lag" not in out2 and "滞后" not in out2, out2
