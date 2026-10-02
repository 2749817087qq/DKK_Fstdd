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
        changes_dir = tmp_path / ".fstdd" / "changes"
        change_dir = changes_dir / "2026-06-06-test-fix"
        change_dir.mkdir(parents=True)
        (change_dir / ".fstdd.yaml").write_text(yaml.dump({
            "status": "active",
            "current_phase": "build",
        }), encoding="utf-8")

        found, phase = _find_active_change(tmp_path)
        assert found is not None
        assert found.name == "2026-06-06-test-fix"
        assert phase == "build"

    def test_finds_change_with_legacy_phase(self, tmp_path):
        """向后兼容：也识别使用 phase 字段的旧格式 change，并归一化旧阶段（verify→build）。"""
        changes_dir = tmp_path / ".fstdd" / "changes"
        change_dir = changes_dir / "2026-06-05-old-format"
        change_dir.mkdir(parents=True)
        (change_dir / ".fstdd.yaml").write_text(yaml.dump({
            "status": "active",
            "phase": "verify",
        }), encoding="utf-8")

        found, phase = _find_active_change(tmp_path)
        assert found is not None
        # V3.0.5: LEGACY_PHASE_MAP 将旧阶段 verify/slice 归一化为 build
        assert phase == "build"

    def test_skips_batch_directory(self, tmp_path):
        """REQ: _batch 目录不应被识别为 active change。"""
        changes_dir = tmp_path / ".fstdd" / "changes"
        batch_dir = changes_dir / "_batch" / "2026-06-06"
        batch_dir.mkdir(parents=True)
        (batch_dir / ".fstdd.yaml").write_text(yaml.dump({
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
        changes_dir = tmp_path / ".fstdd" / "changes"
        change_dir = changes_dir / "2026-06-06-both"
        change_dir.mkdir(parents=True)
        (change_dir / ".fstdd.yaml").write_text(yaml.dump({
            "status": "active",
            "current_phase": "build",
            "phase": "understand",
        }), encoding="utf-8")

        _, phase = _find_active_change(tmp_path)
        assert phase == "build"  # current_phase wins


class TestFindOpenBatch:
    """Test _find_open_batch. Returns (batch_dir, batch_data) tuple."""

    def test_finds_open_batch(self, tmp_path):
        batches_dir = tmp_path / ".fstdd" / "changes" / "_batch" / "2026-06-06"
        batches_dir.mkdir(parents=True)
        (batches_dir / ".fstdd.yaml").write_text(yaml.dump({
            "mode": "batch",
            "batch_id": "2026-06-06",
            "closed_at": None,
        }), encoding="utf-8")

        batch_dir, batch_data = _find_open_batch(tmp_path)
        assert batch_dir is not None
        assert batch_dir.name == "2026-06-06"

    def test_skips_closed_batch(self, tmp_path):
        batches_dir = tmp_path / ".fstdd" / "changes" / "_batch" / "2026-06-05"
        batches_dir.mkdir(parents=True)
        (batches_dir / ".fstdd.yaml").write_text(yaml.dump({
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
        changes_dir = tmp_path / ".fstdd" / "changes"
        change_dir = changes_dir / "2026-06-06-path-test"
        change_dir.mkdir(parents=True)
        (tmp_path / ".fstdd" / "config.d").mkdir(parents=True)
        (tmp_path / ".fstdd" / "config.d" / "project.yaml").write_text(
            yaml.dump({"project": {"name": "t", "language": "python"}, "enforce_stdd": True}),
            encoding="utf-8")
        phases = {p: {"status": "completed" if p in done else "pending"}
                  for p in ("understand", "spec", "build", "deliver")}
        for p in done:
            phases[p]["confirmed_at"] = f"2026-06-06T1{len(done)}:00:00"
        (change_dir / ".fstdd.yaml").write_text(yaml.dump({
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
        """SC-GUARD-004: .fstdd.yaml 内容含 confirmed_at/by → exit 2."""
        change_dir = self._setup_change(tmp_path, "build")
        self._stdin_json(monkeypatch, "Write", str(change_dir / ".fstdd.yaml"),
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

    # ── 根因2回归（2026-09-17 修）：阻断爆炸半径不得超出项目边界 ──

    def _setup_broken_change(self, tmp_path):
        """构造 integrity 失败的 active change（status=completed 但缺 confirmed_at）。

        复刻真实触发样本：迁移期手写 gate: approved 代替 confirmed_at。
        """
        change_dir = self._setup_change(tmp_path, "build", done=("understand", "spec"))
        state_path = change_dir / ".fstdd.yaml"
        data = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        for p in ("understand", "spec"):
            data["phases"][p].pop("confirmed_at", None)
            data["phases"][p]["gate"] = "approved"
        state_path.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8"
        )
        return change_dir

    def test_broken_change_does_not_block_other_project(self, tmp_path, monkeypatch):
        """SC-GUARD-006: 本项目 change 残缺时，写**其他项目**路径 SHALL 放行。"""
        self._setup_broken_change(tmp_path)
        outside = tmp_path.parent / "another-project" / "notes.md"
        self._stdin_json(monkeypatch, "Write", str(outside), content="hi\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0

    def test_broken_change_still_blocks_in_project_code(self, tmp_path, monkeypatch):
        """SC-GUARD-007: 同一残缺 change 下写**本项目内**源码 SHALL 仍阻断（不降强度）。"""
        self._setup_broken_change(tmp_path)
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "app" / "foo.py"), content="x=1\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 2

    def test_broken_change_still_blocks_project_root_file(self, tmp_path, monkeypatch):
        """SC-GUARD-007: 项目根下的普通文件同属项目内 → 仍阻断。"""
        self._setup_broken_change(tmp_path)
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "README.md"), content="# x\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 2

    def test_integrity_error_names_change_id(self, tmp_path, monkeypatch, capsys):
        """SC-GUARD-008: integrity 报错 SHALL 含 change_id，便于定位被卡的变更。"""
        self._setup_broken_change(tmp_path)
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "app" / "foo.py"), content="x=1\n")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_check
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 2
        captured = capsys.readouterr()
        assert "2026-06-06-path-test" in (captured.out + captured.err)


class TestGatePhaseOrderDeterminism:
    """根因1回归（2026-09-17 修）：Gate 遍历必须有序 —— 报错不得随 hash seed 变化。"""

    _BROKEN = {"phases": {
        "understand": {"status": "completed"},
        "spec": {"status": "completed"},
        "build": {"status": "in_progress"},
    }}

    def test_gate_phases_is_ordered_sequence(self):
        """SC-GUARD-009: _GATE_PHASES SHALL 为有序序列（set 迭代序随机）。"""
        from fstdd.cli.commands.guard import _GATE_PHASES
        from fstdd.cli.commands.phase_constants import GATE_PHASE_ORDER
        assert not isinstance(_GATE_PHASES, (set, frozenset)), (
            "_GATE_PHASES 为 set → 报错随 hash seed 变化，不可复现"
        )
        assert list(_GATE_PHASES) == list(GATE_PHASE_ORDER)

    def test_reports_earliest_missing_gate(self):
        """SC-GUARD-009: understand/spec 均缺确认 → 必须报最靠前的 Gate 1。"""
        from fstdd.cli.commands.guard import _check_phase_integrity
        ok, reason = _check_phase_integrity(dict(self._BROKEN), "build")
        assert ok is False
        assert "understand" in reason
        assert "Gate 1" in reason

    def test_message_stable_across_hash_seeds(self):
        """SC-GUARD-009: 跨进程不同 PYTHONHASHSEED 下报错 SHALL 完全一致。"""
        import os
        import subprocess
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        code = (
            "import sys; sys.path.insert(0, {root!r});"
            "from fstdd.cli.commands.guard import _check_phase_integrity;"
            "d={{'phases':{{'understand':{{'status':'completed'}},"
            "'spec':{{'status':'completed'}},'build':{{'status':'in_progress'}}}}}};"
            "print(_check_phase_integrity(d, 'build')[1])"
        ).format(root=str(root))
        seen = set()
        for seed in ("1", "2", "3", "4", "5"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            proc = subprocess.run([sys.executable, "-c", code], env=env,
                                  capture_output=True, text=True)
            assert proc.returncode == 0, proc.stderr
            seen.add(proc.stdout.strip())
        assert len(seen) == 1, f"报错随 PYTHONHASHSEED 变化：{seen}"


class TestGateFieldDiagnostics:
    """根因3回归（2026-09-17 修）：字段口径 —— 非法 gate 字段不得冒充确认凭据。"""

    _BROKEN = {"phases": {
        "understand": {"status": "completed", "gate": "approved"},
        "spec": {"status": "completed", "gate": "approved"},
        "build": {"status": "in_progress"},
    }}

    def test_gate_field_is_not_a_confirmation_credential(self):
        """SC-GUARD-010: 手写 gate: approved 不构成确认凭据 → 仍判定不完整。"""
        from fstdd.cli.commands.guard import _check_phase_integrity
        ok, _ = _check_phase_integrity(dict(self._BROKEN), "build")
        assert ok is False

    def test_error_lists_actual_fields(self):
        """SC-GUARD-010: 报错 SHALL 列出该 phase 实际字段，一眼看出缺 confirmed_at。"""
        from fstdd.cli.commands.guard import _check_phase_integrity
        _, reason = _check_phase_integrity(dict(self._BROKEN), "build")
        assert "confirmed_at" in reason
        assert "gate" in reason

    def test_error_gives_actionable_command(self):
        """SC-GUARD-010: 报错 SHALL 给出可复制的修复命令。"""
        from fstdd.cli.commands.guard import _check_phase_integrity
        _, reason = _check_phase_integrity(dict(self._BROKEN), "build")
        assert "gate approve" in reason

    def test_blocks_ai_writing_illegal_gate_field(self, tmp_path):
        """SC-GUARD-011: AI 写 .fstdd.yaml 写入非法 gate 确认字段 → 阻断。"""
        from fstdd.cli.commands.guard import _is_state_confirmation_edit
        state = tmp_path / "x.fstdd.yaml"
        assert _is_state_confirmation_edit(tmp_path, str(state), "gate: approved\n") is True
        assert _is_state_confirmation_edit(tmp_path, str(state), "  gate: approved\n") is True
        # 非确认用途的正常字段不得误伤
        assert _is_state_confirmation_edit(tmp_path, str(state), "gate_notes: x\n") is False
        assert _is_state_confirmation_edit(tmp_path, str(state), "status: active\n") is False


class TestGuardDisable:
    """V3.0.7 回归：guard disable 必须真的关得掉。

    原实现双重失效 ——
    ① 只处理 .claude/settings.local.json，而 init 同时写 .codebuddy/（WorkBuddy 只读后者）；
    ② 匹配串是过期的 "stdd guard"，而 init 实写 '... bin/fstdd" guard check ...'
       （含 "guard check"，不含 "stdd guard"）。
    结果：命令打印 "Already disabled" 但 hook 仍在拦截 —— **以为关了其实没关**。
    """

    # cmd_guard_init 实际写入的命令形态（绝对路径 + guard check）
    INIT_CMD = (
        '"/Users/x/envs/fstdd/bin/python" '
        '"/Users/x/Fstdd/upstream/bin/fstdd" guard check '
        "--platform claude-code --hook-stdin"
    )
    LEGACY_CMD = "python bin/stdd guard check --platform claude-code --hook-stdin"
    OTHER_CMD = "python tools/my_formatter.py --check"

    def _make_args(self, **kw):
        ns = argparse.Namespace(command="guard", action="disable", platform="claude-code",
                                strict=False, quiet=False, dry_run=False, verbose=0)
        for k, v in kw.items():
            setattr(ns, k, v)
        return ns

    def _write_settings(self, root, sub, commands):
        """在 <root>/<sub>/settings.local.json 写入若干 PreToolUse 条目。"""
        d = root / sub
        d.mkdir(parents=True, exist_ok=True)
        data = {
            "permissions": {"allow": ["Bash(git status:*)"]},
            "hooks": {"PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": c}]}
                for c in commands
            ]},
        }
        (d / "settings.local.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return d / "settings.local.json"

    @staticmethod
    def _hook_commands(path):
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [
            h.get("command")
            for entry in data.get("hooks", {}).get("PreToolUse", [])
            for h in entry.get("hooks", [])
        ]

    def test_disable_removes_init_hook_from_both_dirs(self, tmp_path, monkeypatch):
        """SC-GUARD-012: disable SHALL 摘除 .claude/ 与 .codebuddy/ 两处的 init hook。"""
        claude = self._write_settings(tmp_path, ".claude", [self.INIT_CMD])
        codebuddy = self._write_settings(tmp_path, ".codebuddy", [self.INIT_CMD])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())
        assert self.INIT_CMD not in self._hook_commands(claude), ".claude 未摘除"
        assert self.INIT_CMD not in self._hook_commands(codebuddy), ".codebuddy 未摘除"

    def test_disable_removes_legacy_stdd_guard_hook(self, tmp_path, monkeypatch):
        """SC-GUARD-012: 旧写法（stdd guard check）同样要能摘除（向后兼容）。"""
        s = self._write_settings(tmp_path, ".codebuddy", [self.LEGACY_CMD])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())
        assert self._hook_commands(s) == []

    def test_disable_preserves_unrelated_hooks_and_settings(self, tmp_path, monkeypatch):
        """SC-GUARD-013: disable SHALL NOT 误删非 guard hook 与其他 settings。"""
        s = self._write_settings(tmp_path, ".codebuddy", [self.INIT_CMD, self.OTHER_CMD])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())
        cmds = self._hook_commands(s)
        assert cmds == [self.OTHER_CMD]
        data = json.loads(s.read_text(encoding="utf-8"))
        assert data["permissions"]["allow"] == ["Bash(git status:*)"]

    def test_disable_cleans_empty_hooks_key(self, tmp_path, monkeypatch):
        """SC-GUARD-013: 摘除后 hooks 为空 → 不得留下空 hooks/PreToolUse 骨架。"""
        s = self._write_settings(tmp_path, ".claude", [self.INIT_CMD])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())
        data = json.loads(s.read_text(encoding="utf-8"))
        assert "hooks" not in data

    def test_disable_is_idempotent(self, tmp_path, monkeypatch, capsys):
        """SC-GUARD-014: 重复 disable SHALL 幂等且明确报告已关闭。"""
        self._write_settings(tmp_path, ".codebuddy", [self.INIT_CMD])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())
        capsys.readouterr()
        cmd_guard_disable(self._make_args())  # 第二次
        out = capsys.readouterr()
        assert "Already disabled" in (out.out + out.err)

    def test_disable_without_settings_does_not_crash(self, tmp_path, monkeypatch):
        """SC-GUARD-014: 无任何 settings 文件时 SHALL 友好退出，不抛异常。"""
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args())  # 不应抛异常

    def test_disable_dry_run_does_not_write(self, tmp_path, monkeypatch):
        """SC-GUARD-015: --dry-run SHALL 只预览、不落盘（文档承诺）。"""
        s = self._write_settings(tmp_path, ".codebuddy", [self.INIT_CMD])
        before = s.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_disable
        cmd_guard_disable(self._make_args(dry_run=True))
        assert s.read_text(encoding="utf-8") == before, "--dry-run 竟然改写了文件"

    def test_enable_then_disable_roundtrip(self, tmp_path, monkeypatch):
        """SC-GUARD-012: enable(init) → disable 往返后不得残留 guard hook。"""
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.guard import cmd_guard_enable, cmd_guard_disable
        cmd_guard_enable(self._make_args())
        cmd_guard_disable(self._make_args())
        for sub in (".claude", ".codebuddy"):
            cmds = self._hook_commands(tmp_path / sub / "settings.local.json")
            assert not any("guard check" in (c or "") for c in cmds), f"{sub} 残留 guard hook"


