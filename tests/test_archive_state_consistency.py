"""test_archive_state_consistency.py — 归档/恢复两端的相位状态自洽

覆盖 TC-ASC-001..006（capability: archive-state-consistency）
对应 spec：`.fstdd/changes/2026-10-07-change-dir-resolution-unify/canonical/specs/code/archive-state-consistency.yaml`
  → REQ-001 / SC-201（归档即闭合）、SC-202（只动两个字段）
  → REQ-002 / SC-203（恢复保留原相位）、SC-204（phases 零改动）、SC-205（往返一致）

背景（实测 @f7bf8ec）：
- `archive` 只把 `status` 置 archived，**不闭合 `phases.deliver.status`** ⇒ 归档态悬空
  （3 个历史归档 change 分别停在 in_progress / pending / 更早的 build）。
- `rollback` 写死 `state["current_phase"] = "understand"`，而 `phases.*.status` 全部保留
  ⇒ 恢复后 `current_phase=understand` 与 `phases.understand.status=completed` 自相矛盾。

⚠️ 纪律：本文件所有 `archive` / `rollback` 调用都在 **tmp_path 合成项目**内进行，
   绝不对仓库内的真实 change 执行移动类操作（EXP-2026-0015 / EXP-2026-0023）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import repo_root

REPO = repo_root()
CLI = REPO / "upstream" / "bin" / "fstdd"

SYNTH = "2026-01-01-synth"

#: 闸门审计字段（C3/C4 必须逐字段保持不变）
GATE_FIELDS = ("confirmed_at", "confirmed_by", "confirmed_evidence")


def _mk_project(tmp_path: Path, name: str = SYNTH, current_phase: str = "deliver") -> Path:
    """合成项目：一个 BUILD 已完成、处于 deliver 相位、三道闸门均已确认的在办 change。"""
    cd = tmp_path / ".fstdd" / "changes" / name
    cd.mkdir(parents=True)
    state = {
        "change_id": name,
        "complexity_score": 9,
        "current_phase": current_phase,
        "design_adjustments": {"count": 0},
        "mode": "thorough",
        "phases": {
            "build": {
                "status": "completed",
                "confirmed_at": "2026-01-01T03:00:00+00:00",
                "confirmed_by": "dialog",
                "confirmed_evidence": "确认",
            },
            "deliver": {"status": "in_progress"},
            "spec": {
                "status": "completed",
                "confirmed_at": "2026-01-01T02:00:00+00:00",
                "confirmed_by": "dialog",
                "confirmed_evidence": "确认",
            },
            "understand": {
                "status": "completed",
                "confirmed_at": "2026-01-01T01:00:00+00:00",
                "confirmed_by": "dialog",
                "confirmed_evidence": "确认",
            },
        },
        "score_confidence": "preliminary",
        "status": "active",
        "task_type": "code",
        "traceability": {"spec_scenarios": 1, "tc_cases": 1, "test_functions": 1},
        "version": "3.0",
    }
    (cd / ".fstdd.yaml").write_text(
        yaml.safe_dump(state, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
        newline="",
    )
    return cd


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(project),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _read_state(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _archive(project: Path, name: str = SYNTH) -> subprocess.CompletedProcess:
    return _run(project, "archive", name, "--skip-specs")


def _rollback(project: Path, name: str = SYNTH) -> subprocess.CompletedProcess:
    return _run(project, "rollback", name)


def _gate_fields(state: dict) -> dict:
    """抽取全部闸门审计字段（用于逐字段相等断言）。"""
    out = {}
    for phase, body in (state.get("phases") or {}).items():
        for f in GATE_FIELDS:
            if f in body:
                out[f"{phase}.{f}"] = body[f]
    return out


# ============================================================
# TC-ASC-001 / SC-201 — 归档即闭合 phases.deliver.status
# ============================================================
def test_tc_asc_001_archive_closes_deliver_phase(tmp_path):
    cd = _mk_project(tmp_path)
    assert _read_state(cd / ".fstdd.yaml")["phases"]["deliver"]["status"] == "in_progress"

    r = _archive(tmp_path)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-400:]}\n{r.stderr[-400:]}"

    archived = tmp_path / ".fstdd" / "archive" / SYNTH
    assert archived.is_dir(), "未归档到 .fstdd/archive/"
    state = _read_state(archived / ".fstdd.yaml")
    assert state["status"] == "archived", state.get("status")
    assert state["phases"]["deliver"]["status"] == "completed", (
        "归档后 phases.deliver.status 未闭合（归档态悬空）—— 本 capability 要修的缺陷"
    )


# ============================================================
# TC-ASC-002 / SC-202 — 归档只动两个字段，闸门字段逐字段不变
# ============================================================
def test_tc_asc_002_archive_touches_only_status_and_deliver(tmp_path):
    cd = _mk_project(tmp_path)
    before = _read_state(cd / ".fstdd.yaml")
    gates_before = _gate_fields(before)

    assert _archive(tmp_path).returncode == 0

    after = _read_state(tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml")
    gates_after = _gate_fields(after)

    # 闸门审计字段：逐字段相等（KG-094：不得抽检）
    assert gates_after == gates_before, (
        f"闸门审计字段被改写：{ {k: (gates_before.get(k), gates_after.get(k)) for k in set(gates_before) | set(gates_after) if gates_before.get(k) != gates_after.get(k)} }"
    )

    # 允许变化的字段：status + phases.deliver.status
    def _normalize(state: dict) -> dict:
        s = yaml.safe_load(yaml.safe_dump(state, allow_unicode=True, sort_keys=True))
        s.pop("status", None)
        s.get("phases", {}).get("deliver", {}).pop("status", None)
        return s

    assert _normalize(after) == _normalize(before), (
        "归档改动了 status / phases.deliver.status 之外的字段"
    )


# ============================================================
# TC-ASC-003 / SC-203 — rollback 保留原 current_phase
# ============================================================
def test_tc_asc_003_rollback_preserves_current_phase(tmp_path):
    cd = _mk_project(tmp_path, current_phase="deliver")
    assert _archive(tmp_path).returncode == 0

    r = _rollback(tmp_path)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout[-400:]}"

    restored = tmp_path / ".fstdd" / "changes" / SYNTH
    assert restored.is_dir(), "未恢复到 changes/"
    state = _read_state(restored / ".fstdd.yaml")
    assert state["status"] == "active", state.get("status")
    assert state["current_phase"] == "deliver", (
        f"rollback 把 current_phase 改成了 {state['current_phase']!r}（应为归档前的 'deliver'）"
    )


def test_tc_asc_003b_rollback_keeps_arbitrary_phase(tmp_path):
    """TC-ASC-003（附加）/ SC-203：相位非 deliver 时同样保留。"""
    """相位不是 deliver 时同样保留（防止「只对 deliver 特判」的假修）。"""
    cd = _mk_project(tmp_path, current_phase="build")
    assert _archive(tmp_path).returncode == 0
    assert _rollback(tmp_path).returncode == 0
    state = _read_state(tmp_path / ".fstdd" / "changes" / SYNTH / ".fstdd.yaml")
    assert state["current_phase"] == "build", state["current_phase"]


# ============================================================
# TC-ASC-004 / SC-204 — rollback 后 phases.* 与闸门字段零改动
# ============================================================
def test_tc_asc_004_rollback_touches_only_status(tmp_path):
    cd = _mk_project(tmp_path)
    assert _archive(tmp_path).returncode == 0
    before = _read_state(tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml")

    assert _rollback(tmp_path).returncode == 0
    after = _read_state(tmp_path / ".fstdd" / "changes" / SYNTH / ".fstdd.yaml")

    # phases 全量逐字段相等（含 status 与闸门字段）
    assert after["phases"] == before["phases"], (
        f"rollback 改动了 phases.*：{ {k: (before['phases'].get(k), after['phases'].get(k)) for k in set(before['phases']) | set(after['phases']) if before['phases'].get(k) != after['phases'].get(k)} }"
    )


# ============================================================
# TC-ASC-005 / SC-205 — 归档 → 恢复 → 再归档 往返一致
# ============================================================
def test_tc_asc_005_archive_rollback_archive_roundtrip(tmp_path):
    cd = _mk_project(tmp_path, current_phase="deliver")

    assert _archive(tmp_path).returncode == 0
    first = _read_state(tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml")

    assert _rollback(tmp_path).returncode == 0
    assert not (tmp_path / ".fstdd" / "archive" / SYNTH).exists(), "rollback 后归档区不应残留"

    assert _archive(tmp_path).returncode == 0
    second = _read_state(tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml")

    assert second["current_phase"] == first["current_phase"] == "deliver"
    assert second["phases"] == first["phases"], "往返后 phases 不一致"
    assert second["status"] == "archived"


# ============================================================
# TC-ASC-006 / SC-203 AND-2 — rollback 冲突检查不回归
# ============================================================
def test_tc_asc_006_rollback_refuses_on_conflict(tmp_path):
    cd = _mk_project(tmp_path)
    assert _archive(tmp_path).returncode == 0

    # 人为制造冲突：changes/ 下再放一个同名目录
    conflict = tmp_path / ".fstdd" / "changes" / SYNTH
    conflict.mkdir(parents=True)
    (conflict / ".fstdd.yaml").write_text("change_id: synth\n", encoding="utf-8", newline="")

    before_archived = (tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml").read_bytes()
    r = _rollback(tmp_path)

    assert r.returncode != 0, "同名冲突时 rollback 应拒绝"
    assert "冲突" in (r.stdout + r.stderr), f"未给出冲突提示：{r.stdout[-300:]}"
    assert (tmp_path / ".fstdd" / "archive" / SYNTH).is_dir(), "冲突时归档区不应被移动"
    assert (tmp_path / ".fstdd" / "archive" / SYNTH / ".fstdd.yaml").read_bytes() == before_archived
