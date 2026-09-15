import argparse
import sys
import shutil
from pathlib import Path

# ── 模块级常量：供 upgrade.py 等模块导入复用 ──

DIRS = [
    ".stdd/skills",
    ".stdd/skills/_shared",
    ".stdd/templates",
    ".stdd/templates/canonical",
    ".stdd/templates/human-view",
    ".stdd/standards",
    ".stdd/config.d",
    ".stdd/experiences",
    ".stdd/onboarding",
    ".stdd/platforms/claude-code/skills",
    ".stdd/platforms/workbuddy/skills",
    ".stdd/platforms/trae/skills",
    ".stdd/canonical/proposals",
    ".stdd/canonical/specs",
    ".stdd/canonical/designs",
    ".stdd/agent_tests",
    ".stdd/changes",
    ".stdd/specs",
    ".stdd/archive",
]

FILES_TO_COPY = [
    # Config
    ".stdd/config.d/project.yaml",
    ".stdd/config.d/gates.yaml",
    ".stdd/config.d/long_range.yaml",
    ".stdd/config.d/quality.yaml",
    ".stdd/config.d/lite.yaml",
    ".stdd/config.d/experience.yaml",
    ".stdd/config.d/knowledge.yaml",
    ".stdd/config.d/guard.yaml",
    # Skills
    ".stdd/skills/understand.md",
    ".stdd/skills/spec.md",
    ".stdd/skills/build.md",
    ".stdd/skills/deliver.md",
    ".stdd/skills/upgrade.md",
    ".stdd/skills/_shared/version-check.md",
    # Human View templates
    ".stdd/templates/proposal.md",
    ".stdd/templates/design.md",
    ".stdd/templates/spec.md",
    ".stdd/templates/test-plan.md",
    ".stdd/templates/tasks.md",
    ".stdd/templates/slices.md",
    ".stdd/templates/design-adjustments.md",
    ".stdd/templates/test-report.md",
    ".stdd/templates/phase-context.md",
    ".stdd/templates/spec-draft.md",
    ".stdd/templates/long-range-auth.md",
    ".stdd/templates/human-view/proposal-brief.md",
    # Canonical YAML templates (dual-track system)
    ".stdd/templates/canonical/proposal.yaml",
    ".stdd/templates/canonical/spec.yaml",
    ".stdd/templates/canonical/agent_spec.yaml",
    ".stdd/templates/canonical/design-adjustments.yaml",
    ".stdd/templates/canonical/pending-adjustments.yaml",
    # Onboarding (V3.0.1)
    ".stdd/onboarding/AI_OPERATING_MANUAL.yaml",
    ".stdd/onboarding/AI_OPERATING_MANUAL.md",
    # Standards
    ".stdd/standards/python.md",
    # Project docs
    "STDD.md",
    "AGENTS.md",
]

# Config files that should be MERGED (not overwritten) during upgrade.
CONFIG_MERGE_FILES = [
    ".stdd/config.d/project.yaml",
]

# All config files under config.d/
CONFIG_ALL_FILES = [
    ".stdd/config.d/project.yaml",
    ".stdd/config.d/gates.yaml",
    ".stdd/config.d/long_range.yaml",
    ".stdd/config.d/quality.yaml",
]

# Platforms with skills directories under .stdd/platforms/
PLATFORMS = ["claude-code", "workbuddy", "trae"]


