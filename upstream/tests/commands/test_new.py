"""测试 cmd_new 命令。"""
import argparse
import pytest
import sys
from pathlib import Path

from fstdd.cli.commands.new import cmd_new


def test_new_valid_name(temp_project: Path, monkeypatch):
    """有效的 change 名称创建成功。"""
    monkeypatch.chdir(temp_project)
    # 需要 templates 目录
    (temp_project / ".fstdd" / "templates").mkdir(parents=True, exist_ok=True)
    for t in ["proposal", "design", "test-plan"]:
        (temp_project / ".fstdd" / "templates" / f"{t}.md").write_text(f"# {t}", encoding="utf-8")

    args = argparse.Namespace(name="my-feature", dry_run=False, verbose=0)
    cmd_new(args)

    changes = list((temp_project / ".fstdd" / "changes").iterdir())
    assert len(changes) == 1
    assert changes[0].name.endswith("my-feature")
    assert (changes[0] / ".fstdd.yaml").exists()
    # V3.0.5 (YAML-first): proposal.md 不再复制 — Canonical YAML 是源头，MD 由 Gate 1 生成
    assert not (changes[0] / "proposal.md").exists()
    canon_yaml = changes[0] / "canonical" / "proposals" / f"{changes[0].name}.yaml"
    assert canon_yaml.exists(), f"Expected Canonical YAML at {canon_yaml}"
    assert (changes[0] / "design.md").exists()   # 非 YAML 模板照旧复制
    assert (changes[0] / "test-plan.md").exists()


def test_new_invalid_name_special_chars(temp_project: Path, monkeypatch):
    """包含特殊字符的名称被拒绝。"""
    monkeypatch.chdir(temp_project)
    args = argparse.Namespace(name="bad name!", dry_run=False, verbose=0)
    with pytest.raises(SystemExit):
        cmd_new(args)


def test_new_duplicate_name(sample_change: Path, monkeypatch):
    """重复名称被拒绝。"""
    monkeypatch.chdir(sample_change.parent.parent.parent)
    name_part = sample_change.name.split("-", 3)[-1]
    args = argparse.Namespace(name=name_part, dry_run=False, verbose=0)
    with pytest.raises(SystemExit):
        cmd_new(args)


def test_new_dry_run(temp_project: Path, monkeypatch, capsys):
    """--dry-run 预览但不创建目录。"""
    monkeypatch.chdir(temp_project)
    args = argparse.Namespace(name="test-dry", dry_run=True, verbose=0)
    cmd_new(args)
    captured = capsys.readouterr()
    assert "[DRY-RUN]" in captured.out
    # 未创建 change 目录
    changes = list((temp_project / ".fstdd" / "changes").iterdir())
    assert len(changes) == 0


def test_new_version_field(temp_project: Path, monkeypatch):
    """cmd_new 生成的 .fstdd.yaml 使用 4-phase schema version 3.0（V3.0.5）。"""
    monkeypatch.chdir(temp_project)
    (temp_project / ".fstdd" / "templates").mkdir(parents=True, exist_ok=True)
    for t in ["proposal", "design", "test-plan"]:
        (temp_project / ".fstdd" / "templates" / f"{t}.md").write_text(f"# {t}", encoding="utf-8")

    args = argparse.Namespace(name="ver-check", dry_run=False, verbose=0)
    cmd_new(args)

    import yaml
    changes = list((temp_project / ".fstdd" / "changes").iterdir())
    assert len(changes) == 1
    state_file = changes[0] / ".fstdd.yaml"
    with open(state_file, "r", encoding="utf-8") as f:
        state = yaml.safe_load(f)
    assert state["version"] == "3.0"
    # 4-phase schema：不含 slice/verify 键
    assert set(state["phases"].keys()) == {"understand", "spec", "build", "deliver"}


# ---------------------------------------------------------------------------
# TC-NEW-001~004: 日期幂等 + canonical scaffold 出声
# 2026-09-25 由 D 哥实测发现两个真实缺陷：
#   ① `stdd new` 无条件 prepend 今日日期 ⇒ 已含日期的名字产生双日期脚手架
#   ② `except SystemExit: pass` 静默吞掉 canonical scaffold 失败
# ---------------------------------------------------------------------------

def _setup_templates(temp_project: Path) -> None:
    """cmd_new 需要模板目录可读（否则 canonical 骨架可能缺）。"""
    (temp_project / ".fstdd" / "templates").mkdir(parents=True, exist_ok=True)
    for t in ["proposal", "design", "test-plan"]:
        (temp_project / ".fstdd" / "templates" / f"{t}.md").write_text(f"# {t}", encoding="utf-8")


