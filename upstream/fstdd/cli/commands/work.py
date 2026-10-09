"""STDD work CLI — track related work during a change (V2.9.4).

Related work captures bugfixes, tests, experiences, and other
incidental work produced during a change's lifecycle.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from ..timeutil import utc_now_iso
from ..finder import find_change_dir, require_active_change_dir
from ._dryrun import dry_run_preview
import yaml


def _find_batch_child(project_root: Path) -> Path:
    """V3.0.5 批级管线兜底：open batch 下最近修改的子 change（统一入口覆盖不到）。"""
    try:
        from .batch import _find_open_batch
    except Exception:
        return None
    batch_dir = _find_open_batch(project_root)
    if not batch_dir:
        return None
    children_dir = batch_dir / "changes"
    if not children_dir.is_dir():
        return None
    children = sorted(
        [d for d in children_dir.iterdir() if d.is_dir() and (d / ".fstdd.yaml").exists()],
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    return children[0] if children else None


def _find_change(project_root: Path, name: str = None) -> Path:
    """**读路径**解析：统一入口（含归档回退）+ 批级管线兜底。

    2026-10-07 收口：主路径改走 `finder.find_change_dir(..., include_archive=True)`
    —— 此前只扫 `.fstdd/changes/`，`fstdd work list <已归档 change>` 会报
    `.fstdd.yaml not found in <name>`。
    """
    hit = find_change_dir(name, project_root, include_archive=True)
    if hit is not None:
        return hit
    if name:
        return None
    return _find_batch_child(project_root)


def _resolve_write_change(project_root: Path, name: str = None) -> Path:
    """**写路径**解析：统一写入口（归档拒绝）+ 批级子 change 放行。"""
    hit = find_change_dir(name, project_root, include_archive=True)
    if hit is None and not name:
        child = _find_batch_child(project_root)
        if child is not None:
            return child
    return require_active_change_dir(name, project_root)


def cmd_work(args: argparse.Namespace) -> None:
    """Track related work for a change."""
    project_root = Path.cwd()
    action = getattr(args, "work_action", "list")
    change_name = getattr(args, "name", None)

    # 读/写分层（2026-10-07 / SC-103 vs SC-106）：`list` 是读（放行归档），
    # `add` 是写（归档 change 上由统一写入口拒绝）。
    if action == "add":
        change_dir = _resolve_write_change(project_root, change_name)
    else:
        change_dir = _find_change(project_root, change_name)
        if change_dir is None:
            print("  No change found.")
            sys.exit(1)

    stdd_yaml = change_dir / ".fstdd.yaml"
    if not stdd_yaml.exists():
        print(f"  .fstdd.yaml not found in {change_dir.name}")
        sys.exit(1)

    data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
    works = data.get("related_work", [])

    if action == "add" and dry_run_preview(args, "work add"):
        return

    if action == "add":
        work_type = getattr(args, "work_type", "other") or "other"
        description = getattr(args, "description", "")
        if not description:
            print("  Usage: fstdd work add --type bugfix \"描述\"")
            sys.exit(1)
        commit = getattr(args, "commit_hash", "") or ""

        works.append({
            "type": work_type,
            "description": description,
            "commit": commit,
            "added_at": utc_now_iso(),
        })
        data["related_work"] = works
        stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        print(f"  ✅ [{len(works)}] {work_type}: {description}")
        return

    # list
    if works:
        print(f"  Related work ({len(works)}):")
        for i, w in enumerate(works, 1):
            commit_str = f" ({w.get('commit', '')})" if w.get('commit') else ""
            print(f"    {i}. [{w.get('type', '?')}] {w.get('description', '?')}{commit_str}")
    else:
        print(f"  暂无关联工作记录。")
        print(f"  用 'fstdd work add --type bugfix \"描述\"' 记录附带工作。")
