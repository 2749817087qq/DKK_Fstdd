"""Tests for stdd gate CLI command (V2.5 gate-file-confirm)."""
import pytest
import argparse
import yaml


def _make_args(subcommand="approve", **kwargs):
    ns = argparse.Namespace(
        command="gate",
        subcommand=subcommand,
        dry_run=False,
        verbose=0,
    )
    # V3.0.5 硬防线：默认走 dialog 通道（口头确认）。旧测试语义即口头确认。
    kwargs.setdefault("confirmed_by", "dialog")
    kwargs.setdefault("evidence", "")
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _setup_gate_project(tmp_path, gates_confirmed=None):
    """Create project with change directory and .fstdd.yaml."""
    (tmp_path / ".fstdd" / "config.d").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".fstdd" / "config.d" / "gates.yaml").write_text("""\
gates:
  phase1_understand:
    required: true
  phase2_spec:
    required: true
  phase3_build:
    required: true
confirmation:
  channels:
    - dialog
    - file_token
    - cli
""", encoding="utf-8")
    (tmp_path / ".fstdd" / "config.d" / "project.yaml").write_text("""\
paths:
  changes_dir: changes
  archive_dir: archive
project:
  language: python
  name: test
stdd_version: '2.0'
""", encoding="utf-8")
    (tmp_path / ".fstdd" / "changes").mkdir(exist_ok=True)
    change_dir = tmp_path / ".fstdd" / "changes" / "2026-01-01-gate-test"
    change_dir.mkdir(parents=True)

    phases = {
        "understand": {"status": "pending"},
        "spec": {"status": "pending"},
        "build": {"status": "pending"},
        "deliver": {"status": "pending"},
    }

    if gates_confirmed:
        for g in gates_confirmed:
            label, key = {1: ("understand", "understand"), 2: ("spec", "spec"), 3: ("build", "build")}[g]
            phases[key]["status"] = "completed"
            phases[key]["confirmed_at"] = "2026-01-01T10:00:00"

    state = {
        "change_id": "2026-01-01-gate-test",
        "current_phase": "spec",
        "status": "active",
        "version": "2.0",
        "phases": phases,
        "traceability": {"spec_scenarios": 3, "tc_cases": 3, "test_functions": 0},
    }
    (change_dir / ".fstdd.yaml").write_text(
        yaml.dump(state, allow_unicode=True, default_flow_style=False),
        encoding="utf-8"
    )

    return change_dir


