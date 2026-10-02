"""V3.0.5 batch pipeline (mini-STDD) tests:
open → proposal → gate1 → gate2 → child → build evidence → deliver → archive
"""
import argparse
import yaml
from pathlib import Path


def _make_args(action="status", description="", strategy="monthly", force=False,
               gate=None, child_action=None, name=None, confirmed_by="dialog", evidence=""):
    return argparse.Namespace(
        command="batch", action=action, description=description,
        strategy=strategy, force=force, dry_run=False, verbose=0,
        gate=gate, child_action=child_action, name=name,
        confirmed_by=confirmed_by, evidence=evidence,
    )


def _setup_env(tmp_path: Path):
    """Create minimal STDD project."""
    (tmp_path / ".fstdd" / "config.d").mkdir(parents=True)
    (tmp_path / ".fstdd" / "config.d" / "lite.yaml").write_text(
        yaml.dump({"batch": {"strategy": "monthly", "max_items": 20, "auto_close": True}},
                  allow_unicode=True),
        encoding="utf-8",
    )
    (tmp_path / ".fstdd" / "config.d" / "project.yaml").write_text(
        yaml.dump({"project": {"name": "t", "language": "python"}, "enforce_stdd": True}),
        encoding="utf-8",
    )
    (tmp_path / ".fstdd" / "changes" / "_batch").mkdir(parents=True)
    (tmp_path / ".fstdd" / "templates").mkdir(parents=True)
    (tmp_path / ".fstdd" / "templates" / "design.md").write_text("# Design", encoding="utf-8")


