"""STDD hooks CLI — lifecycle hook management (V2.7)."""

import sys
import json
from pathlib import Path


HOOK_SCRIPTS = {
    "session-start": """#!/usr/bin/env python3
\"\"\"STDD SessionStart Hook — auto-load change state.\"\"\"
from pathlib import Path
import yaml

def _find_active_change_dir(changes_dir):
    \"\"\"与 phase.py 同语义：最近修改的 change 视为活跃。

    按字母序取第一个会命中**早已停更**的 change（多 change 并存时），
    与 phase.py / guard 的「活跃」定义不一致 ⇒ 显示与判定分歧。
    \"\"\"
    candidates = sorted(
        (d for d in changes_dir.iterdir()
         if d.is_dir() and d.name != "_batch" and (d / ".fstdd.yaml").exists()),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    return candidates[0] if candidates else None

def main():
    project_root = Path.cwd()
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        return
    change_dir = _find_active_change_dir(changes_dir)
    if change_dir is None:
        return
    stdd_yaml = change_dir / ".fstdd.yaml"
    state = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
    phase = state.get("active_phase", "?")
    name = state.get("change_name", change_dir.name)
    print(f"[STDD] Active change: {name} (Phase {phase})")
    pc = state.get("phase_context_file", "")
    if pc:
        print(f"[STDD] Phase context: {pc}")

if __name__ == "__main__":
    main()
""",
    "pre-compact": """#!/usr/bin/env python3
\"\"\"STDD PreCompact Hook — save critical state before compaction.\"\"\"
from pathlib import Path
from datetime import datetime, timezone
import yaml

# 本脚本被注册为**独立脚本**执行（python .fstdd/hooks/pre-compact.py），
# 此时已脱离包 ⇒ `from ..timeutil import ...` 必然 ImportError。
# 时间戳就地生成，口径与 fstdd/cli/timeutil.utc_now_iso 一致（SC-010：必须带时区）。
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _find_active_change_dir(changes_dir):
    \"\"\"与 phase.py 同语义：最近修改的 change 视为活跃。

    ⚠️ 按字母序取第一个会命中**早已停更**的 change：本 hook 是**写操作**，
    写错 change 等于给那个 change 虚假刷新 last_modified，
    干扰依赖 last_modified 的僵尸检测。
    \"\"\"
    candidates = sorted(
        (d for d in changes_dir.iterdir()
         if d.is_dir() and d.name != "_batch" and (d / ".fstdd.yaml").exists()),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    return candidates[0] if candidates else None

def main():
    project_root = Path.cwd()
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        return
    change_dir = _find_active_change_dir(changes_dir)
    if change_dir is None:
        return
    stdd_yaml = change_dir / ".fstdd.yaml"
    state = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
    state["last_modified"] = _utc_now_iso()
    # 与 phase.py / new.py 同口径落盘 —— 只改内存不写盘等于什么都没存
    stdd_yaml.write_text(
        yaml.dump(state, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"[STDD] State saved: {change_dir.name} (Phase {state.get('active_phase', '?')})")

if __name__ == "__main__":
    main()
""",
    "session-end": """#!/usr/bin/env python3
\"\"\"STDD Stop Hook — persist session learnings.\"\"\"
from pathlib import Path
import yaml

def main():
    project_root = Path.cwd()
    exp_dir = project_root / ".fstdd" / "experiences"
    exp_count = len([p for p in exp_dir.glob("*.md") if not p.name.startswith(".")]) if exp_dir.exists() else 0
    if exp_count > 0:
        print(f"[STDD] Experience library: {exp_count} entries")
        print(f"[STDD] Tip: run 'stdd experience curate' to extract new patterns")

if __name__ == "__main__":
    main()
""",
}


