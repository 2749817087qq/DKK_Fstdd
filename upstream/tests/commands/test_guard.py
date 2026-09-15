"""Tests for stdd guard CLI — intelligent enforcement gate (V2.9.3)."""

import argparse
import io
import json
import yaml

from fstdd.cli.commands.guard import (
    _find_active_change,
    _find_open_batch,
    _classify_description,
    _SCOPE_MICRO,
    _SCOPE_SMALL,
    _SCOPE_MEDIUM,
    _SCOPE_LARGE,
)


class TestFindActiveChange:
    """Test _find_active_change with both 'phase' and 'current_phase' keys."""

    def test_finds_change_with_current_phase(self, tmp_path):
        """REQ: 应识别使用 current_phase 字段的 change（new.py 的标准格式）。"""
        changes_dir = tmp_path / ".stdd" / "changes"
        change_dir = changes_dir / "2026-06-06-test-fix"
        change_dir.mkdir(parents=True)
        (change_dir / ".stdd.yaml").write_text(yaml.dump({
            "status": "active",
            "current_phase": "build",
        }), encoding="utf-8")

        found, phase = _find_active_change(tmp_path)
        assert found is not None
        assert found.name == "2026-06-06-test-fix"
        assert phase == "build"

    def test_finds_change_with_legacy_phase(self, tmp_path):
        """向后兼容：也识别使用 phase 字段的旧格式 change，并归一化旧阶段（verify→build）。"""
        changes_dir = tmp_path / ".stdd" / "changes"
        change_dir = changes_dir / "2026-06-05-old-format"
        change_dir.mkdir(parents=True)
        (change_dir / ".stdd.yaml").write_text(yaml.dump({
            "status": "active",
            "phase": "verify",
        }), encoding="utf-8")

        found, phase = _find_active_change(tmp_path)
        assert found is not None
        # V3.0.5: LEGACY_PHASE_MAP 将旧阶段 verify/slice 归一化为 build
        assert phase == "build"

    def test_skips_batch_directory(self, tmp_path):
        """REQ: _batch 目录不应被识别为 active change。"""
        changes_dir = tmp_path / ".stdd" / "changes"
        batch_dir = changes_dir / "_batch" / "2026-06-06"
        batch_dir.mkdir(parents=True)
        (batch_dir / ".stdd.yaml").write_text(yaml.dump({
            "mode": "batch",
            "batch_id": "2026-06-06",
            "closed_at": None,
        }), encoding="utf-8")

        found, phase = _find_active_change(tmp_path)
        assert found is None

    def test_returns_none_when_no_changes(self, tmp_path):
        """无 changes 目录时返回 None。"""
        found, phase = _find_active_change(tmp_path)
        assert found is None

    def test_current_phase_has_priority_over_legacy_phase(self, tmp_path):
        """current_phase 优先于 phase。"""
        changes_dir = tmp_path / ".stdd" / "changes"
        change_dir = changes_dir / "2026-06-06-both"
        change_dir.mkdir(parents=True)
        (change_dir / ".stdd.yaml").write_text(yaml.dump({
            "status": "active",
            "current_phase": "build",
            "phase": "understand",
        }), encoding="utf-8")

        _, phase = _find_active_change(tmp_path)
        assert phase == "build"  # current_phase wins


class TestFindOpenBatch:
    """Test _find_open_batch. Returns (batch_dir, batch_data) tuple."""

    def test_finds_open_batch(self, tmp_path):
        batches_dir = tmp_path / ".stdd" / "changes" / "_batch" / "2026-06-06"
        batches_dir.mkdir(parents=True)
        (batches_dir / ".stdd.yaml").write_text(yaml.dump({
            "mode": "batch",
            "batch_id": "2026-06-06",
            "closed_at": None,
        }), encoding="utf-8")

        batch_dir, batch_data = _find_open_batch(tmp_path)
        assert batch_dir is not None
        assert batch_dir.name == "2026-06-06"

    def test_skips_closed_batch(self, tmp_path):
        batches_dir = tmp_path / ".stdd" / "changes" / "_batch" / "2026-06-05"
        batches_dir.mkdir(parents=True)
        (batches_dir / ".stdd.yaml").write_text(yaml.dump({
            "mode": "batch",
            "batch_id": "2026-06-05",
            "closed_at": "2026-06-05T12:00:00",
        }), encoding="utf-8")

        batch_dir, batch_data = _find_open_batch(tmp_path)
        assert batch_dir is None

    def test_returns_none_when_no_batches(self, tmp_path):
        batch_dir, batch_data = _find_open_batch(tmp_path)
        assert batch_dir is None


