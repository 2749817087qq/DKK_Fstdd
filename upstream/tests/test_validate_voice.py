# -*- coding: utf-8 -*-
"""TC-DFX-007..009 — detection-voice Slice S4a：validate/baseline/batch 失败有声化。

先行断言（RED 目标）：
- DFX-007：fstdd validate 遇损坏基线状态文件 → 输出含「基线」警告而非静默通过
- DFX-008：baseline._load_yaml 遇损坏基线文件 → 返回 {} 且 stderr 含「损坏」
- DFX-009：batch deliver 时 _confirm_gate(3) 抛错 → stderr「Gate 3 确认失败」，
  且批次仍推进到 deliver（业务决策：闭合优先，确认失败留痕）

对应需求 DV-008 / DV-009 / DV-010。
invariants：阈值一律不变；警告走 stderr，stdout 结构化输出不受污染；
守卫类默认值保持 fail-closed。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "upstream"
CLI = UPSTREAM / "bin" / "fstdd"
sys.path.insert(0, str(UPSTREAM))

from fstdd.cli.commands import baseline, batch  # noqa: E402

# 流式映射未闭合 —— yaml.safe_load 必然抛 ScannerError
CORRUPT_YAML = "at: 2026-09-18\nbaseline: { node_id: N1, base_git_sha: [unclosed\n"


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
    rc, _, err = run_cli("new", "s4a", cwd=proj)
    assert rc == 0, f"new 失败: {err}"
    return proj, next(p.name for p in (proj / ".fstdd" / "changes").iterdir() if p.is_dir())


# --------------------------------------------------------------------------- #
# DFX-007 / DV-008 — validate 基线状态不可读必须有声
# --------------------------------------------------------------------------- #

def test_dfx_007_validate_warns_on_corrupt_baseline_state(tmp_path):
    proj, change_id = make_project(tmp_path)
    change_dir = proj / ".fstdd" / "changes" / change_id
    (change_dir / ".fstdd.yaml").write_text(CORRUPT_YAML, encoding="utf-8")

    rc, out, err = run_cli("validate", change_id, cwd=proj)
    combined = out + err
    assert "基线" in combined, f"损坏基线状态被静默吞掉（rc={rc}）:\n{combined}"
    assert "状态不可读" in combined, f"缺少「状态不可读」措辞:\n{combined}"


def test_dfx_007_validate_ok_state_reports_incomplete(tmp_path):
    """阴性对照：状态可读但基线不完整 → 既有「不完整」警告保持不回归。"""
    proj, change_id = make_project(tmp_path)
    change_dir = proj / ".fstdd" / "changes" / change_id
    (change_dir / ".fstdd.yaml").write_text(
        "phases:\n  understand:\n    status: completed\n", encoding="utf-8")

    rc, out, err = run_cli("validate", change_id, cwd=proj)
    assert "基线" in out + err, out


# --------------------------------------------------------------------------- #
# DFX-008 / DV-009 — _load_yaml 损坏文件须 stderr 警告
# --------------------------------------------------------------------------- #

def test_dfx_008_load_yaml_warns_on_corrupt_file(tmp_path, capfd):
    bad = tmp_path / "baseline.yaml"
    bad.write_text(CORRUPT_YAML, encoding="utf-8")

    assert baseline._load_yaml(bad) == {}
    err = capfd.readouterr().err
    assert "损坏" in err, f"损坏文件静默返回空字典: stderr={err!r}"


def test_dfx_008_load_yaml_ok_file_stays_silent(tmp_path, capfd):
    """阴性对照：正常文件不得误告警（防过度出声）。"""
    good = tmp_path / "baseline.yaml"
    good.write_text("baseline:\n  at: 2026-09-18\n", encoding="utf-8")

    data = baseline._load_yaml(good)
    # YAML 会把 2026-09-18 自动解析为 date 类型，此处只验键值存在，不比较具体类型
    assert data.get("baseline", {}).get("at"), data
    assert "损坏" not in capfd.readouterr().err


def test_dfx_008_load_yaml_missing_file_stays_silent(tmp_path, capfd):
    """阴性对照：文件不存在沿用「无基线」安全默认，不告警。"""
    assert baseline._load_yaml(tmp_path / "nope.yaml") == {}
    assert "损坏" not in capfd.readouterr().err


# --------------------------------------------------------------------------- #
# DFX-009 / DV-010 — batch deliver 的 Gate 3 确认失败：有声但不阻断闭合
# --------------------------------------------------------------------------- #

def _make_batch_with_child(tmp_path: Path) -> tuple[Path, Path, Path]:
    proj = tmp_path / "proj"
    batch = proj / ".fstdd" / "batches" / "BATCH-S4A"
    child = batch / "changes" / "s4a-child"
    child.mkdir(parents=True)
    (batch / ".fstdd.yaml").write_text(
        yaml.safe_dump({
            "name": "BATCH-S4A",
            "created_at": "2026-09-18T10:00:00+00:00",
            "items": ["s4a-child"],
            "current_phase": "build",
        }, allow_unicode=True),
        encoding="utf-8")
    (child / ".fstdd.yaml").write_text(
        yaml.safe_dump({"phases": {"build": {"status": "completed"}}}, allow_unicode=True),
        encoding="utf-8")
    (child / "test-report.md").write_text("# child report\n", encoding="utf-8")
    return proj, batch, child


def test_dfx_009_deliver_warns_and_still_closes_on_gate3_error(tmp_path, monkeypatch, capfd):
    from fstdd.cli.commands import gate as gate_mod

    def boom(*args, **kwargs):
        raise RuntimeError("模拟 Gate 3 确认失败")

    monkeypatch.setattr(gate_mod, "_confirm_gate", boom)
    proj, batch_dir, _ = _make_batch_with_child(tmp_path)

    batch._cmd_batch_deliver(proj, batch_dir,
                             confirmed_by="dialog", evidence="用户确认原文")

    err = capfd.readouterr().err
    assert "Gate 3 确认失败" in err, f"Gate 3 确认失败被静默吞掉: stderr={err!r}"
    # 闭合优先：批次仍推进到 deliver 并产出 test-report.md
    data = yaml.safe_load((batch_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
    assert data.get("current_phase") == "deliver", data
    assert (batch_dir / "test-report.md").exists()
