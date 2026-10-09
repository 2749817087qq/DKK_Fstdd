"""fstdd state — Read/write resume context fields in .fstdd.yaml (V2.5)."""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from ..timeutil import utc_now_iso
from ..finder import find_change_dir, require_active_change_dir
from ._dryrun import dry_run_preview

import yaml


RESUME_FIELDS = ["resume_context", "active_slice", "last_action", "last_modified",
                  "active_phase", "phase_context_file"]


def _find_change_dir(name: str | None, project_root: Path) -> Path | None:
    """**读路径**解析（2026-10-07 收口）：统一入口 + 归档回退。

    此前只拼 `changes/<name>`，对已归档 change 会返回不存在的路径，
    最终报出 `.fstdd.yaml not found in <绝对路径 changes/<name>>`
    —— 把「本命令去错地方找」这件事直接暴露给了使用者。
    """
    return find_change_dir(name, project_root, include_archive=True)


def read_resume_context(change_dir: Path) -> dict:
    """Read resume fields from .fstdd.yaml with backward compatibility.

    Returns dict with resume_context, active_slice, last_action, last_modified.
    Values are None for missing fields (V2.4 compatibility).
    """
    state_file = change_dir / ".fstdd.yaml"
    if not state_file.exists():
        return {k: None for k in RESUME_FIELDS}

    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    result = {}
    for k in RESUME_FIELDS:
        result[k] = data.get(k)
    return result


def write_resume_context(change_dir: Path, **kwargs) -> None:
    """Write resume fields to .fstdd.yaml. Only writes specified keys.

    Usage: write_resume_context(change_dir, resume_context="...", active_slice=2)
    """
    state_file = change_dir / ".fstdd.yaml"
    if not state_file.exists():
        print(f"  .fstdd.yaml not found in {change_dir}")
        return

    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    for k in RESUME_FIELDS:
        if k in kwargs:
            data[k] = kwargs[k]
    data["last_modified"] = utc_now_iso(timespec="seconds")

    state_file.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8"
    )


def cmd_state(args: argparse.Namespace) -> None:
    """CLI entry: fstdd state <change-name> [--resume] [--set KEY=VALUE]."""
    project_root = Path.cwd()
    # 读/写分层（2026-10-07 / SC-102 vs SC-106）：只有 `--set` 是写操作，
    # 归档 change 上的写必须被统一写入口拒绝；查看与 `--resume` 是读，放行归档。
    if getattr(args, "set", None):
        change_dir = require_active_change_dir(getattr(args, "name", None), project_root)
    else:
        change_dir = _find_change_dir(getattr(args, "name", None), project_root)
        if change_dir is None:
            print("  No change found.")
            sys.exit(1)

    if getattr(args, "resume", False):
        ctx = read_resume_context(change_dir)
        state_file = change_dir / ".fstdd.yaml"
        data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}

        # --compact: single-line machine-readable output, cross-platform
        if getattr(args, "compact", False):
            phase = data.get("active_phase", "?")
            active_slice = data.get("active_slice", "N/A")
            last_action = data.get("last_action", "unknown")
            freshness = data.get("state_freshness", {})
            saved_head = freshness.get("git_head", "")

            import subprocess
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=5,
                )
                current_head = result.stdout.strip()
            except Exception:
                current_head = ""

            if saved_head and current_head and saved_head != current_head:
                fresh = "STALE"
            else:
                fresh = "FRESH"

            print(f"change={change_dir.name} phase={phase} slice={active_slice} "
                  f"last=\"{last_action}\" freshness={fresh}")
            return

        print(f"\n  ══════════════════════════════════════")
        print(f"    STDD Resume Context")
        print(f"  ══════════════════════════════════════")
        print(f"\n  Change: {change_dir.name}")
        print(f"  Phase: {data.get('active_phase', '?')}")
        print(f"  Slice: {data.get('active_slice', 'N/A')}")
        print(f"  Last Action: {data.get('last_action', 'unknown')}")
        print(f"  Last Modified: {data.get('last_modified', 'unknown')}")

        # Phase context file pointer
        pc_file = data.get("phase_context_file", "")
        if pc_file:
            print(f"\n  📄 Phase Context: {pc_file}")
            print(f"  💡 建议: 先读取 phase-context.md 了解完整背景")

        # State freshness check (V2.7)
        freshness = data.get("state_freshness", {})
        if freshness:
            verified_at = freshness.get("verified_at", "unknown")
            saved_head = freshness.get("git_head", "")

            # Check git HEAD
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, cwd=project_root
                )
                current_head = result.stdout.strip()
            except Exception:
                current_head = ""

            if saved_head and current_head and saved_head != current_head:
                print(f"\n  🟡 State Freshness: STALE")
                print(f"     Git HEAD 已变更: saved={saved_head}, current={current_head}")
                print(f"     建议: 检查变更是否影响当前 change 的产出物")
            else:
                print(f"\n  🟢 State Freshness: FRESH — {verified_at}")

        print()
        return

    if getattr(args, "set", None) and dry_run_preview(args, "state --set"):
        return

    set_kv = getattr(args, "set", None)
    if set_kv:
        if "=" not in set_kv:
            print("  Usage: --set KEY=VALUE")
            sys.exit(1)
        key, value = set_kv.split("=", 1)
        if key not in RESUME_FIELDS:
            print(f"  Unknown field: {key}. Valid: {', '.join(RESUME_FIELDS)}")
            sys.exit(1)
        write_resume_context(change_dir, **{key: value})
        print(f"  Set {key}={value} for {change_dir.name}")
        return

    # Default: show full state
    state_file = change_dir / ".fstdd.yaml"
    if not state_file.exists():
        print(f"  .fstdd.yaml not found in {change_dir}")
        sys.exit(1)
    data = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    print(f"  State for {change_dir.name}:")
    print(f"    current_phase: {data.get('current_phase', 'unknown')}")
    print(f"    status: {data.get('status', 'unknown')}")
    ctx = {k: data.get(k) for k in RESUME_FIELDS}
    print(f"    resume_context: {ctx.get('resume_context')}")
    print(f"    active_slice: {ctx.get('active_slice')}")
    print(f"    last_action: {ctx.get('last_action')}")
    print(f"    last_modified: {ctx.get('last_modified')}")
