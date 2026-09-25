import argparse
import sys
import re
import shutil
from datetime import date
from pathlib import Path

import yaml


def cmd_new(args: argparse.Namespace) -> None:
    from ..utils import get_logger
    logger = get_logger()

    project_root = Path.cwd()
    change_name = args.name

    if not re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9_.]{1,49}\Z", change_name):
        print(f" 无效的 change 名称: {change_name}")
        print(f"   名称必须以字母或数字开头，可包含连字符(-)、下划线(_)、点(.)")
        print(f"   长度 2-50 字符，不能包含空格或特殊字符")
        print(f"   示例: fix-login-bug, feature_rate_limit, v1.2.1")
        sys.exit(1)

    today = date.today().isoformat()
    # 幂等：名字已以 YYYY-MM-DD- 开头时不再 prepend，避免产生双日期脚手架
    # （`stdd new 2026-09-25-fix-x` → `2026-09-25-2026-09-25-fix-x`，确定性缺陷）
    if re.match(r"^\d{4}-\d{2}-\d{2}-", change_name):
        dir_name = change_name
    else:
        dir_name = f"{today}-{change_name}"
    change_dir = project_root / ".fstdd" / "changes" / dir_name

    if change_dir.exists():
        print(f" Change 目录已存在: changes/{dir_name}")
        sys.exit(1)

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print(" [DRY-RUN] 将执行以下操作:")
        print(f"   创建 change 目录: changes/{dir_name}")
        print(f"   创建 specs 子目录: changes/{dir_name}/specs")
        print(f"   复制模板: design.md, test-plan.md")
        print(f"   Scaffold Canonical YAML: canonical/proposals/, specs/code/ (YAML-first)")
        print(f"   创建状态文件: changes/{dir_name}/.fstdd.yaml")
        print(f"   状态版本: 3.0, 状态: active")
        print(" [DRY-RUN] 文件系统未发生变化")
        return

    (change_dir / "specs").mkdir(parents=True)

    # V3.0.5 (YAML-first): proposal.md 不再复制 — Gate 1 时从 canonical YAML 自动生成。
    templates_dir = project_root / ".fstdd" / "templates"
    for tmpl_name in ["design", "test-plan"]:
        tmpl = templates_dir / f"{tmpl_name}.md"
        if tmpl.exists():
            shutil.copy2(tmpl, change_dir / f"{tmpl_name}.md")

    state = {
        "version": "3.0",             # V3.0.5: 4-phase state schema
        "change_id": dir_name,
        "status": "active",
        "current_phase": "understand",
        "mode": "standard",           # V2.9: standard | lightweight | thorough
        "task_type": getattr(args, "task_type", "code") or "code",  # V2.9.4: from --task-type
        "complexity_score": None,     # V2.9: set by Phase 1 Step 3.5
        "score_confidence": None,     # V2.9: preliminary | confirmed
        "phases": {
            "understand": {"status": "pending"},
            "spec": {"status": "pending"},
            "build": {"status": "pending"},
            "deliver": {"status": "pending"},
        },
        "design_adjustments": {"count": 0},
        "traceability": {"spec_scenarios": 0, "tc_cases": 0, "test_functions": 0},
    }
    with open(change_dir / ".fstdd.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    # V3.0.5 (YAML-first): scaffold Canonical YAML 模板（AI 只写 YAML，MD 由 Gate 自动生成）
    # 失败不阻断 change 创建，但**必须出声** —— 静默 pass 会让 change 目录建好而
    # canonical 缺失，且用户看到「Change 创建完成」误以为一切就绪。
    canon_ok = True
    try:
        from .canon import cmd_canon_init
        import argparse as _argparse
        cmd_canon_init(_argparse.Namespace(
            subcommand="init",
            change=dir_name,
            project_level=False,
        ))
    except SystemExit as exc:
        canon_ok = False
        print(f" ⚠️ Canonical YAML scaffold 失败（exit={exc.code}）")
        print(f"   change 目录已建，但 canonical/ 可能缺失 —— 请手动执行：")
        print(f"   stdd canon init --change {dir_name}")
    except Exception as exc:  # 非 SystemExit 的异常同样要出声，不能静默
        canon_ok = False
        print(f" ⚠️ Canonical YAML scaffold 异常: {type(exc).__name__}: {exc}")
        print(f"   change 目录已建，但 canonical/ 可能缺失 —— 请手动执行：")
        print(f"   stdd canon init --change {dir_name}")

    logger.info("Change 创建完成: changes/%s", dir_name)
    print(f" Change 创建完成: changes/{dir_name}")
    print(f"   模板已就绪: design.md, test-plan.md")
    print(f"   Canonical YAML: canonical/proposals/{dir_name}.yaml + specs/code/ (YAML-first)")
    print(f"   proposal.md 将在 Gate 1 自动生成")
    print(f"   状态文件: .fstdd.yaml")

    # 终态校验：不看 canon_init 是否抛异常，直接验端状态 —— canonical 产物是否真的在盘上。
    # 异常被上面吃掉、或 canon_init 正常退出但漏写文件，都会在这里暴露。
    canon_root = project_root / ".fstdd" / "changes" / dir_name / "canonical"
    if canon_ok and not canon_root.exists():
        canon_ok = False
        print(f" ⚠️ 终态校验失败: canonical/ 目录不存在于 changes/{dir_name}/")
        print(f"   change 可用，但缺 YAML-first 骨架 —— 请手动执行：stdd canon init --change {dir_name}")
    print(f"   Canonical 终态: {'✅ 就绪' if canon_ok else '❌ 缺失（见上方告警）'}")

    # V2.8: Two-Instance Kickoff
    if getattr(args, "parallel", False):
        _setup_parallel_worktrees(project_root, dir_name)

    print()
    print("  下一步:")
    print(f"   /fstdd-understand  开始需求理解阶段")


def _setup_parallel_worktrees(project_root: Path, change_name: str):
    """V2.8: Create parallel worktrees for Two-Instance Kickoff."""
    import subprocess
    base = project_root / ".claude" / "worktrees"
    base.mkdir(parents=True, exist_ok=True)

    print(f"\n  🔀 Two-Instance Kickoff 模式")
    print(f"  {'─' * 40}")

    for suffix, role, desc in [
        ("-explore", "Explorer", "需求探索 → proposal.md"),
        ("-research", "Researcher", "技术调研 → research.md"),
    ]:
        wt_path = base / f"{change_name}{suffix}"
        if not wt_path.exists():
            result = subprocess.run(
                ["git", "worktree", "add", str(wt_path)],
                capture_output=True, text=True, cwd=project_root
            )
            if result.returncode == 0:
                print(f"  ✅ {role}: {wt_path}")
                print(f"     职责: {desc}")
            else:
                print(f"  ⚠️ {role}: 创建失败 — {result.stderr.strip()}")
        else:
            print(f"  ⚠️ {role}: worktree 已存在 — {wt_path}")

    print()
    print(f"  启动双 Agent (在两个终端中分别执行):")
    print(f"    Terminal 1 (Explorer):  cd {base}/{change_name}-explore  && claude")
    print(f"    Terminal 2 (Researcher): cd {base}/{change_name}-research && claude")
    print(f"  Gate 1 前合并双 Agent 结果到 changes/{change_name}/")