class TestBatchPipeline:
    """批级 mini-STDD 管线端到端。"""

    def test_full_pipeline(self, tmp_path, monkeypatch, capsys):
        """open → proposal → gate1 → gate2 → child → build 证据 → deliver。"""
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.batch import cmd_batch, _find_open_batch

        # 1. open
        cmd_batch(_make_args("open", "批量修复UI bug"))
        batch = _find_open_batch(tmp_path)
        assert batch is not None
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["current_phase"] == "understand"
        assert set(data["phases"].keys()) == {"understand", "spec", "build", "deliver"}

        # 2. proposal
        cmd_batch(_make_args("proposal", "批量修复UI bug"))
        proposal_yaml = batch / "canonical" / "proposals" / f"{batch.name}.yaml"
        assert proposal_yaml.exists()
        assert (batch / "design.md").exists()

        # 3. gate 1 → auto proposal.md, phase → spec
        cmd_batch(_make_args("gate", gate=1))
        captured = capsys.readouterr()
        assert "Gate 1" in captured.out
        assert (batch / "proposal.md").exists()  # Gate 自动生成
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["current_phase"] == "spec"
        assert data["phases"]["understand"]["status"] == "completed"

        # 4. 写批级 spec YAML → gate 2 → phase → build
        specs_code = batch / "canonical" / "specs" / "code"
        specs_code.mkdir(parents=True)
        (specs_code / "rate-limit.yaml").write_text(yaml.dump({
            "meta": {"capability": "rate-limit", "change_id": batch.name,
                     "created": "now", "confidence": "high"},
            "requirements": [{
                "id": "REQ-001",
                "description": "限流",
                "scenarios": [{"id": "SC-001", "given": "g", "when": "w",
                               "then": "system SHALL return 429"}]
            }]
        }), encoding="utf-8")
        cmd_batch(_make_args("gate", gate=2))
        captured = capsys.readouterr()
        assert "Gate 2" in captured.out
        assert (batch / "specs" / "rate-limit" / "spec.md").exists()  # Gate 自动生成 spec.md
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["current_phase"] == "build"

        # 5. child add — 从 build 起步，继承批级 confirmed_at
        cmd_batch(_make_args("child", child_action="add", name="fix-fees", description="修复费用显示"))
        children = list((batch / "changes").iterdir())
        assert len(children) == 1
        child = children[0]
        cdata = yaml.safe_load((child / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert cdata["current_phase"] == "build"
        assert cdata["parent_batch"] == batch.name
        assert cdata["phases"]["understand"]["status"] == "completed"
        assert cdata["phases"]["spec"]["status"] == "completed"

        # 6. 子 change build 证据 + test-report.md
        cdata["phases"]["build"]["status"] = "completed"
        cdata["phases"]["build"]["slices_completed"] = {
            "1": {"status": "done", "tc_coverage": "5/5", "new_tests": 5,
                  "verified_at": "2026-08-17T10:00:00"}
        }
        (child / ".fstdd.yaml").write_text(
            yaml.dump(cdata, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        (child / "test-report.md").write_text("# 子change测试报告", encoding="utf-8")

        # 7. deliver — 聚合证据 → 批级 test-report.md
        cmd_batch(_make_args("deliver"))
        captured = capsys.readouterr()
        assert "批级交付完成" in captured.out
        report = batch / "test-report.md"
        assert report.exists()
        content = report.read_text(encoding="utf-8")
        assert "累计测试: 5" in content
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["current_phase"] == "deliver"

        # 8. close + archive
        cmd_batch(_make_args("close", force=True))
        cmd_batch(_make_args("archive"))
        assert (tmp_path / ".fstdd" / "archive" / batch.name).exists()

    def test_child_requires_gate2(self, tmp_path, monkeypatch, capsys):
        """Gate 2 未通过时 child add 被拒。"""
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.batch import cmd_batch
        cmd_batch(_make_args("open", "测试"))
        cmd_batch(_make_args("child", child_action="add", name="early", description="x"))
        captured = capsys.readouterr()
        assert "尚未通过 Gate 2" in captured.out

    def test_deliver_blocks_incomplete_child(self, tmp_path, monkeypatch, capsys):
        """子 change build 未完成时 deliver 拒绝。"""
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.batch import cmd_batch, _find_open_batch
        cmd_batch(_make_args("open", "测试"))
        batch = _find_open_batch(tmp_path)
        # 直接推进批级到 build
        from fstdd.cli.commands.gate import _confirm_gate
        _confirm_gate(1, batch, confirmed_by="test")
        _confirm_gate(2, batch, confirmed_by="test")
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        data["current_phase"] = "build"
        (batch / ".fstdd.yaml").write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

        cmd_batch(_make_args("child", child_action="add", name="wip", description="x"))
        # 子 change 无 test-report.md → deliver 拒绝
        cmd_batch(_make_args("deliver"))
        captured = capsys.readouterr()
        assert "尚未完成 build" in captured.out
        assert not (batch / "test-report.md").exists()


class TestBatchPipelineGuard:
    """V3.0.5: guard 批级分支 — build 放行，before gate1 只读。"""

    def test_guard_finds_child_in_build(self, tmp_path, monkeypatch):
        """批级 build 阶段：guard 返回活跃子 change（放行编辑）。"""
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.batch import cmd_batch, _find_open_batch
        from fstdd.cli.commands.guard import _find_active_change

        cmd_batch(_make_args("open", "测试"))
        batch = _find_open_batch(tmp_path)
        # 推进到 build 并创建子 change
        from fstdd.cli.commands.gate import _confirm_gate
        _confirm_gate(1, batch, confirmed_by="test")
        _confirm_gate(2, batch, confirmed_by="test")
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        data["current_phase"] = "build"
        (batch / ".fstdd.yaml").write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        cmd_batch(_make_args("child", child_action="add", name="c1", description="x"))

        child_dir, phase = _find_active_change(tmp_path)
        assert child_dir is not None
        assert child_dir.parent.parent.name == batch.name  # 在批级 _batch/<id>/changes/ 下
        assert phase == "build"


class TestBatchHardDefense:
    """V3.0.5: batch gate/deliver 收口 — 强制 confirmed_by 通道声明 + 审计继承."""

    def _open_and_gate1(self, tmp_path, monkeypatch):
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)
        from fstdd.cli.commands.batch import cmd_batch, _find_open_batch
        cmd_batch(_make_args("open", "批量修复UI bug"))
        cmd_batch(_make_args("proposal", "批量修复UI bug"))
        cmd_batch(_make_args("gate", gate=1))
        return _find_open_batch(tmp_path)

    def test_batch_gate_requires_channel(self, tmp_path, monkeypatch, capsys):
        """TC-BATCH-101: 批级 gate 无 confirmed_by → 拒绝，phase 不动."""
        batch = self._open_and_gate1(tmp_path, monkeypatch)
        from fstdd.cli.commands.batch import cmd_batch
        cmd_batch(_make_args("gate", gate=2, confirmed_by=""))
        captured = capsys.readouterr()
        assert "confirmed_by" in captured.out
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["current_phase"] == "spec"  # Gate 2 未推进

    def test_batch_gate_audit_field(self, tmp_path, monkeypatch):
        """TC-BATCH-102: 批级 gate 带 dialog → confirmed_by=dialog 落审计字段."""
        batch = self._open_and_gate1(tmp_path, monkeypatch)
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["understand"]["confirmed_by"] == "dialog"

    def test_batch_deliver_requires_channel(self, tmp_path, monkeypatch, capsys):
        """TC-BATCH-103: 批级 deliver 无 confirmed_by → 拒绝（Gate 3 不再静默自动确认）."""
        batch = self._open_and_gate1(tmp_path, monkeypatch)
        from fstdd.cli.commands.batch import cmd_batch
        cmd_batch(_make_args("gate", gate=2))
        cmd_batch(_make_args("child", child_action="add", name="c1", description="x"))
        # deliver 无通道声明 → 拒绝
        cmd_batch(_make_args("deliver", confirmed_by=""))
        captured = capsys.readouterr()
        assert "Gate 3 确认通道声明" in captured.out
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert "confirmed_at" not in data["phases"]["build"]

    def test_batch_deliver_gate3_audit_field(self, tmp_path, monkeypatch, capsys):
        """TC-BATCH-104: 批级 deliver 带 dialog → build.confirmed_by=dialog 落库."""
        batch = self._open_and_gate1(tmp_path, monkeypatch)
        from fstdd.cli.commands.batch import cmd_batch
        cmd_batch(_make_args("gate", gate=2))
        cmd_batch(_make_args("child", child_action="add", name="c1", description="x"))
        child = list((batch / "changes").iterdir())[0]
        cdata = yaml.safe_load((child / ".fstdd.yaml").read_text(encoding="utf-8"))
        cdata["phases"]["build"]["status"] = "completed"
        (child / ".fstdd.yaml").write_text(
            yaml.dump(cdata, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        (child / "test-report.md").write_text("# report", encoding="utf-8")

        cmd_batch(_make_args("deliver", confirmed_by="dialog", evidence="用户：确认"))
        captured = capsys.readouterr()
        assert "批级交付完成" in captured.out
        data = yaml.safe_load((batch / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert data["phases"]["build"]["confirmed_by"] == "dialog"
        assert data["phases"]["build"]["confirmed_evidence"] == "用户：确认"

    def test_child_inherits_batch_audit(self, tmp_path, monkeypatch):
        """TC-BATCH-105: 子 change 继承批级 confirmed_by/confirmed_actor."""
        batch = self._open_and_gate1(tmp_path, monkeypatch)
        from fstdd.cli.commands.batch import cmd_batch
        cmd_batch(_make_args("gate", gate=2))
        cmd_batch(_make_args("child", child_action="add", name="c1", description="x"))
        child = list((batch / "changes").iterdir())[0]
        cdata = yaml.safe_load((child / ".fstdd.yaml").read_text(encoding="utf-8"))
        assert cdata["phases"]["understand"]["confirmed_by"] == "dialog"
        assert cdata["phases"]["spec"]["confirmed_by"] == "dialog"
        assert cdata["phases"]["understand"]["confirmed_actor"] in ("ai", "user")

    def test_guard_no_child_before_gate1(self, tmp_path, monkeypatch):
        """批级 understand 阶段：guard 找不到子 change（需先推进 Gate）。"""
        _setup_env(tmp_path)
        monkeypatch.chdir(tmp_path)

        from fstdd.cli.commands.batch import cmd_batch
        from fstdd.cli.commands.guard import _find_active_change

        cmd_batch(_make_args("open", "测试"))
        child_dir, phase = _find_active_change(tmp_path)
        assert child_dir is None
