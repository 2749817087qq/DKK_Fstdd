import argparse
import sys
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# change-isolation（2026-09-25-new-isolate-flag）
# 隔离形态：none = 与主工作区共享（默认）/ worktree = 独立工作树 / branch = 独立分支
# ---------------------------------------------------------------------------

_ISOLATE_MODES = ("none", "worktree", "branch")
_DEFAULT_ISOLATE_MODE = "none"


def _load_isolation_config(project_root: Path) -> dict:
    """读取 .fstdd/config.d/project.yaml 的 `isolation` 块。

    **不抛异常**：文件缺失 / YAML 不可解析 / 结构不符，一律返回 {}，
    由调用方回落到保守默认值 `none`（见 _resolve_isolate_mode）。
    """
    cfg_path = project_root / ".fstdd" / "config.d" / "project.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return {}
    if not isinstance(data, dict):
        return {}
    block = data.get("isolation")
    return block if isinstance(block, dict) else {}


def _resolve_isolate_mode(args: argparse.Namespace, project_root: Path) -> str:
    """解析隔离形态：显式参数 > 项目配置 > `none`。

    回落方向是**锁死的**：配置不可读 / 取值非法时回落到 `none`，**绝不**回落到
    `worktree` —— 否则一个坏 YAML 会让 `stdd new` 开始悄悄往用户仓库外建 worktree。
    """
    explicit = getattr(args, "isolate", None)
    if explicit in _ISOLATE_MODES:
        return explicit
    configured = _load_isolation_config(project_root).get("default")
    if isinstance(configured, str) and configured.strip() in _ISOLATE_MODES:
        return configured.strip()
    return _DEFAULT_ISOLATE_MODE


def _print_isolation_hint(mode: str, raw_name: str) -> None:
    """打印**一行**隔离提示（当前形态 + 如需隔离的完整命令）。零交互、不阻塞。"""
    if mode == "worktree":
        print("  💡 隔离形态: worktree（独立工作树，主工作区不受本 change 影响）")
    elif mode == "branch":
        print("  💡 隔离形态: branch（独立分支，工作区仍共享）")
    else:
        print(f"  💡 隔离形态: none（与主工作区共享）｜如需隔离："
              f"stdd new {raw_name} --isolate worktree")


_DEFAULT_BRANCH_PREFIX = "fstdd/"


def _git_worktree_root(project_root: Path):
    """返回项目根所在 git 工作树的顶层目录；非 git 仓 / git 不可用 ⇒ None。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=str(project_root),
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    top = (result.stdout or "").strip()
    return Path(top) if top else None


def _branch_exists(project_root: Path, branch: str) -> bool:
    """分支是否已存在。查 refs/heads/<branch> 以避免与同名 tag 混淆。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            capture_output=True, text=True, cwd=str(project_root),
        )
    except (OSError, ValueError):
        return False
    return result.returncode == 0


