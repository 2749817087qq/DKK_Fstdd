import argparse
import sys
from pathlib import Path

import yaml


def cmd_status(args: argparse.Namespace) -> None:
    from ..finder import find_change_dir

    project_root = Path.cwd()

    change_dir = find_change_dir(args.name, project_root)
    if change_dir is None:
        print(f" 找不到 change: {args.name or '(无)'}")
        sys.exit(1)

    state_file = change_dir / ".stdd.yaml"
    if not state_file.exists():
        print(" 缺少 .stdd.yaml 状态文件")
        sys.exit(1)

    with open(state_file, "r", encoding="utf-8") as f:
        state = yaml.safe_load(f) or {}

    print(f"\n  Change: {state.get('change_id', change_dir.name)}")
    print(f"   状态: {state.get('status', 'unknown')}")
    print(f"   当前阶段: {state.get('current_phase', 'unknown')}")
    long_range = state.get("long_range", {})
    mode = long_range.get("mode", None)
    if mode == "full_auto":
        print(f"   执行模式:   全自动长程模式")
    elif mode == "normal" or mode is None:
        print(f"   执行模式:   普通交互模式（默认）")
    else:
        print(f"   执行模式: {mode}")
    print()

    phase_order = ["understand", "spec", "build", "deliver"]
    phase_names = {
        "understand": "Phase 1: UNDERSTAND (需求理解)",
        "spec": "Phase 2: SPEC (规格设计)",
        "build": "Phase 3: BUILD (切片规划+TDD实现+质量验证)",
        "deliver": "Phase 4: DELIVER (交付)",
    }
    status_icons = {
        "pending": "  ",
        "in_progress": "  ",
        "completed": "  ",
    }

    for phase in phase_order:
        phase_info = state.get("phases", {}).get(phase, {})
        phase_status = phase_info.get("status", "pending")
        icon = status_icons.get(phase_status, " ?")
        name = phase_names.get(phase, phase)
        confirmed = phase_info.get("confirmed_at", "")
        confirm_str = f" (确认于 {confirmed})" if confirmed else ""
        print(f"   {icon}  {name}: {phase_status}{confirm_str}")

    print(f"\n  文件状态:")
    expected_files = [
        "proposal.md", "design.md", "test-plan.md",
        "tasks.md", "test-report.md", "design-adjustments.md"
    ]
    for f in expected_files:
        exists = (change_dir / f).exists()
        icon = "  " if exists else "  "
        print(f"   {icon}  {f}")

    specs_dir = change_dir / "specs"
    if specs_dir.exists():
        spec_files = list(specs_dir.rglob("*.md"))
        print(f"     Spec 文件: {len(spec_files)} 个")
        for sf in spec_files:
            print(f"      - {sf.relative_to(change_dir)}")

    # V3.0.1: Guard status
    print()
    _show_guard_status(project_root)
    _show_zombie_changes(project_root, change_dir.name)


def _show_zombie_changes(project_root: Path, current_name: str) -> None:
    """V3.0.1: Show zombie changes in changes/ directory."""
    from datetime import datetime, timedelta
    changes_dir = project_root / ".stdd" / "changes"
    if not changes_dir.exists():
        return
    zombies = []
    for d in sorted(changes_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue
        if d.name == current_name:
            continue
        yf = d / ".stdd.yaml"
        if not yf.exists():
            continue
        import yaml
        data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        last_mod = data.get("last_modified", "")
        if not last_mod:
            continue
        try:
            lm = datetime.fromisoformat(last_mod)
            if datetime.now() - lm > timedelta(days=7):
                zombies.append(d.name)
        except Exception:
            pass
    if zombies:
        print(f"  ⚠️ 僵尸 Change ({len(zombies)}): {', '.join(zombies)} — 建议 stdd abort 清理")


def _show_guard_status(project_root: Path) -> None:
    """V3.0.1: Display Guard installation status."""
    import json
    settings_file = project_root / ".claude" / "settings.local.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {}).get("PreToolUse", [])
            if any("stdd guard" in str(h) for h in hooks):
                print(f"  Guard: ✅ 已激活 (Claude Code)")
                return
        except Exception:
            pass
    # Check OpenCode
    opencode_file = project_root / ".opencode" / "settings.json"
    if opencode_file.exists():
        try:
            settings = json.loads(opencode_file.read_text(encoding="utf-8"))
            if any("stdd guard" in str(h) for h in settings.get("hooks", {}).get("PreToolUse", [])):
                print(f"  Guard: ✅ 已激活 (OpenCode)")
                return
        except Exception:
            pass
    # Check Codex
    agents_file = project_root / "AGENTS.md"
    if agents_file.exists() and "STDD-GUARD-ENABLED" in agents_file.read_text(encoding="utf-8"):
        print(f"  Guard: ✅ 已激活 (Codex CLI)")
        return
    print(f"  Guard: ⚠️ 未安装 — 执行 stdd guard init 安装")