def cmd_init(args: argparse.Namespace) -> None:
    project_root = Path.cwd()

    from ..utils import get_stdd_source, get_logger
    logger = get_logger()
    stdd_source = get_stdd_source()

    dirs = DIRS
    files_to_copy = FILES_TO_COPY

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print(" [DRY-RUN] 将执行以下操作:")
        print(f"   项目根目录: {project_root}")
        for d in dirs:
            print(f"   创建目录: {d}")
        force = getattr(args, "force", False)
        for f in files_to_copy:
            src = stdd_source / f
            if src.exists():
                dst = project_root / f
                if force or not dst.exists():
                    print(f"   复制: {f}")
            else:
                print(f"   (缺失源文件: {f})")
        for platform in PLATFORMS:
            platform_skills = stdd_source / ".stdd" / "platforms" / platform / "skills"
            if platform_skills.exists():
                for skill_file in platform_skills.iterdir():
                    dst = project_root / ".stdd" / "platforms" / platform / "skills" / skill_file.name
                    if force or not dst.exists():
                        print(f"   复制: {dst}")
        print(" [DRY-RUN] 文件系统未发生变化")
        return

    for d in dirs:
        (project_root / d).mkdir(parents=True, exist_ok=True)

    force = getattr(args, "force", False)
    copied = 0
    skipped = 0
    for f in files_to_copy:
        src = stdd_source / f
        dst = project_root / f
        if src.exists():
            if force or not dst.exists():
                shutil.copy2(src, dst)
                copied += 1
            else:
                skipped += 1

    for platform in PLATFORMS:
        platform_skills = stdd_source / ".stdd" / "platforms" / platform / "skills"
        if platform_skills.exists():
            for skill_file in platform_skills.iterdir():
                dst = project_root / ".stdd" / "platforms" / platform / "skills" / skill_file.name
                if force or not dst.exists():
                    shutil.copy2(skill_file, dst)
                    copied += 1
                else:
                    skipped += 1

    logger.info("STDD 初始化完成，已复制 %d 个文件", copied)
    print("STDD 初始化完成")
    print(f"   项目根目录: {project_root}")
    print(f"   已创建 .stdd/ 目录、changes/、specs/、archive/、agent_tests/")
    if force and skipped > 0:
        print(f"   已复制 {copied} 个文件, 跳过 {skipped} 个已存在文件（使用 --force 覆盖）")
    print()

    # ── V3.0.1: 注册到全局项目表 ──
    from .upgrade import _register_project
    from ..utils import get_source_version
    _register_project(project_root, get_source_version() or "3.0.1")

    # ── V3.0.1: 自动初始化 Guard + 经验 + 流程契约 ──
    _post_init_guard(project_root)
    _post_init_experiences(project_root, stdd_source)
    _post_init_constitution(project_root)
    _post_init_self_check(project_root)

    print()
    print("  开始使用:")
    print("   /stdd-understand  <需求描述>    启动新变更的需求理解阶段")
    print("   /stdd-spec                      进入规格设计阶段")
    print("   /stdd-continue                  继续执行当前变更")


def _post_init_guard(project_root: Path) -> None:
    """V3.0.1: Auto-install Guard hooks after init."""
    from .guard import cmd_guard_init as _guard_init
    import argparse as _argparse
    print("  [STDD] 自动安装 Guard...")
    for platform in ["claude-code", "opencode", "codex"]:
        try:
            args = _argparse.Namespace(platform=platform, verbose=0, dry_run=False)
            _guard_init(args)
            return  # success on first supported platform
        except SystemExit:
            continue
        except Exception:
            continue
    print("  [STDD] Guard: 未检测到支持的平台，跳过自动安装。可手动执行 stdd guard init")


def _post_init_experiences(project_root: Path, stdd_source: Path) -> None:
    """V3.0.1: Auto-pull community experiences after init."""
    from .experience import cmd_experience as _exp_cmd
    import argparse as _argparse
    print("  [STDD] 拉取社区经验库...")
    try:
        args = _argparse.Namespace(subcommand="pull", pack_name="python", verbose=0, dry_run=False)
        _exp_cmd(args)
    except SystemExit:
        pass
    except Exception:
        print("  [STDD] 社区经验拉取失败（网络不可用），可稍后手动执行 stdd experience pull")