class TestGuardChangeScope:
    """V3.0.7: 相位门按 change 声明作用域判定（scope.paths）— 范围外 warn-only。

    对应 test-plan.md TC-SCOPE-001..012 / spec.md SC-001..SC-010。
    """

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

    def _make_change(self, tmp_path, phase="understand", scope=None, cid="2026-09-25-scope-x"):
        """造一个 active change；scope 非 None 时在 canonical proposal 里声明作用域。

        phases 必须是 dict 且已完成相位带 confirmed_at：_check_phase_integrity 会
        先校验这两点，否则在相位门之前就被拦下（测不出作用域行为）。
        """
        change_dir = tmp_path / ".fstdd" / "changes" / cid
        canon = change_dir / "canonical" / "proposals"
        canon.mkdir(parents=True)
        proposal = {"meta": {"change_id": cid}, "why": {"problem": "t"}}
        if scope is not None:
            proposal["scope"] = {"paths": scope}
        (canon / (cid + ".yaml")).write_text(
            yaml.dump(proposal, allow_unicode=True), encoding="utf-8")
        order = ["understand", "spec", "build", "deliver"]
        phases = {}
        if phase in order:
            idx = order.index(phase)
            for earlier in order[:idx]:
                phases[earlier] = {
                    "status": "completed",
                    "confirmed_at": "2026-09-25T00:00:00+00:00",
                    "confirmed_by": "dialog",
                }
            phases[phase] = {"status": "in_progress"}
            for later in order[idx + 1:]:
                phases[later] = {"status": "pending"}
        (change_dir / ".fstdd.yaml").write_text(yaml.dump({
            "status": "active", "current_phase": phase, "task_type": "code",
            "phases": phases,
        }), encoding="utf-8")
        return change_dir

    # ---- TC-SCOPE-001 / 002: _load_change_scope -------------------------

    def test_tc_scope_001_loads_declared_paths(self, tmp_path):
        from fstdd.cli.commands.guard import _load_change_scope
        d = self._make_change(tmp_path, scope=["a.py", "d/"])
        assert _load_change_scope(d) == ["a.py", "d/"]

    def test_tc_scope_002_returns_none_when_not_declared(self, tmp_path):
        """无 scope 块 / paths 为空 / 无 proposal ⇒ 一律 None（fail-closed）。"""
        from fstdd.cli.commands.guard import _load_change_scope
        c3 = tmp_path / "c3"
        (c3 / ".fstdd" / "changes" / "2026-09-25-noprop").mkdir(parents=True)
        (c3 / ".fstdd" / "changes" / "2026-09-25-noprop" / ".fstdd.yaml").write_text(
            yaml.dump({"status": "active", "current_phase": "understand"}),
            encoding="utf-8")
        cases = [
            self._make_change(tmp_path / "c1", scope=None, cid="2026-09-25-a"),
            self._make_change(tmp_path / "c2", scope=[], cid="2026-09-25-b"),
            c3 / ".fstdd" / "changes" / "2026-09-25-noprop",
        ]
        for d in cases:
            assert _load_change_scope(d) is None, d

    # ---- TC-SCOPE-003..005 / 010: 命中判定 ------------------------------

    def test_tc_scope_003_exact_file_in_scope(self, tmp_path):
        from fstdd.cli.commands.guard import _is_in_change_scope
        assert _is_in_change_scope(tmp_path, str(tmp_path / "src" / "app.py"),
                                   ["src/app.py"]) is True

    def test_tc_scope_004_directory_pattern_matches_descendants(self, tmp_path):
        from fstdd.cli.commands.guard import _is_in_change_scope
        assert _is_in_change_scope(tmp_path, str(tmp_path / "src" / "deep" / "mod.py"),
                                   ["src/"]) is True

    def test_tc_scope_005_out_of_scope_is_false(self, tmp_path):
        from fstdd.cli.commands.guard import _is_in_change_scope
        assert _is_in_change_scope(tmp_path, str(tmp_path / "tools" / "evil.py"),
                                   ["src/"]) is False

    def test_tc_scope_010_dotdot_normalized_before_matching(self, tmp_path):
        """.. 穿越按归一化后的真实位置判定，不做字符串级匹配。"""
        from fstdd.cli.commands.guard import _is_in_change_scope
        escaped = str(tmp_path / "src" / ".." / "tools" / "evil.py")
        assert _is_in_change_scope(tmp_path, escaped, ["src/"]) is False

    # ---- TC-SCOPE-006..009 / 011 / 012: cmd_guard_check 判定序 ----------

    def test_tc_scope_006_in_scope_blocks_in_readonly(self, tmp_path, monkeypatch, capsys):
        """范围内文件在只读相位仍被拦，并提示扩展 scope.paths。"""
        from fstdd.cli.commands.guard import cmd_guard_check
        self._make_change(tmp_path, phase="understand", scope=["src/"])
        (tmp_path / "src").mkdir()
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "src" / "app.py"), "x=1\n")
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 2
        assert "scope.paths" in capsys.readouterr().out

    def test_tc_scope_007_out_of_scope_warns_and_allows(self, tmp_path, monkeypatch, capsys):
        from fstdd.cli.commands.guard import cmd_guard_check
        self._make_change(tmp_path, phase="understand", scope=["src/"])
        (tmp_path / "docs").mkdir()
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "docs" / "x.md"), "# x\n")
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 0
        assert "out of scope" in capsys.readouterr().out

    def test_tc_scope_008_no_scope_declared_keeps_global_block(self, tmp_path, monkeypatch):
        """未声明 scope ⇒ 维持既有全局拦截（fail-closed，行为零漂移）。"""
        from fstdd.cli.commands.guard import cmd_guard_check
        self._make_change(tmp_path, phase="understand", scope=None)
        (tmp_path / "docs").mkdir()
        self._stdin_json(monkeypatch, "Write", str(tmp_path / "docs" / "x.md"), "# x\n")
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 2

    def test_tc_scope_009_gate_token_still_blocked(self, tmp_path, monkeypatch, capsys):
        """硬阻断优先于作用域收窄：GATE token 在任何相位/范围下都拦。"""
        from fstdd.cli.commands.guard import cmd_guard_check
        self._make_change(tmp_path, phase="understand", scope=["src/"])
        (tmp_path / "src").mkdir()
        self._stdin_json(monkeypatch, "Write",
                         str(tmp_path / "src" / "GATE1_APPROVED"), "1\n")
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True)) == 2
        assert "人工创建" in capsys.readouterr().out

    def test_tc_scope_011_yaml_first_artifact_still_allowed(self, tmp_path, monkeypatch):
        """判定序 3（YAML-first 流程产出物）不受作用域收窄影响。"""
        from fstdd.cli.commands.guard import cmd_guard_check
        cd = self._make_change(tmp_path, phase="spec", scope=["src/"])
        self._stdin_json(monkeypatch, "Write",
                         str(cd / "canonical" / "proposals" / "x.yaml"), "meta: {}\n")
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0

    def test_tc_scope_012_editable_phase_ignores_scope(self, tmp_path, monkeypatch):
        """可编辑相位不受作用域影响（SC-009）。"""
        from fstdd.cli.commands.guard import cmd_guard_check
        self._make_change(tmp_path, phase="build", scope=["src/"])
        (tmp_path / "docs").mkdir()
        self._stdin_json(monkeypatch, "Edit", str(tmp_path / "docs" / "x.md"))
        monkeypatch.chdir(tmp_path)
        assert cmd_guard_check(self._make_args(hook_stdin=True, quiet=True)) == 0
