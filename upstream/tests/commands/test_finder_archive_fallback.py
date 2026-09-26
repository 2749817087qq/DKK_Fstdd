"""TC-FAF-007 ~ TC-FAF-013：归档后四条命令仍可用 + 三条零漂移守卫。

change: 2026-09-26-finder-archive-fallback
spec:   specs/change-dir-resolution/spec.md（REQ-002 SC-007~010 / REQ-003 SC-011~013）
design: design.md（include_archive 仅关键字、默认 False；changes/ 优先；不改 rollback.py）

修复前实测（observed_base_git_sha=f3b2713）：validate / status / canon verify /
structure merge 对已归档 change 全部 rc=1。
"""
import argparse
import shutil

import pytest
import yaml
from pathlib import Path


CHANGE = "2026-01-01-archived-target"


def _make_change(base: Path, name: str = CHANGE, status: str = "active") -> Path:
    """在 base 下建一个「已完成」的 change 骨架（archive 要求 build=completed）。"""
    d = base / name
    (d / "canonical" / "proposals").mkdir(parents=True, exist_ok=True)
    (d / ".fstdd.yaml").write_text(
        yaml.dump(
            {
                "change_id": name,
                "status": status,
                "current_phase": "deliver",
                "phases": {
                    p: {"status": "completed"}
                    for p in ("understand", "spec", "build", "deliver")
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return d


def _archive_it(project_root: Path, name: str = CHANGE) -> Path:
    """把 changes/<name> 整体移到 archive/<name>（等价 stdd archive 的落点）。"""
    src = project_root / ".fstdd" / "changes" / name
    dst = project_root / ".fstdd" / "archive" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


# ---------------------------------------------------------------------------
# REQ-002：归档后四条命令不再因「找不到 change」失败
# ---------------------------------------------------------------------------
def test_faf_007_validate_works_on_archived_change(temp_project: Path, monkeypatch, capsys):
    """TC-FAF-007 / SC-007：归档后 validate 正常完成（修复前 rc=1）。"""
    from fstdd.cli.commands.validate import cmd_validate

    d = _make_change(temp_project / ".fstdd" / "changes")
    (d / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
    (d / "design.md").write_text("# Design\n", encoding="utf-8")
    (d / "test-plan.md").write_text("# Test Plan\n", encoding="utf-8")
    _archive_it(temp_project)
    monkeypatch.chdir(temp_project)

    # 不抛 SystemExit 即 rc=0
    cmd_validate(argparse.Namespace(name=CHANGE, dry_run=False, verbose=0))

    out = capsys.readouterr().out
    assert "找不到 change" not in out


def test_faf_008_status_works_on_archived_change(temp_project: Path, monkeypatch, capsys):
    """TC-FAF-008 / SC-008：归档后 status 正常输出（修复前 rc=1）。"""
    from fstdd.cli.commands.status import cmd_status

    _make_change(temp_project / ".fstdd" / "changes", status="archived")
    _archive_it(temp_project)
    monkeypatch.chdir(temp_project)

    cmd_status(argparse.Namespace(name=CHANGE, dry_run=False, verbose=0))

    out = capsys.readouterr().out
    assert CHANGE in out
    assert "找不到 change" not in out


def test_faf_009_canon_verify_works_on_archived_change(temp_project: Path, monkeypatch, capsys):
    """TC-FAF-009 / SC-009：归档后 canon verify 输出 2/2 通过。

    本 case 是「只改 finder 不够」的直接证据 —— canon._get_canon_dir
    原先纯路径拼接、根本不走 finder。
    """
    from fstdd.cli.commands.canon import cmd_canon_verify
    from fstdd.cli.timeutil import content_hash

    d = _make_change(temp_project / ".fstdd" / "changes")
    yaml_file = d / "canonical" / "proposals" / f"{CHANGE}.yaml"
    yaml_file.write_text(
        yaml.dump({"meta": {"change_id": CHANGE, "title": "归档目标"}}, allow_unicode=True),
        encoding="utf-8",
    )
    # Human View 需带与 YAML 一致的 source_hash（否则 DC-HASH 判不一致）
    (d / "proposal.md").write_text(
        f"<!-- source_hash: {content_hash(yaml_file.read_bytes())} -->\n# 归档目标\n",
        encoding="utf-8",
    )
    _archive_it(temp_project)
    monkeypatch.chdir(temp_project)

    cmd_canon_verify(argparse.Namespace(change_name=CHANGE))

    out = capsys.readouterr().out
    assert "2/2" in out, f"应输出 DC-HASH + DC-FIELD 两项通过，实际: {out!r}"
    assert "not found" not in out


def test_faf_010_structure_merge_reads_archived_delta(temp_project: Path, monkeypatch, capsys):
    """TC-FAF-010 / SC-010：归档后 structure merge 读到 delta（修复前 rc=1）。"""
    from fstdd.cli.commands.structure import cmd_structure_merge

    d = _make_change(temp_project / ".fstdd" / "changes")
    (d / "code-structure-delta.md").write_text(
        "# Code Structure Delta\n\n## 变更文件\n\n- `upstream/x.py`\n", encoding="utf-8"
    )
    _archive_it(temp_project)
    monkeypatch.chdir(temp_project)

    cmd_structure_merge(argparse.Namespace(target=CHANGE))

    out = capsys.readouterr().out
    assert "Delta not found" not in out
    assert (
        temp_project / ".fstdd" / "code-structure" / "deltas" / f"{CHANGE}.md"
    ).exists(), "delta 应被复制进 code-structure/deltas/"


# ---------------------------------------------------------------------------
# REQ-003：归档相关既有行为零漂移（反例守卫）
# ---------------------------------------------------------------------------
def test_faf_011_archive_never_resolves_archive_dir(temp_project: Path, monkeypatch):
    """TC-FAF-011 / SC-011：二次 archive 必须非 0，且 archive/ 原地不动。

    若 find_change_dir 默认值被改成 True，archive 会解析到 archive/<name>
    并**把它自己再移动一次** ⇒ 目录丢失。本 case 是核心反例。
    """
    from fstdd.cli.commands.archive import cmd_archive

    _make_change(temp_project / ".fstdd" / "changes")
    archived = _archive_it(temp_project)
    before_mtime = archived.stat().st_mtime
    before_inode = archived.stat().st_ino
    monkeypatch.chdir(temp_project)

    with pytest.raises(SystemExit):
        cmd_archive(
            argparse.Namespace(
                name=CHANGE, yes=True, skip_specs=False, dry_run=False, verbose=0
            )
        )

    assert archived.exists(), "archive/ 不得被自我移动（数据丢失）"
    st = archived.stat()
    assert st.st_mtime == before_mtime
    assert st.st_ino == before_inode, "目录 inode 变化 ⇒ 已被移动/重建"


def test_faf_012_rollback_restores_from_archive(temp_project: Path, monkeypatch):
    """TC-FAF-012 / SC-012：rollback 既有 archive 恢复逻辑不回归。

    本 change **不修改** rollback.py（它有独立的 archive/ + archive/aborted/ 搜索）。
    """
    from fstdd.cli.commands.rollback import cmd_rollback

    _make_change(temp_project / ".fstdd" / "changes", status="archived")
    archived = _archive_it(temp_project)
    monkeypatch.chdir(temp_project)

    cmd_rollback(argparse.Namespace(name=CHANGE, dry_run=False, verbose=0))

    restored = temp_project / ".fstdd" / "changes" / CHANGE
    assert restored.exists(), "rollback 应把归档件恢复到 changes/"
    assert not archived.exists()


def test_faf_013_archive_unarchived_change_still_works(temp_project: Path, monkeypatch):
    """TC-FAF-013 / SC-013：未归档 change 正常归档（既有行为不回归）。"""
    from fstdd.cli.commands.archive import cmd_archive

    _make_change(temp_project / ".fstdd" / "changes")
    monkeypatch.chdir(temp_project)

    cmd_archive(
        argparse.Namespace(name=CHANGE, yes=True, skip_specs=False, dry_run=False, verbose=0)
    )

    dst = temp_project / ".fstdd" / "archive" / CHANGE
    assert dst.exists()
    assert not (temp_project / ".fstdd" / "changes" / CHANGE).exists()
    state = yaml.safe_load((dst / ".fstdd.yaml").read_text(encoding="utf-8"))
    assert state["status"] == "archived"