def _post_init_constitution(project_root: Path) -> None:
    """V3.0.1: Generate STDD_CONSTITUTION.md with mandatory process contract."""
    const_path = project_root / "STDD_CONSTITUTION.md"
    if const_path.exists():
        return  # don't overwrite existing
    content = """# STDD 流程强制契约 / Process Constitution

> V3.0.1 | 本项目启用 STDD 流程管控。以下规则**不可协商、不可跳过**。
> V3.0.1 | This project enforces STDD process control. The following rules are **non-negotiable**.

## ⚠️ 核心规则 / Core Rules

### 1. 所有代码修改必须通过 STDD Change
- 新功能 / 重构 / Bug 修复 → 先 `/stdd-understand <描述>`
- **不得在没有 active change 的情况下直接编辑代码**
- Guard 会自动拦截未经授权的 Write/Edit 操作

### 2. 每个 Change 必须走完完整的 4 Phase（V3.0.5）
- Phase 1 Understand → Phase 2 Spec → Phase 3 Build → Phase 4 Deliver
- **Phase 3 (Build) 不可跳过 — 即使所有测试通过**（Build = 切片规划 + TDD 实现 + 质量验证合并）
- Build 包含：per-slice 证据链 + 失败模式检查 + test-report.md

### 3. 三道 Gate 必须用户明确确认
- Gate 1: 用户确认 proposal（范围与边界）
- Gate 2: 用户确认 design + specs（技术方案）
- Gate 3: 用户确认 test-report（质量验收）
- **不得自行判断"用户可能已经同意了"**

### 4. Agent 操作也受 STDD 管理
- 多系统协调 / 数据处理 / 部署迁移等 Agent 任务 → 同样需要走 STDD Change
- Agent 操作完成后必须执行 CP 检查点验证（agent verify）

### 5. TDD 严格执行
- RED（先写失败测试）→ GREEN（最小实现）→ REFACTOR（重构优化）
- **不得"先写代码后补测试"**
- 每个 Slice 必须通过 per-slice 验证才能进入下一个 Slice

### 6. 经验闭环
- Build 阶段发现的失败模式自动记录到 `.stdd/experiences/`
- Phase 4 (Deliver) 自动上传经验到社区 + 同步知识图谱
- 每次 Phase 3 (Build) 开始前加载经验库预防已知错误

## 🔧 常用命令

| 命令 | 用途 |
|------|------|
| `/stdd-understand <需求>` | 启动新 Change（Phase 1） |
| `/stdd-spec` | 进入规格设计（Phase 2） |
| `/stdd-continue` | 继续执行当前 Change |
| `stdd status` | 查看当前 Change 状态 + Guard 状态 |
| `stdd guard status` | 查看 Guard 运行状态 |
"""
    const_path.write_text(content, encoding="utf-8")
    print("  [STDD] STDD_CONSTITUTION.md 已生成（强制性流程契约）")


def _post_init_self_check(project_root: Path) -> None:
    """V3.0.1: Self-check after init to verify Guard + experiences are ready."""
    print()
    print("  [STDD] 初始化自检:")
    # Check Guard
    from ..utils import read_config
    settings_file = project_root / ".claude" / "settings.local.json"
    if settings_file.exists():
        import json
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {}).get("PreToolUse", [])
            guard_active = any("stdd guard" in str(h) for h in hooks)
            print(f"    Guard: {'✅ 已激活' if guard_active else '⚠️ 未安装（手动执行: stdd guard init）'}")
        except Exception:
            print("    Guard: ⚠️ 配置文件读取失败")
    else:
        print("    Guard: ⚠️ 未检测到 Claude Code 配置（其他平台请手动安装: stdd guard init）")
    # Check experiences
    exp_dir = project_root / ".stdd" / "experiences"
    exp_count = len(list(exp_dir.glob("EXP-*.md"))) if exp_dir.exists() else 0
    print(f"    经验库: {'✅ ' + str(exp_count) + ' 条' if exp_count > 0 else '⚠️ 空（手动拉取: stdd experience pull）'}")
    print(f"    Agent验证: ✅ agent_tests/ 已创建")