def _validate_hooks_config(settings_path: Path) -> list[str]:
    """Validate that hooks in settings.json use correct array-of-matchers format.

    Returns a list of warning messages (empty = all valid).
    """
    warnings: list[str] = []
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return [f"  ⚠️  Cannot read settings for validation: {e}"]

    hooks = settings.get("hooks", {})
    for hook_name in ("SessionStart", "PreCompact", "Stop"):
        if hook_name not in hooks:
            continue
        value = hooks[hook_name]
        if not isinstance(value, list):
            warnings.append(
                f"  ⚠️  hooks.{hook_name} should be an array of matchers, "
                f"got {type(value).__name__}. Hook may be ignored by Claude Code."
            )
            continue
        for i, matcher in enumerate(value):
            if not isinstance(matcher, dict):
                warnings.append(
                    f"  ⚠️  hooks.{hook_name}[{i}] should be a dict, "
                    f"got {type(matcher).__name__}."
                )
                continue
            matcher_hooks = matcher.get("hooks", [])
            if not matcher_hooks:
                warnings.append(
                    f"  ⚠️  hooks.{hook_name}[{i}].hooks is empty or missing."
                )
                continue
            for j, h in enumerate(matcher_hooks):
                if not isinstance(h, dict):
                    warnings.append(
                        f"  ⚠️  hooks.{hook_name}[{i}].hooks[{j}] should be a dict."
                    )
                    continue
                if h.get("type") != "command":
                    warnings.append(
                        f"  ⚠️  hooks.{hook_name}[{i}].hooks[{j}].type "
                        f"should be 'command', got {h.get('type')!r}."
                    )
                if "command" not in h:
                    warnings.append(
                        f"  ⚠️  hooks.{hook_name}[{i}].hooks[{j}] "
                        f"missing 'command' field."
                    )
    return warnings


def cmd_hooks_install(args):
    """Install STDD hooks to .claude/settings.json."""
    project_root = Path.cwd()
    hooks_dir = project_root / ".fstdd" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Write hook scripts
    for name, script in HOOK_SCRIPTS.items():
        script_path = hooks_dir / f"{name}.py"
        if script_path.exists() and not args.force:
            print(f"  [SKIP] {name}.py already exists (use --force to overwrite)")
            continue
        script_path.write_text(script, encoding="utf-8")
        print(f"  [OK] .fstdd/hooks/{name}.py")

    # Update .claude/settings.json
    settings_path = project_root / ".claude" / "settings.local.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings = {}

    hooks_config = settings.setdefault("hooks", {})
    hooks_config["SessionStart"] = [
        {"hooks": [{"type": "command", "command": "python .fstdd/hooks/session-start.py"}]}
    ]
    hooks_config["PreCompact"] = [
        {"hooks": [{"type": "command", "command": "python .fstdd/hooks/pre-compact.py"}]}
    ]
    hooks_config["Stop"] = [
        {"hooks": [{"type": "command", "command": "python .fstdd/hooks/session-end.py"}]}
    ]

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  [OK] Hooks configured in .claude/settings.local.json")

    # Validate the written config
    warnings = _validate_hooks_config(settings_path)
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("  [OK] Hook config format validated")


def cmd_hooks_status(args):
    """Show current hooks status."""
    project_root = Path.cwd()
    hooks_dir = project_root / ".fstdd" / "hooks"
    if not hooks_dir.exists():
        print("  No STDD hooks installed.")
        return

    scripts = list(hooks_dir.glob("*.py"))
    print(f"  Installed hooks: {len(scripts)}")
    for s in sorted(scripts):
        print(f"    - {s.name}")


def cmd_hooks_uninstall(args):
    """Remove STDD hooks configuration."""
    project_root = Path.cwd()
    settings_path = project_root / ".claude" / "settings.local.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if "hooks" in settings:
            del settings["hooks"]
            settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  Hooks removed from .claude/settings.local.json")


def _dispatch(args):
    """Route to appropriate hooks subcommand."""
    if args.action == "install":
        cmd_hooks_install(args)
    elif args.action == "status":
        cmd_hooks_status(args)
    elif args.action == "uninstall":
        cmd_hooks_uninstall(args)
    else:
        print(f"  Unknown hooks action: {args.action}")
        sys.exit(1)
