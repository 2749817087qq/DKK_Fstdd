"""测试 cmd_init 命令。"""
import argparse
import pytest
from pathlib import Path

from fstdd.cli.commands.init import cmd_init


def test_init_normal(temp_project: Path, monkeypatch):
    """正常初始化创建目录结构。"""
    monkeypatch.chdir(temp_project)
    args = argparse.Namespace(force=False, dry_run=False, verbose=0, prefix=None)
    cmd_init(args)
    assert (temp_project / ".fstdd").exists()
    assert (temp_project / ".fstdd" / "changes").exists()
    assert (temp_project / ".fstdd" / "specs").exists()
    assert (temp_project / ".fstdd" / "archive").exists()
    assert (temp_project / ".fstdd" / "skills").exists()
    assert (temp_project / ".fstdd" / "config.d").exists()


def test_init_force_overwrite(temp_project: Path, monkeypatch):
    """--force 覆盖已存在文件。"""
    monkeypatch.chdir(temp_project)
    args = argparse.Namespace(force=True, dry_run=False, verbose=0, prefix=None)
    cmd_init(args)
    # 再次执行不抛异常
    cmd_init(args)
    assert (temp_project / ".fstdd").exists()


def test_init_dry_run_creates_nothing(tmp_path: Path, monkeypatch, capsys):
    """--dry-run 不创建任何文件（含 .fstdd/ 与 version.yaml）。

    原实现是 `try: cmd_init(args) / except Exception: pass` —— 零断言，
    dry-run 崩掉与正常返回在测试里同形（假测试，已修）。
    """
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(force=False, dry_run=True, verbose=0, prefix=None)
    cmd_init(args)

    assert list(tmp_path.iterdir()) == [], (
        f"dry-run 落盘了: {[p.name for p in tmp_path.iterdir()]}"
    )
    out = capsys.readouterr().out
    assert "[DRY-RUN]" in out
    assert "文件系统未发生变化" in out
