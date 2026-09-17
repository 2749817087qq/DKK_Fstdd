"""STDD phase CLI — advance and check change phase (V3.0.5, 4-phase model)."""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import yaml

from .phase_constants import (
    PHASE_ORDER as _PHASE_ORDER,
    PHASE_LABELS as _PHASE_LABELS,
    GATE_PHASES as _GATE_PHASES,
    GATE_PHASE_ORDER as _GATE_PHASE_ORDER,
    LEGACY_PHASE_MAP,
)


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


def cmd_phase(args: argparse.Namespace) -> None:
    """Advance or check change phase."""
    project_root = Path.cwd()
    action = getattr(args, "phase_action", "status")
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
    current = data.get("current_phase", "understand")

    if action == "record-slice":
        if current != "build":
            print("  ❌ 只有 BUILD phase 可以记录 Slice 证据。")
            sys.exit(1)
        slice_id = getattr(args, "target_phase", None)
        tc_coverage = (getattr(args, "tc_coverage", None) or "").strip()
        new_tests = getattr(args, "new_tests", None)
        verified_at = (getattr(args, "verified_at", None) or "").strip()
        if not slice_id or not tc_coverage or new_tests is None or not verified_at:
            print("  Usage: fstdd phase record-slice <change> <slice-id> --tc-coverage <TCs> --new-tests <N> --verified-at <ISO>")
            sys.exit(2)
        phases = data.setdefault("phases", {})
        build = phases.setdefault("build", {})
        slices = build.setdefault("slices_completed", {})
        existing = slices.get(slice_id)
        evidence = {
            "tc_coverage": tc_coverage,
            "new_tests": new_tests,
            "verified_at": verified_at,
        }
        if existing and existing != evidence:
            print(f"  ❌ Slice {slice_id} 已存在不同证据，拒绝覆盖。")
            sys.exit(1)
        slices[slice_id] = evidence
        data["last_modified"] = datetime.now().isoformat()
        stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        print(f"  Slice {slice_id} evidence recorded for change {change_dir.name}")
        return

    if action == "status":
        idx = _PHASE_ORDER.index(current) if current in _PHASE_ORDER else -1
        print(f"  Change: {change_dir.name}")
        print(f"  Current phase: {_PHASE_LABELS.get(current, current)}")
        print(f"  Status: {data.get('phases', {}).get(current, {}).get('status', 'unknown')}")
        print(f"  Mode: {data.get('mode', 'standard')}")
        print(f"  Task type: {data.get('task_type', 'code')}")
        # Show next phase
        if idx >= 0 and idx + 1 < len(_PHASE_ORDER):
            nxt = _PHASE_ORDER[idx + 1]
            print(f"  Next: {_PHASE_LABELS.get(nxt, nxt)}")
        return

    if action == "advance":
        idx = _PHASE_ORDER.index(current) if current in _PHASE_ORDER else -1
        if idx < 0:
            # V3.0.5: normalize legacy 6-phase states (slice/verify → build)
            norm = LEGACY_PHASE_MAP.get(current)
            if norm:
                idx = _PHASE_ORDER.index(norm)
            else:
                print(f"  Unknown phase: {current}")
                sys.exit(1)
        if idx + 1 >= len(_PHASE_ORDER):
            print(f"  Already at final phase: {_PHASE_LABELS.get(current, current)}")
            sys.exit(0)

        phases = data.setdefault("phases", {})

        # V3.0.5: Gate phases require explicit gate confirmation before advancing
        if current in _GATE_PHASES:
            gate_name = _GATE_PHASES[current]
            current_phase_data = phases.get(current, {})
            if not current_phase_data.get("confirmed_at"):
                gate_num = _GATE_PHASE_ORDER.index(current) + 1
                print(f"  ❌ 当前 Phase 需要 {gate_name} 确认后才能推进。")
                print(f"     请先完成 {gate_name} 确认:")
                print(f"       - 对话确认: 在 Phase 结束时等待用户确认")
                print(f"       - 文件确认: 创建 GATE{gate_num}_APPROVED 文件")
                print(f"       - CLI 确认: stdd gate approve --gate {gate_num}")
                sys.exit(1)

        # V3.0.5: Pre-condition checks for phase transitions (merged at build→deliver)
        nxt = _PHASE_ORDER[idx + 1]
        if nxt == "deliver":
            # build is the merged SLICE+BUILD+VERIFY phase: must carry per-slice evidence
            slices = data.get("phases", {}).get("build", {}).get("slices_completed", {})
            if not slices:
                print("  ❌ BUILD → DELIVER 需要 per-slice 验证证据链。")
                print("     请确保每个 Slice 的 .fstdd.yaml 中包含 tc_coverage/new_tests/verified_at")
                sys.exit(1)
            for sid, sdata in slices.items():
                tc = sdata.get("tc_coverage", "")
                nt = sdata.get("new_tests", "")
                va = sdata.get("verified_at", "")
                if not tc or (not isinstance(nt, int) and not nt) or not va:
                    print(f"  ❌ Slice {sid} 验证证据不完整: tc_coverage={tc}, new_tests={nt}, verified_at={va}")
                    print("     请完成 per-slice 验证后再推进。")
                    sys.exit(1)
            tr = change_dir / "test-report.md"
            if not tr.exists():
                print("  ❌ BUILD → DELIVER 需要 test-report.md。")
                print("     请先完成 Phase 3 BUILD（运行测试、失败模式检查、生成 test-report.md）。")
                sys.exit(1)

        # Mark current phase completed
        phases.setdefault(current, {})["status"] = "completed"
        # Only auto-set confirmed_at for non-gate phases
        if current not in _GATE_PHASES:
            phases.setdefault(current, {})["confirmed_at"] = datetime.now().isoformat()

        # Advance to next
        data["current_phase"] = nxt
        phases.setdefault(nxt, {})["status"] = "in_progress"
        data["last_modified"] = datetime.now().isoformat()

        stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

        print(f"  {_PHASE_LABELS.get(current, current)} → {_PHASE_LABELS[nxt]}")
        print(f"  Change: {change_dir.name}")
        if nxt == "build":
            print(f"  💡 Build phase — Guard 已放行 Edit/Write")

    elif action == "set":
        target = getattr(args, "target_phase", None)
        if not target:
            print("  Usage: stdd phase set <phase>")
            sys.exit(1)
        if target not in _PHASE_ORDER:
            print(f"  Invalid phase: {target}. Valid: {', '.join(_PHASE_ORDER)}")
            sys.exit(1)
        data["current_phase"] = target
        data.setdefault("phases", {}).setdefault(target, {})["status"] = "in_progress"
        data["last_modified"] = datetime.now().isoformat()
        stdd_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
        print(f"  Phase set to {_PHASE_LABELS[target]}")
        print(f"  Change: {change_dir.name}")