def _only_change_dir(temp_project: Path) -> Path:
    dirs = list((temp_project / ".fstdd" / "changes").iterdir())
    assert len(dirs) == 1, f"期望恰好 1 个 change 目录，实际 {len(dirs)}"
    return dirs[0]


def test_new_already_dated_name_no_double_date(temp_project: Path, monkeypatch):
    """TC-NEW-001: 已含 YYYY-MM-DD- 前缀 → **不再** prepend（缺陷复现用例）。"""
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="2026-09-25-fix-x", dry_run=False, verbose=0))

    d = _only_change_dir(temp_project)
    assert d.name == "2026-09-25-fix-x", f"出现双日期脚手架: {d.name}"
    assert not d.name.startswith("2026-09-25-2026-09-25"), d.name


def test_new_short_name_prepends_date_exactly_once(temp_project: Path, monkeypatch):
    """TC-NEW-002: 短名 → prepend 恰好一次。"""
    import re
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="fix-login-bug", dry_run=False, verbose=0))

    d = _only_change_dir(temp_project)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", d.name)
    assert m, f"格式应为 <日期>-<名字>: {d.name}"
    assert m.group(2) == "fix-login-bug", d.name
    # 目录名里只出现一次日期前缀
    assert d.name.count(m.group(1)) == 1, d.name


def test_new_date_in_middle_still_prepends(temp_project: Path, monkeypatch):
    """TC-NEW-003: 日期只在名字中段（非前缀）→ 仍 prepend。"""
    import datetime
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="fix-2026-09-25-bug", dry_run=False, verbose=0))

    d = _only_change_dir(temp_project)
    assert d.name.startswith(datetime.date.today().isoformat() + "-"), d.name
    assert d.name.endswith("-fix-2026-09-25-bug"), d.name


def test_canon_init_system_exit_is_announced(temp_project: Path, monkeypatch, capsys):
    """TC-NEW-004a: cmd_canon_init 抛 SystemExit → 必须出声，而非静默 pass。"""
    import fstdd.cli.commands.canon as canon_mod
    _setup_templates(temp_project)
    monkeypatch.setattr(
        canon_mod, "cmd_canon_init",
        lambda args: (_ for _ in ()).throw(SystemExit(1)),
    )
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="fix-canonical", dry_run=False, verbose=0))

    out = capsys.readouterr().out
    assert "Canonical" in out, f"未出声告警: {out!r}"
    assert "stdd canon init --change" in out, f"未给补救命令: {out!r}"


def test_terminal_state_check_flags_missing_canonical(temp_project: Path, monkeypatch, capsys):
    """TC-NEW-004b: 终态校验 —— canon_init 正常退出但未写文件，仍必须告警。

    「用端状态验证，不只看命令回显」的锚点：只看 return code 会漏掉
    「正常退出但漏写文件」这一整类半完成态。
    """
    import fstdd.cli.commands.canon as canon_mod
    _setup_templates(temp_project)
    monkeypatch.setattr(canon_mod, "cmd_canon_init", lambda args: None)
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="fix-canonical", dry_run=False, verbose=0))

    d = _only_change_dir(temp_project)
    assert not (d / "canonical").exists(), "测试前提：canonical/ 确实未生成"
    out = capsys.readouterr().out
    assert "终态校验失败" in out, f"终态校验未出声: {out!r}"
    assert "缺失" in out, out


def test_terminal_state_ok_when_canonical_present(temp_project: Path, monkeypatch, capsys):
    """TC-NEW-004c: canonical/ 在盘上 → 终态标就绪，无误报。"""
    import fstdd.cli.commands.canon as canon_mod

    def _fake_canon_init(args):
        d = temp_project / ".fstdd" / "changes" / args.change
        (d / "canonical").mkdir(parents=True, exist_ok=True)

    _setup_templates(temp_project)
    monkeypatch.setattr(canon_mod, "cmd_canon_init", _fake_canon_init)
    monkeypatch.chdir(temp_project)
    cmd_new(argparse.Namespace(name="fix-canonical", dry_run=False, verbose=0))

    d = _only_change_dir(temp_project)
    assert (d / "canonical").exists()
    out = capsys.readouterr().out
    assert "终态校验失败" not in out, f"误报: {out!r}"
    assert "就绪" in out, out
