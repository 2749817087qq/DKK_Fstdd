"""Tests for stdd bootcamp CLI."""
import pytest
from pathlib import Path

def test_bootcamp_status(temp_project, monkeypatch, capsys):
    monkeypatch.chdir(temp_project)
    from stdd.cli.commands.bootcamp import cmd_bootcamp
    import argparse
    ns = argparse.Namespace(subcommand="status", level=None, module=None, verbose=0)
    cmd_bootcamp(ns)
    out = capsys.readouterr().out
    assert "Bootcamp" in out or "训练" in out or "bootcamp" in out.lower()

def test_bootcamp_start_shows_level(temp_project, monkeypatch, capsys):
    monkeypatch.chdir(temp_project)
    from stdd.cli.commands.bootcamp import cmd_bootcamp
    import argparse
    ns = argparse.Namespace(subcommand="start", level=None, module=None, verbose=0)
    cmd_bootcamp(ns)
    out = capsys.readouterr().out
    assert "第 1 关" in out or "level" in out.lower()

def test_bootcamp_retry_invalid(temp_project, monkeypatch, capsys):
    monkeypatch.chdir(temp_project)
    from stdd.cli.commands.bootcamp import cmd_bootcamp
    import argparse
    ns = argparse.Namespace(subcommand="retry", level=99, module=None, verbose=0)
    import sys
    try:
        cmd_bootcamp(ns)
    except SystemExit:
        pass

def test_bootcamp_grade_with_work(temp_project, monkeypatch, capsys):
    """TC: grade finds work files by name (not full path)."""
    monkeypatch.chdir(temp_project)
    import yaml
    # Create bootcamp structure with answer and work
    bd = temp_project / ".stdd" / "changes" / "_bootcamp" / "level_1"
    (bd / "answer").mkdir(parents=True)
    (bd / "work" / ".stdd" / "changes" / "fix-typo").mkdir(parents=True)
    # Answer: .stdd.yaml at answer root
    (bd / "answer" / ".stdd.yaml").write_text(yaml.dump({"change_id": "fix-typo"}))
    # Work: .stdd.yaml nested under .stdd/changes/ (mimics real CLI output)
    (bd / "work" / ".stdd" / "changes" / "fix-typo" / ".stdd.yaml").write_text(yaml.dump({"change_id": "fix-typo"}))
    from stdd.cli.commands.bootcamp import cmd_bootcamp
    import argparse
    ns = argparse.Namespace(subcommand="grade", level=1, module=None, verbose=0)
    cmd_bootcamp(ns)
    out = capsys.readouterr().out
    assert "通过" in out or "10" in out
