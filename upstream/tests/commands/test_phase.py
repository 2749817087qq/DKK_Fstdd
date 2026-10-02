"""Tests for stdd phase CLI — 4-phase model (V3.0.5).

Covers: 4-phase advance order, gate confirmation gates, build→deliver
per-slice evidence chain, and legacy 6-phase normalization.
"""

import argparse
import yaml
import pytest
from pathlib import Path
from datetime import date

from fstdd.cli.commands.phase import cmd_phase
from fstdd.cli.commands.phase_constants import (
    PHASE_ORDER,
    GATE_PHASES,
    LEGACY_PHASE_MAP,
    SLICES_COMPLETED_PATH,
)


def _write(change_dir: Path, data: dict) -> None:
    (change_dir / ".fstdd.yaml").write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def _read(change_dir: Path) -> dict:
    return yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))


def _make_change(project_root: Path, name: str, current_phase: str,
                 phases: dict = None, **extra) -> Path:
    today = date.today().isoformat()
    change_dir = project_root / ".fstdd" / "changes" / f"{today}-{name}"
    change_dir.mkdir(parents=True)
    if phases is None:
        phases = {p: {"status": "pending"} for p in PHASE_ORDER}
        phases[current_phase]["status"] = "in_progress"
    state = {
        "version": "3.0",
        "change_id": f"{today}-{name}",
        "status": "active",
        "current_phase": current_phase,
        "phases": phases,
    }
    state.update(extra)
    _write(change_dir, state)
    return change_dir


def _advance_args():
    return argparse.Namespace(phase_action="advance", name=None, target_phase=None)


def _set_args(target: str):
    return argparse.Namespace(phase_action="set", name=None, target_phase=target)


def _gate_confirm(data: dict, phase: str) -> dict:
    data["phases"][phase]["confirmed_at"] = "2026-08-17T00:00:00"
    return data


class TestPhaseConstants:
    def test_phase_order_is_four_phases(self):
        assert PHASE_ORDER == ["understand", "spec", "build", "deliver"]

    def test_gate_phases_map(self):
        # Gate 3 now confirms the merged BUILD phase (V3.0.5)
        assert GATE_PHASES == {"understand": "Gate 1", "spec": "Gate 2", "build": "Gate 3"}

    def test_legacy_map_normalizes_to_build(self):
        assert LEGACY_PHASE_MAP == {"slice": "build", "verify": "build"}

    def test_slices_key_path(self):
        assert SLICES_COMPLETED_PATH == ("phases", "build", "slices_completed")


class TestAdvanceFlow:
    def test_full_advance_sequence(self, temp_project, monkeypatch):
        """understand → spec → build → deliver with gates confirmed."""
        ch = _make_change(temp_project, "flow", "understand")
        data = _read(ch)
        data = _gate_confirm(data, "understand")
        _write(ch, data)

        monkeypatch.chdir(temp_project)

        # understand (Gate 1 confirmed) → spec
        cmd_phase(_advance_args())
        assert _read(ch)["current_phase"] == "spec"
        assert _read(ch)["phases"]["understand"]["status"] == "completed"
        assert _read(ch)["phases"]["spec"]["status"] == "in_progress"

        # spec (Gate 2 confirmed) → build
        data = _read(ch)
        data = _gate_confirm(data, "spec")
        _write(ch, data)
        cmd_phase(_advance_args())
        assert _read(ch)["current_phase"] == "build"

        # build: add per-slice evidence + Gate 3 confirm + test-report → deliver
        data = _read(ch)
        data["phases"]["build"]["slices_completed"] = {
            "1": {"status": "done", "tc_coverage": "3/3", "new_tests": 3, "verified_at": "2026-08-17T01:00:00"},
        }
        data = _gate_confirm(data, "build")
        _write(ch, data)
        (ch / "test-report.md").write_text("# Test Report", encoding="utf-8")

        cmd_phase(_advance_args())
        assert _read(ch)["current_phase"] == "deliver"
        assert _read(ch)["phases"]["build"]["status"] == "completed"
        assert _read(ch)["phases"]["deliver"]["status"] == "in_progress"

    def test_advance_blocked_without_gate_confirmation(self, temp_project, monkeypatch):
        """未确认 Gate 时不允许推进（understand 需要 Gate 1）。"""
        ch = _make_change(temp_project, "no-gate", "understand")
        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit):
            cmd_phase(_advance_args())

    def test_advance_at_final_phase_is_noop(self, temp_project, monkeypatch):
        """deliver 已是最终阶段，推进是 no-op（exit 0，不改变状态）。"""
        ch = _make_change(temp_project, "final", "deliver")
        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit) as ei:
            cmd_phase(_advance_args())
        assert ei.value.code == 0
        assert _read(ch)["current_phase"] == "deliver"


