"""STDD work CLI — track related work during a change (V2.9.4).

Related work captures bugfixes, tests, experiences, and other
incidental work produced during a change's lifecycle.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from ..timeutil import utc_now_iso
import yaml


def _find_change(project_root: Path, name: str = None) -> Path:
    """Find change dir by name (most recent if None).

    V3.0.5: 顶层无活跃 change 时，回退查 open batch 的子 change（批级管线）。
    """
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.is_dir():
        return None
    if name:
        return changes_dir / name
    candidates = sorted(
        [d for d in changes_dir.iterdir() if d.is_dir() and d.name != "_batch" and (d / ".fstdd.yaml").exists()],
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    if candidates:
        return candidates[0]

    # V3.0.5: batch pipeline — 查 open batch 的子 change
    try:
        from .batch import _find_open_batch
    except Exception:
        return None
    batch_dir = _find_open_batch(project_root)
    if batch_dir:
        children_dir = batch_dir / "changes"
        if children_dir.is_dir():
            children = sorted(
                [d for d in children_dir.iterdir() if d.is_dir() and (d / ".fstdd.yaml").exists()],
                key=lambda d: d.stat().st_mtime, reverse=True,
            )
            if children:
                return children[0]
    return None


def cmd_work(args: argparse.Namespace) -> None:
    """Track related work for a change."""
    project_root = Path.cwd()
    action = getattr(args, "work_action", "list")
    change_name = getattr(args, "name", None)

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

    if action == "add":
        work_type = getattr(args, "work_type", "other") or "other"
        description = getattr(args, "description", "")
        if not description:
            print("  Usage: stdd work add --type bugfix \"描述\"")
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
        print(f"  用 'stdd work add --type bugfix \"描述\"' 记录附带工作。")
