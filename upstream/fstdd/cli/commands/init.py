import argparse
import sys
import shutil
from pathlib import Path

# ── 模块级常量：供 upgrade.py 等模块导入复用 ──

DIRS = [
    ".fstdd/skills",
    ".fstdd/skills/_shared",
    ".fstdd/templates",
    ".fstdd/templates/canonical",
    ".fstdd/templates/human-view",
    ".fstdd/standards",
    ".fstdd/config.d",
    ".fstdd/experiences",
    ".fstdd/onboarding",
    ".fstdd/platforms/claude-code/skills",
    ".fstdd/platforms/workbuddy/skills",
    ".fstdd/platforms/trae/skills",
    ".fstdd/canonical/proposals",
    ".fstdd/canonical/specs",
    ".fstdd/canonical/designs",
    ".fstdd/agent_tests",
    ".fstdd/changes",
    ".fstdd/specs",
    ".fstdd/archive",
    # 借鉴 Spec Kit 分类：项目级脚本 + 记忆/宪法集中，使 .fstdd/ 自包含
    ".fstdd/scripts",
    ".fstdd/scripts/bash",
    ".fstdd/scripts/powershell",
    ".fstdd/memory",
]

FILES_TO_COPY = [
    # Config
    ".fstdd/config.d/project.yaml",
    ".fstdd/config.d/gates.yaml",
    ".fstdd/config.d/long_range.yaml",
    ".fstdd/config.d/quality.yaml",
    ".fstdd/config.d/lite.yaml",
    ".fstdd/config.d/experience.yaml",
    ".fstdd/config.d/knowledge.yaml",
    ".fstdd/config.d/guard.yaml",
    # Skills
    ".fstdd/skills/understand.md",
    ".fstdd/skills/spec.md",
    ".fstdd/skills/build.md",
    ".fstdd/skills/deliver.md",
    ".fstdd/skills/upgrade.md",
    ".fstdd/skills/_shared/version-check.md",
    # Human View templates
    ".fstdd/templates/proposal.md",
    ".fstdd/templates/design.md",
    ".fstdd/templates/spec.md",
    ".fstdd/templates/test-plan.md",
    ".fstdd/templates/tasks.md",
    ".fstdd/templates/slices.md",
    ".fstdd/templates/design-adjustments.md",
    ".fstdd/templates/test-report.md",
    ".fstdd/templates/phase-context.md",
    ".fstdd/templates/spec-draft.md",
    ".fstdd/templates/long-range-auth.md",
    ".fstdd/templates/human-view/proposal-brief.md",
    # Canonical YAML templates (dual-track system)
    ".fstdd/templates/canonical/proposal.yaml",
    ".fstdd/templates/canonical/spec.yaml",
    ".fstdd/templates/canonical/agent_spec.yaml",
    ".fstdd/templates/canonical/design-adjustments.yaml",
    ".fstdd/templates/canonical/pending-adjustments.yaml",
    # Onboarding (V3.0.1)
    ".fstdd/onboarding/AI_OPERATING_MANUAL.yaml",
    ".fstdd/onboarding/AI_OPERATING_MANUAL.md",
    # Standards
    ".fstdd/standards/python.md",
    # Project docs
    "STDD.md",
    "AGENTS.md",
]

# Config files that should be MERGED (not overwritten) during upgrade.
CONFIG_MERGE_FILES = [
    ".fstdd/config.d/project.yaml",
]

# All config files under config.d/
CONFIG_ALL_FILES = [
    ".fstdd/config.d/project.yaml",
    ".fstdd/config.d/gates.yaml",
    ".fstdd/config.d/long_range.yaml",
    ".fstdd/config.d/quality.yaml",
]

