"""rollback 命令 — 从 archive 恢复已归档的 change。"""
import argparse
import sys
import shutil
from pathlib import Path

import yaml

from .phase_constants import PHASE_ORDER as _PHASE_ORDER


def _kept_current_phase(state: dict) -> str:
    """恢复时应保留的 `current_phase`（2026-10-07 / SC-203）。

    - 有值 ⇒ **原样保留** —— `rollback` 的语义是「恢复」，不是「重做」；
    - 无值（老数据）⇒ 回落到「首个非 `completed` 的相位」；
    - 全部 `completed`（或结构缺失）⇒ 回落 `understand`。
    """
    current = state.get("current_phase")
    if current:
        return current
    phases = state.get("phases") or {}
    for phase in _PHASE_ORDER:
        if (phases.get(phase) or {}).get("status") != "completed":
            return phase
    return "understand"


def cmd_rollback(args: argparse.Namespace) -> None:
    from ..finder import _resolve_in
    from ..utils import get_logger
    logger = get_logger()

    project_root = Path.cwd()
    name = args.name

    archive_dir = project_root / ".fstdd" / "archive"
    if not archive_dir.exists():
        print(f" .fstdd/archive/ 目录不存在")
        sys.exit(1)

    # 在 archive/ 与 archive/aborted/ 中解析（2026-10-07 收口）。
    # ⚠️ 这里**不能**用 `find_change_dir(include_archive=True)` —— 它优先返回 `changes/`
    # 下的同名目录，而 rollback 要的恰恰是**归档区那一份**。
    # 故复用 finder 的解析原语 `_resolve_in`（精确名 → 后缀匹配），删掉本地重复实现的匹配循环；
    # `archive/aborted/` 是统一入口不覆盖的额外来源，单独扫一次。
    target = _resolve_in(archive_dir, name)
    if target is None:
        aborted_dir = archive_dir / "aborted"
        if aborted_dir.is_dir():
            target = _resolve_in(aborted_dir, name)

    if target is None:
        print(f" 在 archive 中找不到 change: {name}")
        sys.exit(1)

    # 检查 changes/ 下是否已有同名目录
    changes_dir = project_root / ".fstdd" / "changes"
    conflict_dir = changes_dir / target.name
    if conflict_dir.exists():
        print(f" 冲突: changes/{target.name} 已存在")
        print(f"   无法恢复，目标路径已被占用")
        sys.exit(1)

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        _sf = target / ".fstdd.yaml"
        kept = "understand"
        if _sf.exists():
            try:
                kept = _kept_current_phase(yaml.safe_load(_sf.read_text(encoding="utf-8")) or {})
            except Exception:
                kept = "understand"   # 状态文件损坏时预览不得崩（实际恢复路径另有 yaml 解析）
        print(" [DRY-RUN] 将执行以下操作:")
        print(f"   从 archive/ 恢复: {target.name} -> changes/{target.name}")
        print(f"   更新状态: status=active, current_phase={kept}（保留原相位）")
        print(" [DRY-RUN] 文件系统未发生变化")
        return

    logger.info("恢复 %s -> changes/%s", target.name, target.name)

    # 更新状态
    state_file = target / ".fstdd.yaml"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            state = yaml.safe_load(f) or {}
        state["status"] = "active"
        # 2026-10-07（archive-state-consistency / SC-203）：**保留原 current_phase**。
        # 修复前无条件写死 `state["current_phase"] = "understand"`，而 `phases.*.status` 全部保留
        # ⇒ 恢复后 `current_phase=understand` 与 `phases.understand.status=completed` 自相矛盾，
        # 继续推进会回到 spec 而非原相位（`rollback` 的语义是「恢复」，不是「重做」）。
        # ⚠️ 只写 status 与（必要时）current_phase：`phases.*` 一个不碰（SC-204 / KG-094）。
        state["current_phase"] = _kept_current_phase(state)
        with open(state_file, "w", encoding="utf-8") as f:
            yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    # 移动到 changes/
    shutil.move(str(target), str(conflict_dir))

    print(f" 已恢复: changes/{target.name}")
    print(f"   状态已更新为 active")
    print(f"   使用 /fstdd-continue 或 fstdd status {target.name} 查看")