def _is_worktree_dirty(project_root: Path) -> bool:
    """工作区是否有未提交改动（**含未跟踪文件**）。

    测不准时返回 True（保守判脏 ⇒ 拒绝），绝不静默放行 —— ISO-3 裁定的取向
    正是「宁可拒绝，也不制造『看起来隔离了』的假象」。
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(project_root),
        )
    except (OSError, ValueError):
        return True
    if result.returncode != 0:
        return True
    return bool((result.stdout or "").strip())


def _branch_name(project_root: Path, dir_name: str) -> str:
    """隔离分支名：<branch_prefix><dir_name> —— 显式构造，不用 git 隐式派生。"""
    prefix = _load_isolation_config(project_root).get("branch_prefix")
    if not isinstance(prefix, str) or not prefix.strip():
        prefix = _DEFAULT_BRANCH_PREFIX
    return f"{prefix.strip()}{dir_name}"


def _resolve_worktree_root(project_root: Path, dir_name: str) -> Path:
    """worktree 路径：默认在项目根**之外**，可被 isolation.worktree_root 覆盖。

    默认放仓外是刻意的：建在仓内会让 `git status` 变脏，撞上既有断言
    「工作区除 .fstdd/changes/ 外应干净」（test_a6_d_repo_worktree_clean）。
    """
    configured = _load_isolation_config(project_root).get("worktree_root")
    if isinstance(configured, str) and configured.strip():
        base = Path(configured.strip())
        if not base.is_absolute():
            base = project_root / base
        return base / dir_name
    return project_root.parent / f"{project_root.name}.worktrees" / dir_name


def _preflight_isolation(mode: str, project_root: Path, dir_name: str) -> None:
    """隔离前置检查。任一失败即非 0 退出。

    **必须早于任何 change 目录创建**：否则失败会留下半成品 change。
    顺序：git 工作树 → 分支/路径冲突 → （branch 模式）脏树。
    失败路径**不执行任何删除** —— 清理命令只打印，由用户自己执行。
    """
    if mode == "none":
        return

    if _git_worktree_root(project_root) is None:
        print(f"  ❌ --isolate {mode} 需要当前目录位于 git 工作树内")
        print("     当前目录不是 git 仓库（或 git 不可用）")
        print("     如不需要隔离，请改用：--isolate none")
        sys.exit(1)

    if mode == "worktree":
        branch = _branch_name(project_root, dir_name)
        if _branch_exists(project_root, branch):
            print(f"  ❌ 分支已存在：{branch}")
            print(f"     请先处理后再试，例如：git branch -D {branch}")
            sys.exit(1)
        wt_path = _resolve_worktree_root(project_root, dir_name)
        if wt_path.exists():
            print(f"  ❌ worktree 目标路径已存在：{wt_path}")
            print("     本工具不会删除既有路径。请自行确认后清理：")
            print(f"       git worktree remove --force {wt_path}   # 若已注册为 worktree")
            print(f"       rm -rf {wt_path}                        # 否则")
            sys.exit(1)

    elif mode == "branch":
        if _is_worktree_dirty(project_root):
            print("  ❌ 工作区有未提交改动（含未跟踪文件），拒绝切换分支")
            print("     原因：git checkout -b 会把未提交改动带到新分支，")
            print("           使本 change 的提交混入无关改动（ISO-3 裁定）")
            print("     请二选一：先 commit / stash 这些改动，或改用 --isolate worktree")
            sys.exit(1)


def _create_worktree(project_root: Path, path: Path, branch: str) -> bool:
    """`git worktree add -b <branch> <path> HEAD`。成功 ⇒ True。

    三处刻意写死，都是为了避免「隐式派生」带来的不确定性：
      * `-b <branch>` 显式给分支名 —— 不用 git 的路径派生（那会产生
        `<dir>-explore` 之类的名字，见 TC-ISO-004）
      * `HEAD` 显式给起点 —— 不受远端默认分支 / `worktree.guessRemote` 影响
      * 实测 `git worktree add` 会**自行创建多级父目录**，无需预建 `mkdir -p`

    失败时**不做任何清理**：只回报 False，由调用方决定。这与前置检查
    「不删既有路径」的取向一致 —— 本工具不猜用户想不想删。
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(path), "HEAD"],
            capture_output=True, text=True, cwd=str(project_root),
        )
    except (OSError, ValueError) as exc:
        print(f"  ❌ git 调用失败: {type(exc).__name__}: {exc}")
        return False
    if result.returncode != 0:
        print(f"  ❌ git worktree add 失败（exit={result.returncode}）")
        for line in (result.stderr or "").strip().splitlines():
            print(f"     {line}")
        return False
    return True


def _create_branch(project_root: Path, branch: str) -> bool:
    """`git checkout -b <branch>`。成功 ⇒ True。

    **不建 worktree** —— branch 形态共享同一工作区，隔离性来自分支而非目录，
    所以 change 骨架仍落在主仓（`target_root` 保持 `project_root`）。
    前置检查已保证工作区干净（ISO-3 裁定），因此 checkout 不会把无关改动带过来。
    """
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", branch],
            capture_output=True, text=True, cwd=str(project_root),
        )
    except (OSError, ValueError) as exc:
        print(f"  ❌ git 调用失败: {type(exc).__name__}: {exc}")
        return False
    if result.returncode != 0:
        print(f"  ❌ git checkout -b 失败（exit={result.returncode}）")
        for line in (result.stderr or "").strip().splitlines():
            print(f"     {line}")
        return False
    return True