class TestGateConfirm:
    """TC-GF-001 ~ 007: Gate file-token and CLI confirmation."""

    def test_cli_approve_gate1(self, tmp_path, monkeypatch, capsys):
        """TC-GF-001: CLI approve Gate 1 writes confirmed_at."""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 1 confirmed" in captured.out

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["understand"]["confirmed_at"] is not None
        assert data["phases"]["understand"]["status"] == "completed"

    def test_idempotent_reconfirm(self, tmp_path, monkeypatch, capsys):
        """TC-GF-002: Re-confirming an already confirmed gate is idempotent."""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "already confirmed" in captured.out

        # confirmed_at should not change
        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["understand"]["confirmed_at"] == "2026-01-01T10:00:00"

    def test_gate_order_validation(self, tmp_path, monkeypatch):
        """TC-GF-003: Cannot confirm Gate 2 before Gate 1."""
        _setup_gate_project(tmp_path)  # No gates confirmed
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 1

    def test_invalid_gate_number(self, tmp_path, monkeypatch):
        """TC-GF-004: Invalid gate number returns error."""
        _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=4)
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 1

    def test_cli_approve_gate3_confirms_build(self, tmp_path, monkeypatch, capsys):
        """TC-GF-008: Gate 3 now confirms the merged BUILD phase (V3.0.5)."""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1, 2])
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=3)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 3 confirmed" in captured.out

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["build"]["confirmed_at"] is not None
        assert data["phases"]["build"]["status"] == "completed"

    def test_file_token_confirmation(self, tmp_path, monkeypatch, capsys):
        """TC-GF-005: GATE<N>_APPROVED file is recognized as confirmation."""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        # Create file token for Gate 2
        (change_dir / "GATE2_APPROVED").touch()
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 2 confirmed" in captured.out

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["spec"]["confirmed_at"] is not None

    def test_amend_audit_appends_without_overwriting_original(self, tmp_path, monkeypatch, capsys):
        """TC-GATE-110: 用户追认追加记录，原始 Gate 审计保持不变。"""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        state_file = change_dir / ".fstdd.yaml"
        data = yaml.safe_load(state_file.read_text(encoding="utf-8"))
        data["phases"]["understand"].update({
            "confirmed_by": "dialog",
            "confirmed_actor": "ai",
            "confirmed_evidence": "历史 AI 记录",
        })
        state_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate
        args = _make_args("amend-audit", name="2026-01-01-gate-test", gate=1,
                          confirmed_by="dialog", evidence="D哥追认 Gate 1")
        cmd_gate(args)

        result = yaml.safe_load(state_file.read_text(encoding="utf-8"))
        original = result["phases"]["understand"]
        assert original["confirmed_actor"] == "ai"
        assert original["confirmed_evidence"] == "历史 AI 记录"
        assert len(result["audit_amendments"]) == 1
        amendment = result["audit_amendments"][0]
        assert amendment["amended_actor"] == "user"
        assert amendment["amended_evidence"] == "D哥追认 Gate 1"
        assert amendment["original_confirmed_actor"] == "ai"

    def test_amend_audit_is_idempotent(self, tmp_path, monkeypatch, capsys):
        """TC-GATE-111: 相同追认请求重复执行不重复追加。"""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.gate import cmd_gate
        args = _make_args("amend-audit", name="2026-01-01-gate-test", gate=1,
                          confirmed_by="dialog", evidence="D哥追认 Gate 1")
        cmd_gate(args)
        cmd_gate(args)
        result = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert len(result["audit_amendments"]) == 1
        assert "already recorded" in capsys.readouterr().out

    def test_amend_audit_rejects_conflicting_evidence(self, tmp_path, monkeypatch):
        """TC-GATE-112: 同一 Gate 的不同追认证据不得覆盖或追加。"""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.gate import cmd_gate
        first = _make_args("amend-audit", name="2026-01-01-gate-test", gate=1,
                           confirmed_by="dialog", evidence="第一份追认")
        second = _make_args("amend-audit", name="2026-01-01-gate-test", gate=1,
                            confirmed_by="dialog", evidence="第二份追认")
        cmd_gate(first)
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(second)
        assert exc_info.value.code == 1
        result = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert len(result["audit_amendments"]) == 1

    def test_amend_audit_requires_existing_gate(self, tmp_path, monkeypatch):
        """TC-GATE-113: 未确认 Gate 不允许追认。"""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.gate import cmd_gate
        args = _make_args("amend-audit", name="2026-01-01-gate-test", gate=1,
                          confirmed_by="dialog", evidence="D哥追认 Gate 1")
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 1
        result = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert "audit_amendments" not in result

    def test_file_token_and_cli_equivalent(self, tmp_path, monkeypatch, capsys):
        """TC-GF-006: File token + CLI approve are equivalent."""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        (change_dir / "GATE2_APPROVED").touch()
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        # First call: confirm via file token
        args = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        cmd_gate(args)

        # Second call: should say already confirmed
        args2 = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        cmd_gate(args2)
        captured = capsys.readouterr()
        assert "already confirmed" in captured.out

    def test_configurable_channels(self, tmp_path, monkeypatch):
        """TC-GF-007: gates.yaml channels config is readable."""
        _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import _read_gates_config
        config = _read_gates_config(tmp_path)
        assert "confirmation" in config
        assert "channels" in config["confirmation"]
        assert "file_token" in config["confirmation"]["channels"]
        assert "cli" in config["confirmation"]["channels"]


