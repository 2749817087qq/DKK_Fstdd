"""Guard 报错文案的自洽性 —— 文案里给出的修复命令必须真的能用。

V3.0.6 给完整性报错补了「可复制的修复命令」，但当时写的是::

    stdd gate approve --gate N --change <id> --confirmed-by dialog

其中 `--change` 在 CLI 中**不存在**（真实签名是位置参数 `<name>`），
照抄必然报 `unrecognized arguments: --change`。文案缺陷会直接误导调用方，
且比不给出命令更糟，故用测试锁死「文案 ⇄ 实数签名」的一致性。
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]


def _gate_approve_help() -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "fstdd", "gate", "approve", "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert proc.returncode == 0, (
        f"`gate approve --help` 执行失败: {proc.stderr}"
    )
    return proc.stdout


def _integrity_reason_for_incomplete_gate() -> str:
    """构造「已过 gate 但缺 confirmed_at」场景，取回守卫的报错正文。"""
    from fstdd.cli.commands.guard import _check_phase_integrity

    data = {
        "phases": {
            "understand": {"status": "completed"},
            "spec": {"status": "completed"},
            "build": {"status": "in_progress"},
            "deliver": {"status": "pending"},
        },
        "current_phase": "build",
    }
    ok, reason = _check_phase_integrity(data, "build")
    assert not ok, "该场景应判定为完整性不通过"
    return reason


def _extract_fix_cmd(reason: str) -> str:
    m = re.search(r"修复:\s*(stdd gate approve[^\n]*)", reason)
    assert m, f"报错文本里找不到修复命令: {reason!r}"
    return m.group(1).strip()


# --------------------------------------------------------------------------
# 1. 文案里出现的每个选项都必须是 gate approve 真实支持的
# --------------------------------------------------------------------------
def test_fix_cmd_options_exist_in_real_cli() -> None:
    help_text = _gate_approve_help()
    fix_cmd = _extract_fix_cmd(_integrity_reason_for_incomplete_gate())

    opts = set(re.findall(r"--[a-z][a-z-]*", fix_cmd))
    assert opts, f"修复命令里没有选项: {fix_cmd!r}"

    missing = sorted(o for o in opts if o not in help_text)
    assert not missing, (
        f"修复命令 {fix_cmd!r} 使用了 gate approve 不支持的选项 {missing}；"
        "真实签名见 `fstdd gate approve --help`"
    )


def test_fix_cmd_passes_change_name_positionally() -> None:
    fix_cmd = _extract_fix_cmd(_integrity_reason_for_incomplete_gate())
    assert "--change" not in fix_cmd, (
        f"修复命令仍在使用不存在的 --change 选项: {fix_cmd!r}"
    )
    assert re.match(r"stdd gate approve <change_id> ", fix_cmd), (
        f"修复命令应把 change 名作为位置参数紧跟 approve: {fix_cmd!r}"
    )


# --------------------------------------------------------------------------
# 2. 端到端：把占位符换成真实 change 名后，命令必须能跑通
# --------------------------------------------------------------------------
def test_fix_cmd_executes_end_to_end() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="fstdd_fixcmd_"))
    try:
        change = tmp / ".fstdd" / "changes" / "2026-01-01-demo"
        change.mkdir(parents=True)
        (change / ".fstdd.yaml").write_text(
            "version: '3.0'\n"
            "change_id: 2026-01-01-demo\n"
            "status: active\n"
            "current_phase: build\n"
            "task_type: code\n"
            "mode: standard\n"
            "phases:\n"
            "  understand: {status: completed}\n"
            "  spec: {status: completed}\n"
            "  build: {status: in_progress}\n"
            "  deliver: {status: pending}\n",
            encoding="utf-8",
        )

        fix_cmd = _extract_fix_cmd(_integrity_reason_for_incomplete_gate())
        real_cmd = fix_cmd.replace("stdd ", "", 1).replace(
            "<change_id>", "2026-01-01-demo"
        )

        proc = subprocess.run(
            [sys.executable, "-m", "fstdd", *shlex.split(real_cmd)],
            cwd=tmp,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(REPO)},
        )

        assert proc.returncode == 0, (
            f"照抄修复命令仍然失败。\n命令: {real_cmd}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

        data = yaml.safe_load((change / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["understand"].get("confirmed_at"), (
            "命令返回成功但未写入 confirmed_at"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