class TestClassifyDescription:
    """Test _classify_description scope classifier."""

    def test_micro_fix(self):
        assert _classify_description("修复一个typo") == _SCOPE_MICRO
        assert _classify_description("fix a bug") == _SCOPE_MICRO
        assert _classify_description("改个变量名") == _SCOPE_MICRO

    def test_small_change(self):
        assert _classify_description("优化日志输出格式") == _SCOPE_SMALL
        assert _classify_description("调整UI界面显示") == _SCOPE_SMALL

    def test_medium_change(self):
        assert _classify_description("重构交易模块数据处理") == _SCOPE_MEDIUM

    def test_large_change(self):
        assert _classify_description("新增交易风控API接口模块") == _SCOPE_LARGE
        assert _classify_description("重写K线分析架构引擎") == _SCOPE_LARGE

    def test_english_keywords(self):
        # "rewrite"=10 + "architecture"=10 + "system"=10 = 30 → LARGE
        assert _classify_description("rewrite the system architecture") == _SCOPE_LARGE
        # "fix"=1 + "typo"=1 = 2 → MICRO
        assert _classify_description("fix typo in readme") == _SCOPE_MICRO
        # "improve"=2 + "UI"=2 = 4 → SMALL
        assert _classify_description("improve UI") == _SCOPE_SMALL


class TestGuardHookStdin:
    """V3.0.5: guard --hook-stdin 路径感知 — token 阻断 / YAML-first 放行 / 普通文件按 phase."""

    def _make_args(self, **kw):
        ns = argparse.Namespace(command="guard", action="check", platform="cli",
                                strict=False, quiet=False, dry_run=False, verbose=0)
        for k, v in kw.items():
            setattr(ns, k, v)
        return ns

    def _stdin_json(self, monkeypatch, tool_name, file_path, content=""):
        payload = json.dumps({"tool_name": tool_name,
                              "tool_input": {"file_path": file_path, "content": content}})
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    def _setup_change(self, tmp_path, current_phase="build", done=("understand", "spec")):
        """Create active change. done = 已完成的 phase（用于 integrity）。"""
        changes_dir = tmp_path / ".stdd" / "changes"
        change_dir = changes_dir / "2026-06-06-path-test"
        change_dir.mkdir(parents=True)
        (tmp_path / ".stdd" / "config.d").mkdir(parents=True)
        (tmp_path / ".stdd" / "config.d" / "project.yaml").write_text(
            yaml.dump({"project": {"name": "t", "language": "python"}, "enforce_stdd": True}),
            encoding="utf-8")
        phases = {p: {"status": "completed" if p in done else "pending"}
                  for p in ("understand", "spec", "build", "deliver")}
        for p in done:
            phases[p]["confirmed_at"] = f"2026-06-06T1{len(done)}:00:00"
        (change_dir / ".stdd.yaml").write_text(yaml.dump({
            "change_id": "2026-06-06-path-test", "status": "active",
            "current_phase": current_phase, "task_type": "code", "version": "3.0",
            "phases": phases,
        }, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        return change_dir

    def test_blocks_gate_token_write_any_phase(self, tmp_path, monkeypatch):
        """SC-GUARD-004: 任何 phase 写 GATE token → exit 2."""
        change_dir = self._setup_change(tmp_path, "build")
        self._stdin_json(monkeypatch, "Write", str(change_dir / "GATE3_APPROVED"))
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 2

    def test_blocks_state_confirmation_edit(self, tmp_path, monkeypatch):
        """SC-GUARD-004: .stdd.yaml 内容含 confirmed_at/by → exit 2."""
        change_dir = self._setup_change(tmp_path, "build")
        self._stdin_json(monkeypatch, "Write", str(change_dir / ".stdd.yaml"),
                         content="confirmed_at: 2026-06-06T10:00:00\nconfirmed_by: dialog\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 2

    def test_allows_canonical_in_understand(self, tmp_path, monkeypatch):
        """SC-GUARD-002: understand 阶段写 canonical YAML → 放行 (YAML-first)。"""
        change_dir = self._setup_change(tmp_path, "understand", done=())
        canon = change_dir / "canonical" / "proposals" / "2026-06-06-path-test.yaml"
        self._stdin_json(monkeypatch, "Write", str(canon), content="meta:\n  change_id: x\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0

    def test_allows_change_docs_in_spec(self, tmp_path, monkeypatch):
        """SC-GUARD-002: spec 阶段写 change 内 design.md/test-plan.md → 放行。"""
        change_dir = self._setup_change(tmp_path, "spec", done=("understand",))
        for fname in ("design.md", "test-plan.md"):
            self._stdin_json(monkeypatch, "Write", str(change_dir / fname), content="# doc\n")
            monkeypatch.chdir(tmp_path)
            from fstdd.cli.commands.guard import cmd_guard_check
            assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0

    def test_blocks_source_code_in_understand(self, tmp_path, monkeypatch):
        """SC-GUARD-003: understand 阶段写源码 → exit 2（非流程产出物）。"""
        self._setup_change(tmp_path, "understand", done=())
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "app" / "foo.py"), content="x=1\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 2

    def test_allows_normal_file_in_build(self, tmp_path, monkeypatch):
        """SC-GUARD-005: build 阶段写普通文件 → 放行。"""
        self._setup_change(tmp_path, "build", done=("understand", "spec"))
        self._stdin_json(monkeypatch, "Edit", str(tmp_path / "app" / "foo.py"))
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0

    def test_stdin_parse_failure_fails_open(self, tmp_path, monkeypatch):
        """REQ-GUARD-001: stdin 解析失败 → fail-open return 0（不误伤编辑）。"""
        self._setup_change(tmp_path, "build", done=("understand", "spec"))
        monkeypatch.setattr("sys.stdin", io.StringIO("not-json {{{"))
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0