# 宿主门禁注册文件（相对项目根）。两份都是「未跟踪」的常见形态 ——
# 正因如此才需要显式复制，见 _propagate_guard_hooks。
_GUARD_HOOK_FILES = (
    Path(".claude") / "settings.local.json",
    Path(".codebuddy") / "settings.local.json",
)


def _propagate_guard_hooks(project_root: Path, worktree_path: Path) -> bool:
    """把主仓的门禁 hook 注册文件整份复制进新 worktree。返回「是否至少复制了一个」。

    **为什么必须做**：`git worktree add` 只签出**已跟踪**文件，而 hook 注册
    （`.claude/settings.local.json` / `.codebuddy/settings.local.json`）通常被
    gitignore —— 于是新 worktree 里**没有任何门禁**，隔离就成了绕过 Guard 的通道。
    这正是裁定 ISO-1 要堵的口子。

    **文件级整份拷贝，不解析结构**：这两个文件是宿主（Claude Code / CodeBuddy）
    的私有格式，解析会让 FSTDD 与宿主版本耦合；整份拷贝语义最直白，宿主日后
    增删字段也自动跟随。

    源文件一个都不存在时返回 False（调用方据此输出告警），但**不改变 exit code**：
    门禁缺失是可继续的降级，不是失败 —— 否则尚未接入 Guard 的项目里
    `--isolate worktree` 会完全不可用。**但绝不能静默**。
    """
    copied = False
    for rel in _GUARD_HOOK_FILES:
        src = project_root / rel
        if not src.is_file():
            continue
        dst = worktree_path / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except OSError as exc:
            # 单个文件复制失败不中断：另一个宿主可能仍可复制成功。
            print(f"  ⚠️ 门禁 hook 复制失败 {rel}: {type(exc).__name__}: {exc}")
            continue
        copied = True
    return copied