class TestGateAutoMD:
    """V3.0.5 (YAML-first): Gate 确认时自动从 Canonical YAML 生成 Human View MD."""

    def test_gate1_auto_generates_proposal_md(self, tmp_path, monkeypatch, capsys):
        """Gate 1 + canonical proposal YAML → proposal.md 自动生成。"""
        change_dir = _setup_gate_project(tmp_path)
        canon_dir = change_dir / "canonical" / "proposals"
        canon_dir.mkdir(parents=True)
        (canon_dir / "2026-01-01-gate-test.yaml").write_text(yaml.dump({
            "meta": {"change_id": "2026-01-01-gate-test", "title": "Gate Auto MD", "status": "draft"},
            "why": {"problem": "Auto MD from YAML"},
            "what_changes": [{"id": "C1", "description": "Add auto-MD", "type": "new"}],
            "capabilities": {"new": []},
            "success_criteria": ["MD generated"]
        }), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 1 confirmed" in captured.out
        assert "自动生成 Human View" in captured.out

        md = change_dir / "proposal.md"
        assert md.exists()
        content = md.read_text(encoding="utf-8")
        assert "Gate Auto MD" in content
        assert "source_hash" in content

    def test_gate1_no_yaml_skips_silently(self, tmp_path, monkeypatch, capsys):
        """Gate 1 + 无 canonical YAML → 正常确认，无 MD 生成（兼容纯 MD 旧流程）。"""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 1 confirmed" in captured.out
        assert "自动生成" not in captured.out
        assert not (change_dir / "proposal.md").exists()

    def test_gate2_auto_generates_spec_md(self, tmp_path, monkeypatch, capsys):
        """Gate 2 + canonical spec YAML → specs/<cap>/spec.md 自动生成。"""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        canon_dir = change_dir / "canonical" / "proposals"
        canon_dir.mkdir(parents=True)
        (canon_dir / "2026-01-01-gate-test.yaml").write_text(yaml.dump({
            "meta": {"change_id": "2026-01-01-gate-test", "title": "T", "status": "draft"},
            "why": {"problem": "p"},
            "capabilities": {"new": []}
        }), encoding="utf-8")
        specs_code = change_dir / "canonical" / "specs" / "code"
        specs_code.mkdir(parents=True)
        (specs_code / "rate-limit.yaml").write_text(yaml.dump({
            "meta": {"capability": "rate-limit", "change_id": "2026-01-01-gate-test",
                     "created": "now", "confidence": "high"},
            "requirements": [{
                "id": "REQ-001",
                "description": "Rate limit enforced",
                "scenarios": [{
                    "id": "SC-001",
                    "given": "requests over limit",
                    "when": "client sends burst",
                    "then": "system SHALL return 429"
                }]
            }]
        }), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 2 confirmed" in captured.out

        spec_md = change_dir / "specs" / "rate-limit" / "spec.md"
        assert spec_md.exists()
        content = spec_md.read_text(encoding="utf-8")
        assert "Rate limit enforced" in content
        assert "429" in content

    def test_gate2_skips_todo_scaffold(self, tmp_path, monkeypatch, capsys):
        """Gate 2 跳过 new.py scaffold 的 TODO 模板 spec（占位 capability 含冒号，Windows 路径非法）。"""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        canon_dir = change_dir / "canonical" / "proposals"
        canon_dir.mkdir(parents=True)
        (canon_dir / "2026-01-01-gate-test.yaml").write_text(yaml.dump({
            "meta": {"change_id": "2026-01-01-gate-test", "title": "T", "status": "draft"},
            "why": {"problem": "p"},
            "capabilities": {"new": []}
        }), encoding="utf-8")
        specs_code = change_dir / "canonical" / "specs" / "code"
        specs_code.mkdir(parents=True)
        # scaffold 模板占位（capability 仍为 TODO）+ 真实 spec
        (specs_code / "2026-01-01-gate-test.yaml").write_text(yaml.dump({
            "meta": {"capability": "TODO: 能力名称", "change_id": "2026-01-01-gate-test"},
            "requirements": []
        }), encoding="utf-8")
        (specs_code / "rate-limit.yaml").write_text(yaml.dump({
            "meta": {"capability": "rate-limit", "change_id": "2026-01-01-gate-test",
                     "created": "now", "confidence": "high"},
            "requirements": [{
                "id": "REQ-001",
                "description": "Rate limit enforced",
                "scenarios": [{"id": "SC-001", "given": "g", "when": "w", "then": "system SHALL 429"}]
            }]
        }), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2)
        cmd_gate(args)  # 不应因 TODO 占位目录创建失败而抛错
        captured = capsys.readouterr()
        assert "Gate 2 confirmed" in captured.out
        assert "1 个 spec.md" in captured.out

        # 只生成真实 spec，不生成 TODO 占位目录
        assert (change_dir / "specs" / "rate-limit" / "spec.md").exists()
        assert not (change_dir / "specs" / "TODO").exists()


class TestGateHardDefense:
    """V3.0.5: Gate 硬防线 — --confirmed-by 必填 + 审计链 + file_token 通道校验."""

    def test_missing_confirmed_by_exits_2(self, tmp_path, monkeypatch):
        """TC-GATE-101: 省略 --confirmed-by → exit 2，不写 confirmed_at."""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = argparse.Namespace(
            command="gate", subcommand="approve", dry_run=False, verbose=0,
            name="2026-01-01-gate-test", gate=1,
        )  # 无 confirmed_by —— 绕过 argparse 直接构造 Namespace 的调用方同样被拒
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 2

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert "confirmed_at" not in data["phases"]["understand"]

    def test_dialog_channel_writes_audit_chain(self, tmp_path, monkeypatch, capsys):
        """TC-GATE-102: dialog 通道确认 → confirmed_by/confirmed_evidence/confirmed_at 落库."""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1,
                          confirmed_by="dialog", evidence="用户：确认")
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "Gate 1 confirmed" in captured.out

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        u = data["phases"]["understand"]
        assert u["confirmed_by"] == "dialog"
        assert u["confirmed_evidence"] == "用户：确认"
        assert u["confirmed_at"] is not None

    def test_confirmed_actor_lands(self, tmp_path, monkeypatch, capsys):
        """TC-GATE-103: confirmed_actor 落库，默认 ai；env 覆盖为 user."""
        change_dir = _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1, confirmed_by="dialog")
        cmd_gate(args)
        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["understand"]["confirmed_actor"] == "ai"

        # env 强制 user 发起者
        change_dir2 = _setup_gate_project(tmp_path / "proj2")
        monkeypatch.chdir(tmp_path / "proj2")
        monkeypatch.setenv("STDD_CONFIRM_ACTOR", "user")
        args2 = _make_args("approve", name="2026-01-01-gate-test", gate=1, confirmed_by="dialog")
        cmd_gate(args2)
        data2 = yaml.safe_load((change_dir2 / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data2["phases"]["understand"]["confirmed_actor"] == "user"

    def test_file_token_without_token_rejected(self, tmp_path, monkeypatch):
        """TC-GATE-104: --confirmed-by file_token 但无 GATE token → exit 2."""
        _setup_gate_project(tmp_path, gates_confirmed=[1])
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2,
                          confirmed_by="file_token")
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 2

    def test_file_token_path_checks_gate_order(self, tmp_path, monkeypatch):
        """TC-GATE-105: file_token 通道也过 _check_gate_order — Gate 1 未确认时 Gate 2 拒."""
        change_dir = _setup_gate_project(tmp_path)  # 无任何 gate 确认
        (change_dir / "GATE2_APPROVED").touch()
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2,
                          confirmed_by="file_token")
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 1

    def test_file_token_with_token_confirmed(self, tmp_path, monkeypatch, capsys):
        """TC-GATE-106: --confirmed-by file_token + token 存在 → confirmed_by=file_token 落库."""
        change_dir = _setup_gate_project(tmp_path, gates_confirmed=[1])
        (change_dir / "GATE2_APPROVED").touch()
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=2,
                          confirmed_by="file_token")
        cmd_gate(args)
        captured = capsys.readouterr()
        assert "confirmed_by=file_token" in captured.out

        data = yaml.safe_load((change_dir / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["spec"]["confirmed_by"] == "file_token"

    def test_invalid_confirmed_by_rejected(self, tmp_path, monkeypatch):
        """TC-GATE-107: 非法 --confirmed-by 值 → exit 2."""
        _setup_gate_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.gate import cmd_gate

        args = _make_args("approve", name="2026-01-01-gate-test", gate=1,
                          confirmed_by="hacker")
        with pytest.raises(SystemExit) as exc_info:
            cmd_gate(args)
        assert exc_info.value.code == 2