class TestBuildDeliverEvidence:
    def test_build_to_deliver_blocked_without_slices(self, temp_project, monkeypatch):
        """BUILD → DELIVER 缺少 per-slice 证据链时被拦截。"""
        ch = _make_change(temp_project, "no-evidence", "build")
        data = _read(ch)
        data = _gate_confirm(data, "build")
        _write(ch, data)
        (ch / "test-report.md").write_text("# Test Report", encoding="utf-8")

        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit):
            cmd_phase(_advance_args())

    def test_build_to_deliver_blocked_with_partial_slice_evidence(self, temp_project, monkeypatch):
        """切片证据不完整（缺 verified_at）时被拦截。"""
        ch = _make_change(temp_project, "partial", "build")
        data = _read(ch)
        data["phases"]["build"]["slices_completed"] = {
            "1": {"status": "done", "tc_coverage": "2/2", "new_tests": 2},  # no verified_at
        }
        data = _gate_confirm(data, "build")
        _write(ch, data)
        (ch / "test-report.md").write_text("# Test Report", encoding="utf-8")

        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit):
            cmd_phase(_advance_args())

    def test_build_to_deliver_blocked_without_test_report(self, temp_project, monkeypatch):
        """证据完整但缺 test-report.md 时被拦截。"""
        ch = _make_change(temp_project, "no-report", "build")
        data = _read(ch)
        data["phases"]["build"]["slices_completed"] = {
            "1": {"status": "done", "tc_coverage": "2/2", "new_tests": 2, "verified_at": "2026-08-17T01:00:00"},
        }
        data = _gate_confirm(data, "build")
        _write(ch, data)

        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit):
            cmd_phase(_advance_args())

    def test_build_to_deliver_succeeds_with_full_evidence(self, temp_project, monkeypatch):
        """证据链完整 + test-report.md 存在时推进成功。"""
        ch = _make_change(temp_project, "full", "build")
        data = _read(ch)
        data["phases"]["build"]["slices_completed"] = {
            "1": {"status": "done", "tc_coverage": "2/2", "new_tests": 2, "verified_at": "2026-08-17T01:00:00"},
        }
        data = _gate_confirm(data, "build")
        _write(ch, data)
        (ch / "test-report.md").write_text("# Test Report", encoding="utf-8")

        monkeypatch.chdir(temp_project)
        cmd_phase(_advance_args())
        assert _read(ch)["current_phase"] == "deliver"


class TestLegacyNormalization:
    def test_advance_from_legacy_verify_normalizes(self, temp_project, monkeypatch):
        """旧 6-phase 数据（current_phase=verify）归一化为 build 后可推进。"""
        ch = _make_change(temp_project, "legacy", "verify", phases={
            "understand": {"status": "completed", "confirmed_at": "2026-08-17T00:00:00"},
            "spec": {"status": "completed", "confirmed_at": "2026-08-17T00:00:00"},
            "build": {"status": "in_progress",
                      "slices_completed": {
                          "1": {"status": "done", "tc_coverage": "2/2", "new_tests": 2,
                                "verified_at": "2026-08-17T01:00:00"}},
                      "confirmed_at": "2026-08-17T01:00:00"},
            "verify": {"status": "in_progress", "confirmed_at": "2026-08-17T01:00:00"},
            "deliver": {"status": "pending"},
        })
        (ch / "test-report.md").write_text("# Test Report", encoding="utf-8")

        monkeypatch.chdir(temp_project)
        cmd_phase(_advance_args())
        assert _read(ch)["current_phase"] == "deliver"


class TestPhaseSet:
    def test_set_valid_phase(self, temp_project, monkeypatch):
        ch = _make_change(temp_project, "set-ok", "understand")
        monkeypatch.chdir(temp_project)
        cmd_phase(_set_args("build"))
        assert _read(ch)["current_phase"] == "build"

    def test_set_invalid_phase(self, temp_project, monkeypatch):
        ch = _make_change(temp_project, "set-bad", "understand")
        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit):
            cmd_phase(_set_args("slice"))  # 旧阶段不再是合法目标


class TestRecordSlice:
    def _args(self, name, slice_id, tc_coverage="TC-001", new_tests=2,
              verified_at="2026-09-17T10:00:00"):
        return __import__("argparse").Namespace(
            phase_action="record-slice", name=name, target_phase=slice_id,
            tc_coverage=tc_coverage, new_tests=new_tests, verified_at=verified_at,
        )

    def test_record_slice_writes_controlled_evidence(self, temp_project, monkeypatch):
        ch = _make_change(temp_project, "record", "build")
        monkeypatch.chdir(temp_project)
        cmd_phase(self._args(ch.name, "S1", "TC-001,TC-002", 3))
        data = _read(ch)
        assert data["phases"]["build"]["slices_completed"]["S1"] == {
            "tc_coverage": "TC-001,TC-002",
            "new_tests": 3,
            "verified_at": "2026-09-17T10:00:00",
        }

    def test_record_slice_rejects_conflicting_overwrite(self, temp_project, monkeypatch):
        ch = _make_change(temp_project, "record-conflict", "build")
        monkeypatch.chdir(temp_project)
        cmd_phase(self._args(ch.name, "S1"))
        with pytest.raises(SystemExit) as exc_info:
            cmd_phase(self._args(ch.name, "S1", "TC-999"))
        assert exc_info.value.code == 1

    def test_record_slice_requires_build_phase(self, temp_project, monkeypatch):
        ch = _make_change(temp_project, "record-phase", "spec")
        monkeypatch.chdir(temp_project)
        with pytest.raises(SystemExit) as exc_info:
            cmd_phase(self._args(ch.name, "S1"))
        assert exc_info.value.code == 1