def cmd_new(args: argparse.Namespace) -> None:
    from ..utils import get_logger
    logger = get_logger()

    project_root = Path.cwd()
    change_name = args.name
    isolate_mode = _resolve_isolate_mode(args, project_root)

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
    # 主仓口径的落点 —— 仅用于「防重复建 change」。真正的落点在隔离环境确定后由
    # target_root 决定（worktree 模式下落在 worktree 内，见下方隔离创建段）。
    main_change_dir = project_root / ".fstdd" / "changes" / dir_name

    if main_change_dir.exists():
        print(f" Change 目录已存在: .fstdd/changes/{dir_name}")
        sys.exit(1)

    dry_run = getattr(args, "dry_run", False)
    if dry_run:
        print(" [DRY-RUN] 将执行以下操作:")
        if isolate_mode == "worktree":
            wt_preview = _resolve_worktree_root(project_root, dir_name)
            print(f"   创建隔离 worktree: {wt_preview}")
            print(f"     分支: {_branch_name(project_root, dir_name)}")
            print(f"   创建 change 目录: {wt_preview}/.fstdd/changes/{dir_name}")
        else:
            print(f"   创建 change 目录: .fstdd/changes/{dir_name}")
        print(f"   创建 specs 子目录: .fstdd/changes/{dir_name}/specs")
        print(f"   复制模板: design.md, test-plan.md")
        print(f"   Scaffold Canonical YAML: canonical/proposals/, specs/code/ (YAML-first)")
        print(f"   创建状态文件: .fstdd/changes/{dir_name}/.fstdd.yaml")
        print(f"   状态版本: 3.0, 状态: active")
        print(" [DRY-RUN] 文件系统未发生变化")
        return

    # V3.0.7: 隔离前置检查 —— 必须早于**任何** change 目录创建（SC-006/007/008）。
    _preflight_isolation(isolate_mode, project_root, dir_name)

    # V3.0.7: 创建隔离环境 —— **顺序锁：先隔离、后脚手架**（SC-001/005/009/010）。
    # 反过来会先把骨架铺在主仓、再发现隔离未生效（或需要搬移半成品）。
    target_root = project_root
    if isolate_mode == "worktree":
        wt_path = _resolve_worktree_root(project_root, dir_name)
        branch = _branch_name(project_root, dir_name)
        if not _create_worktree(project_root, wt_path, branch):
            print("  ❌ 隔离 worktree 创建失败 —— 未创建任何 change 骨架")
            sys.exit(1)
        target_root = wt_path
        print(f"  🔀 隔离 worktree 已创建: {wt_path}")
        print(f"     分支: {branch}")
        # 裁定 ISO-1：worktree 内必须保持门禁有效，否则隔离 = 绕过 Guard 的通道。
        # 必须在 worktree 建好之后立刻做 —— 晚于此处的任何失败都会留下无门禁的 worktree。
        if _propagate_guard_hooks(project_root, wt_path):
            print("     ✅ 门禁 hook 已随行（.claude / .codebuddy）")
        else:
            print("     ⚠️ 未发现门禁 hook 注册文件（.claude/settings.local.json 等）")
            print("        该 worktree 内 Guard 门禁**不会生效** —— 请确认这是预期行为")
    elif isolate_mode == "branch":
        branch = _branch_name(project_root, dir_name)
        if not _create_branch(project_root, branch):
            print("  ❌ 隔离分支创建失败 —— 未创建任何 change 骨架")
            sys.exit(1)
        # 落点**不变**：branch 形态共享工作区，骨架仍建在主仓（target_root 保持）。
        print(f"  🔀 隔离分支已创建: {branch}")

    change_dir = target_root / ".fstdd" / "changes" / dir_name
    (change_dir / "specs").mkdir(parents=True)

    # V3.0.5 (YAML-first): proposal.md 不再复制 — Gate 1 时从 canonical YAML 自动生成。
    # 裁定 ISO-4：模板源**始终取主仓**（project_root），不是 target_root。
    # 理由：模板是**项目级**资源，worktree 只是 change 的落点。且 worktree 是 HEAD 的
    # 签出，主仓里**未提交**的模板不会随行 —— 若源改取 target_root，这类模板会被
    # `if tmpl.exists()` 静默跳过，产出缺 design.md / test-plan.md 的半成品骨架。
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
            # 隔离落点：canonical 骨架必须建在 target_root（worktree 模式下 = worktree）。
            # canon 侧以 `getattr(args, "project_root", None) or Path.cwd()` 读取；
            # 此处不传会回落 cwd（= 主仓），导致「worktree 建了、骨架却留主仓」的割裂。
            project_root=target_root,
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

    logger.info("Change 创建完成: .fstdd/changes/%s", dir_name)
    print(f" Change 创建完成: .fstdd/changes/{dir_name}")
    print(f"   模板已就绪: design.md, test-plan.md")
    print(f"   Canonical YAML: canonical/proposals/{dir_name}.yaml + specs/code/ (YAML-first)")
    print(f"   proposal.md 将在 Gate 1 自动生成")
    print(f"   状态文件: .fstdd.yaml")

    # 终态校验：不看 canon_init 是否抛异常，直接验端状态 —— canonical 产物是否真的在盘上。
    # 异常被上面吃掉、或 canon_init 正常退出但漏写文件，都会在这里暴露。
    canon_root = target_root / ".fstdd" / "changes" / dir_name / "canonical"
    if canon_ok and not canon_root.exists():
        canon_ok = False
        print(f" ⚠️ 终态校验失败: canonical/ 目录不存在于 .fstdd/changes/{dir_name}/")
        print(f"   change 可用，但缺 YAML-first 骨架 —— 请手动执行：stdd canon init --change {dir_name}")
    print(f"   Canonical 终态: {'✅ 就绪' if canon_ok else '❌ 缺失（见上方告警）'}")

    # V3.0.7: 隔离可见性 —— 一行提示，零交互（SC-011 / SC-012）。
    # 注意：本处只在**实际建出骨架之后**打印，因此提示中的形态必定是已生效的形态。
    _print_isolation_hint(isolate_mode, args.name)

    print()
    print("  下一步:")
    print(f"   /fstdd-understand  开始需求理解阶段")
