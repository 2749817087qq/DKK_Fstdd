#!/usr/bin/env python3
"""STDD SessionStart Hook — auto-load change state + V3.0.1 new project guidance + phase integrity."""
from pathlib import Path
import yaml
from datetime import datetime


def main():
    project_root = Path.cwd()
    changes_dir = project_root / ".stdd" / "changes"

    # ── V3.0.1: New project detection ──
    archive_dir = project_root / ".stdd" / "archive"
    completed_changes = 0
    if archive_dir.exists():
        completed_changes = len([d for d in archive_dir.iterdir()
                                 if d.is_dir() and not d.name.startswith(".")
                                 and (d / ".stdd.yaml").exists()])

    # V3.0.2: Check for upgrade notes (AI self-learning)
    notes_path = project_root / ".stdd" / "UPGRADE_NOTES.yaml"
    is_new_project = completed_changes == 0

    if is_new_project or notes_path.exists():
        if is_new_project:
            print("[STDD Guard] 🆕 新项目 — STDD V3.0 流程管控已启用")
        else:
            try:
                notes = yaml.safe_load(notes_path.read_text(encoding="utf-8")) or {}
                fv = notes.get("from_version", "?")
                tv = notes.get("to_version", "?")
                print(f"[STDD Guard] 📦 已升级: {fv} → {tv}")
                for ch in notes.get("changes", [])[:2]:  # show last 2 versions
                    print(f"[STDD Guard]    {ch['version']}: {ch['title']}")
            except Exception:
                pass
        manual = project_root / ".stdd" / "onboarding" / "AI_OPERATING_MANUAL.yaml"
        if manual.exists():
            print("[STDD Guard]   📖 请阅读 AI 操作手册: .stdd/onboarding/AI_OPERATING_MANUAL.yaml")
            print("[STDD Guard]   📋 完成自检清单（self_check 章节，8 道题）")
        if notes_path.exists():
            print("[STDD Guard]   📝 版本变更: .stdd/UPGRADE_NOTES.yaml")
            notes_path.unlink()  # one-time, don't repeat
        print()

    # ── Active change display ──
    if not changes_dir.exists():
        return
    for change_dir in sorted(changes_dir.iterdir()):
        if not change_dir.is_dir():
            continue
        if change_dir.name.startswith("_") or change_dir.name.startswith("."):
            continue
        stdd_yaml = change_dir / ".stdd.yaml"
        if stdd_yaml.exists():
            state = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
            phase = state.get("active_phase", "?")
            name = state.get("change_name", change_dir.name)
            print(f"[STDD] Active change: {name} (Phase {phase})")
            pc = state.get("phase_context_file", "")
            if pc:
                print(f"[STDD] Phase context: {pc}")

            # V3.0.1: Phase integrity check
            phases = state.get("phases", {})
            _check_phase_gaps(change_dir.name, phases)
            break

    # V3.0.1: Zombie change detection
    _check_zombie_changes(project_root)

    # V3.0.1: Guard status
    _show_guard_status(project_root)


def _check_zombie_changes(project_root: Path) -> None:
    """Warn about zombie changes (>7 days inactive)."""
    from datetime import datetime, timedelta
    changes_dir = project_root / ".stdd" / "changes"
    if not changes_dir.exists():
        return
    zombies = []
    for d in sorted(changes_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue
        yf = d / ".stdd.yaml"
        if not yf.exists():
            continue
        data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        last_mod = data.get("last_modified", "")
        if not last_mod:
            continue
        try:
            lm = datetime.fromisoformat(last_mod)
            if datetime.now() - lm > timedelta(days=7):
                phase = data.get("active_phase", "?")
                zombies.append((d.name, phase))
        except Exception:
            pass
    if zombies:
        print("[STDD Guard] ⚠️ 僵尸 Change 检测（>7天未推进）:")
        for name, phase in zombies:
            print(f"[STDD Guard]   {name} (phase: {phase}) — 建议 stdd abort 或 archive")
        print()


def _check_phase_gaps(change_name: str, phases: dict) -> None:
    """Warn about skipped or stuck phases."""
    build_done = phases.get("build", {}).get("status") == "completed"
    verify_done = phases.get("verify", {}).get("status") == "completed"
    build_time = phases.get("build", {}).get("completed_at", "")
    spec_done = phases.get("spec", {}).get("status") == "completed"
    slice_done = phases.get("slice", {}).get("status") == "completed"
    spec_time = phases.get("spec", {}).get("completed_at", "")

    if build_done and not verify_done:
        try:
            bt = datetime.fromisoformat(build_time)
            hours = (datetime.now() - bt).total_seconds() / 3600
            if hours > 1:
                print(f"[STDD Guard] ⚠️ Build 完成已 {hours:.0f}h，Verify 尚未开始")
                print("[STDD Guard]    请执行 Phase 5: /stdd-continue → Verify")
        except Exception:
            pass

    if spec_done and not slice_done:
        try:
            st = datetime.fromisoformat(spec_time)
            hours = (datetime.now() - st).total_seconds() / 3600
            if hours > 24:
                print(f"[STDD Guard] ⚠️ Spec 完成已 >24h，Slice 尚未开始")
        except Exception:
            pass


def _show_guard_status(project_root: Path) -> None:
    """Show Guard installation status."""
    import json
    settings_file = project_root / ".claude" / "settings.local.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {}).get("PreToolUse", [])
            if any("stdd guard" in str(h) for h in hooks):
                return  # Guard active, silent
        except Exception:
            pass
    print("[STDD Guard] ⚠️ Guard 未安装 — 手动执行: stdd guard init")


if __name__ == "__main__":
    main()