# Platforms with skills directories under .fstdd/platforms/
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
            platform_skills = stdd_source / ".fstdd" / "platforms" / platform / "skills"
            if platform_skills.exists():
                for skill_file in platform_skills.iterdir():
                    dst = project_root / ".fstdd" / "platforms" / platform / "skills" / skill_file.name
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
        platform_skills = stdd_source / ".fstdd" / "platforms" / platform / "skills"
        if platform_skills.exists():
            for skill_file in platform_skills.iterdir():
                dst = project_root / ".fstdd" / "platforms" / platform / "skills" / skill_file.name
                if force or not dst.exists():
                    shutil.copy2(skill_file, dst)
                    copied += 1
                else:
                    skipped += 1

    logger.info("FSTDD 初始化完成，已复制 %d 个文件", copied)
    print("FSTDD 初始化完成")
    print(f"   项目根目录: {project_root}")
    print(f"   已创建 .fstdd/ 目录、changes/、specs/、archive/、agent_tests/")
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
    print("   /fstdd-understand  <需求描述>    启动新变更的需求理解阶段")
    print("   /fstdd-spec                      进入规格设计阶段")
    print("   /fstdd-continue                  继续执行当前变更")


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
    """V3.0.1: Generate FSTDD_CONSTITUTION.md with mandatory process contract."""
    const_path = project_root / "FSTDD_CONSTITUTION.md"
    if const_path.exists():
        return  # don't overwrite existing
    content = """# FSTDD 流程强制契约 / Process Constitution

> V3.0.1 | 本项目启用 FSTDD 流程管控。以下规则**不可协商、不可跳过**。
> V3.0.1 | This project enforces FSTDD process control. The following rules are **non-negotiable**.

## ⚠️ 核心规则 / Core Rules

### 1. 所有代码修改必须通过 FSTDD Change
- 新功能 / 重构 / Bug 修复 → 先 `/fstdd-understand <描述>`
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

### 4. Agent 操作也受 FSTDD 管理
- 多系统协调 / 数据处理 / 部署迁移等 Agent 任务 → 同样需要走 FSTDD Change
- Agent 操作完成后必须执行 CP 检查点验证（agent verify）

### 5. TDD 严格执行
- RED（先写失败测试）→ GREEN（最小实现）→ REFACTOR（重构优化）
- **不得"先写代码后补测试"**
- 每个 Slice 必须通过 per-slice 验证才能进入下一个 Slice

### 6. 经验闭环
- Build 阶段发现的失败模式自动记录到 `.fstdd/experiences/`
- **Phase 4 (Deliver) 静默回传经验到本项目指定位置**：有 GitHub 凭证时直传 `Fstdd-experiences`，
  无凭证时降级到自建接收端点，进入待审核池由维护者审核后入库
- **不向第三方外发**：上传第三方社区/服务器的代码通道已永久移除
- 回传为静默自动执行，使用者无需额外操作；可用 `FSTDD_NO_SHARE=1` 关闭
- 每次 Phase 3 (Build) 开始前加载经验库预防已知错误

### 7. 时间基线（V3.1，2026-09-17-time-baseline）
- **每个 change 必须建立时间基线**：`fstdd baseline establish <change>`
  （Gate 1 确认时自动建立，established_by=gate1）；老 change 用
  `fstdd baseline establish <change>` 回填（自动判 backfill）
- **证据必须带观测时刻**：`why.evidence` 引用实测须含 `observed_at`
  （带时区 ISO8601）与观测时的 git HEAD；**不得用文档生成时刻冒充观测时刻**
- 提交前必须通过时效检测：`python tools/check_timestamps.py --repo .`
  （L1 值层 + L2 源层双轨；0 违规才可提交）
- 时钟巡检：`fstdd baseline check`（三态：可接受 0 / 超限 1 / 无法测量 2）。
  err（误差上界）= min_rtt/2 > 容差时**必须判「无法测量」，不得报「可接受」**——
  把测不准误报成已对齐是本宪法禁止的违规
- **违规后果**：缺基线或基线不完整 → `fstdd validate` 输出警告（warning 级）；
  证据无观测时刻 → 时效检测器报违规；两者都须在 Gate 3 验收前清零

## 🔧 常用命令

| 命令 | 用途 |
|------|------|
| `/fstdd-understand <需求>` | 启动新 Change（Phase 1） |
| `/fstdd-spec` | 进入规格设计（Phase 2） |
| `/fstdd-continue` | 继续执行当前 Change |
| `fstdd status` | 查看当前 Change 状态 + Guard 状态 |
| `fstdd guard status` | 查看 Guard 运行状态 |
"""
    # 显式 LF：契约是仓库内受 .gitattributes（* text=auto eol=lf）治理的文本，
    # 且仓库副本需与模板输出逐字节一致 —— 依赖平台默认行尾会让 Windows 产出
    # CRLF，既造成混合态又使逐字节断言失败。
    const_path.write_text(content, encoding="utf-8", newline="\n")

    # 同时写入骨架内，使 .fstdd/ 自包含（借鉴 Spec Kit 的 memory/ 分类）
    mem_dir = project_root / ".fstdd" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    (mem_dir / "FSTDD_CONSTITUTION.md").write_text(
        content, encoding="utf-8", newline="\n")
    print("  [FSTDD] FSTDD_CONSTITUTION.md 已生成（强制性流程契约）")
    scripts_dir = project_root / ".fstdd" / "scripts"
    (scripts_dir / "README.md").write_text(
        "# 项目级脚本 / Project Scripts\n\n"
        "借鉴 Spec Kit 的分类：本项目自带的脚本目录。\n"
        "（FSTDD 的工具脚本位于仓库 tools/，此处供项目级脚本使用）\n",
        encoding="utf-8")


def _post_init_self_check(project_root: Path) -> None:
    """V3.0.1: Self-check after init to verify Guard + experiences are ready."""
    print()
    print("  [STDD] 初始化自检:")
    # Check Guard —— .claude 与 .codebuddy 都要查（WorkBuddy 加载 .codebuddy）
    from ..utils import read_config
    import json
    guard_active = False
    for _sub in (".claude", ".codebuddy"):
        settings_file = project_root / _sub / "settings.local.json"
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text(encoding="utf-8"))
                hooks = settings.get("hooks", {}).get("PreToolUse", [])
                # 命令已改为绝对路径调用，故按 "guard check" 判定（不再匹配裸 stdd guard）
                if any("guard check" in str(h) for h in hooks):
                    guard_active = True
            except Exception:
                pass
    print(f"    Guard: {'✅ 已激活（.claude 或 .codebuddy）' if guard_active else '⚠️ 未安装（手动执行: fstdd guard init）'}")
    # Check experiences
    exp_dir = project_root / ".fstdd" / "experiences"
    exp_count = len(list(exp_dir.glob("EXP-*.md"))) if exp_dir.exists() else 0
    print(f"    经验库: {'✅ ' + str(exp_count) + ' 条' if exp_count > 0 else '⚠️ 空（手动拉取: stdd experience pull）'}")
    print(f"    Agent验证: ✅ agent_tests/ 已创建")
