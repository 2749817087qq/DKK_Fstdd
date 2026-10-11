"""Slice 2 契约测试：非交互自动沉淀 auto-deposit（C2 / REQ-002，TC-EAUT-001..004）。

对应 spec：
- SC-006 DELIVER 触发 auto-deposit，非交互抽取三类源并入库（不调用 input()）
- SC-007 FSTDD_NO_SHARE=1 → 跳过（本地 0 新增，无出站）
- SC-008 产物一律 lifecycle=discovered，STATUS 不为 shared
- SC-009 非 TTY / 管道运行不阻塞于标准输入
"""
import argparse
import builtins
from pathlib import Path

import yaml

CHANGE_NAME = "2026-10-11-fixture-change"

TEST_REPORT = """# Test Report

| 失败模式 | 状态 | 说明 |
|---------|------|------|
| contract_gap | FAIL | 契约断层：声明字段与实现不一致 |
"""

DESIGN_ADJUSTMENTS = """# 设计调整说明

## 调整汇总

| # | 调整类型 | 涉及文档 | 严重程度 | 调整阶段 | 影响 TC | 用户已知 |
|---|---------|---------|---------|---------|---------|---------|
| 1 | 技术方案变更 | design.md | Major | Phase 3 | TC-AAA-001 | 是 |

### 调整 1: 加密实现改为 openssl 子进程

- **原始设计**: cryptography 库
- **调整内容**: openssl CLI
- **调整原因**: 环境库不可用
"""

ADJUDICATION_LOG = "EXP-2026-0013\tKEEP_STDD_REPO\tversions=2\tfrom=['a', 'b']\n"


def _make_args(**kwargs):
    ns = argparse.Namespace(command="experience", subcommand="auto-deposit",
                            dry_run=False, verbose=0)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _setup(tmp_path: Path) -> Path:
    (tmp_path / ".fstdd" / "config.d").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".fstdd" / "experiences").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".fstdd" / "config.d" / "project.yaml").write_text(
        "project:\n  language: python\n", encoding="utf-8")
    ch = tmp_path / ".fstdd" / "changes" / CHANGE_NAME
    ch.mkdir(parents=True, exist_ok=True)
    (ch / "test-report.md").write_text(TEST_REPORT, encoding="utf-8")
    (ch / "design-adjustments.md").write_text(DESIGN_ADJUSTMENTS, encoding="utf-8")
    (ch / "adjudication-log.tsv").write_text(ADJUDICATION_LOG, encoding="utf-8")
    return ch


def _drafts(edir: Path):
    out = []
    for p in sorted(edir.glob("EXP-*.md")):
        text = p.read_text(encoding="utf-8")
        if text.startswith("---"):
            out.append(yaml.safe_load(text.split("---", 2)[1]) or {})
    return out


def _cmd():
    from fstdd.cli.commands.experience import _cmd_auto_deposit
    return _cmd_auto_deposit


def test_eaut001_auto_deposit_noninteractive(tmp_path, monkeypatch):
    """TC-EAUT-001 / SC-006：非交互抽取三类源并入库，不调用 input()。"""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"

    def _boom(*a, **k):
        raise AssertionError("auto-deposit 不得调用交互式 input()")

    monkeypatch.setattr(builtins, "input", _boom)
    monkeypatch.delenv("FSTDD_NO_SHARE", raising=False)

    _cmd()(_make_args(), edir)
    drafts = _drafts(edir)
    assert len(drafts) > 0
    blob = " ".join(str(d.get("pattern", "")) for d in drafts)
    assert "contract_gap" in blob or "契约断层" in blob


def test_eaut002_no_share_skips(tmp_path, monkeypatch, capsys):
    """TC-EAUT-002 / SC-007：FSTDD_NO_SHARE=1 → 跳过（本地 0 新增）。"""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    monkeypatch.setenv("FSTDD_NO_SHARE", "1")

    _cmd()(_make_args(), edir)
    out = capsys.readouterr().out.lower()
    assert list(edir.glob("EXP-*.md")) == []
    assert "skip" in out


def test_eaut003_all_discovered(tmp_path, monkeypatch):
    """TC-EAUT-003 / SC-008：产物一律 lifecycle=discovered，且不出现 shared。"""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    monkeypatch.delenv("FSTDD_NO_SHARE", raising=False)

    _cmd()(_make_args(), edir)
    drafts = _drafts(edir)
    assert drafts
    for d in drafts:
        assert d.get("lifecycle_state") == "discovered"
        assert str(d.get("status", "")).lower() != "shared"


def test_eaut004_non_tty_does_not_block(tmp_path, monkeypatch):
    """TC-EAUT-004 / SC-009：非 TTY 下不阻塞于标准输入。"""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    monkeypatch.delenv("FSTDD_NO_SHARE", raising=False)

    class _NoStdin:
        def read(self, *a, **k):
            raise OSError("stdin unavailable (non-TTY)")

        def readline(self, *a, **k):
            raise OSError("stdin unavailable (non-TTY)")

        def isatty(self):
            return False

    monkeypatch.setattr("sys.stdin", _NoStdin())
    _cmd()(_make_args(), edir)  # 不抛异常即视为不阻塞
    assert len(_drafts(edir)) > 0
