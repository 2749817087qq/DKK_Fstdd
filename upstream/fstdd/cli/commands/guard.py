"""STDD guard CLI — intelligent enforcement gate (V3.0.5, 4-phase).

V2.9.4: Phase integrity checks prevent bypass via manual YAML editing.
Guard now verifies that the current phase was legitimately reached
(previous phases completed, gates confirmed) before allowing edits.
Also supports task_type-aware phase permissions (documentation tasks
need to edit during spec/build phases).

V3.0.5: Phase model collapsed to understand→spec→build→deliver. Legacy
6-phase states (slice/verify) are normalized via LEGACY_PHASE_MAP.
"""

import sys
import argparse
from pathlib import Path

from .phase_constants import (
    PHASE_ORDER as _PHASE_ORDER,
    GATE_PHASES as _GATE_PHASES_DICT,
    EDITABLE_PHASES_BY_TYPE as _EDITABLE_PHASES_BY_TYPE,
    EDITABLE_PHASES as _EDITABLE_PHASES,
    LEGACY_PHASE_MAP,
)

# Phases that require gate confirmation (V3.0.5: Gate 3 = build)
_GATE_PHASES = set(_GATE_PHASES_DICT.keys())

# V2.9.3: Scope classification
#    micro  → batch is ideal
#    small  → batch ok, but monitor
#    medium → batch not recommended, suggest full STDD
#    large  → batch blocked, force full STDD
_SCOPE_MICRO = "micro"
_SCOPE_SMALL = "small"
_SCOPE_MEDIUM = "medium"
_SCOPE_LARGE = "large"

# Batch limits
_BATCH_MAX_FILES = 5       # warn if exceeded
_BATCH_MAX_FILES_HARD = 10  # block if exceeded (batch not suitable)
_BATCH_MAX_HOURS = 2        # warn if batch open longer

# Keyword signals for scope classification (V2.9.3)
# Scores: micro=1, small=2, medium=5, large=10
# Thresholds: >=20 large, >=10 medium, >=3 small, <3 micro
_MICRO_SIGNALS = [
    "修复", "fix", "bug", "热修", "hotfix", "小改",
    "typo", "改个", "补丁", "patch", "修一下", "改一下",
    "快速", "quick", "改个", "小调整",
]
_SMALL_SIGNALS = [
    "调整", "优化", "改进", "更新", "ui", "界面",
    "improve", "tweak", "update", "adjust", "enhance",
    "日志", "格式", "展示", "显示", "配置", "清理",
]
_MEDIUM_SIGNALS = [
    "重构", "refactor", "改版", "迁移", "替换", "改造",
    "feature", "添加", "增加", "新增", "模块",
    "功能", "逻辑", "数据处理", "性能",
]
_LARGE_SIGNALS = [
    "重写", "rewrite", "架构", "architecture",
    "大改", "overhaul", "子系统", "system",
    "新模块", "新增模块", "新功能",
    "api", "接口", "集成", "integration",
    "引擎", "engine", "平台", "platform",
]


def _classify_description(text: str) -> str:
    """Classify a change description into scope level.

    Returns one of: _SCOPE_MICRO, _SCOPE_SMALL, _SCOPE_MEDIUM, _SCOPE_LARGE

    Scoring: micro=1, small=2, medium=5, large=10
    Thresholds: >=20 large, >=10 medium, >=3 small, <3 micro
    """
    lower = text.lower()
    score = 0

    for kw in _MICRO_SIGNALS:
        if kw in lower:
            score += 1
    for kw in _SMALL_SIGNALS:
        if kw in lower:
            score += 2
    for kw in _MEDIUM_SIGNALS:
        if kw in lower:
            score += 5
    for kw in _LARGE_SIGNALS:
        if kw in lower:
            score += 10

    if score >= 20:
        return _SCOPE_LARGE
    elif score >= 10:
        return _SCOPE_MEDIUM
    elif score >= 3:
        return _SCOPE_SMALL
    else:
        return _SCOPE_MICRO


def _count_changed_files(project_root: Path) -> int:
    """Count files changed in the working tree (untracked not counted)."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(project_root),
            timeout=5,
        )
        if result.returncode == 0:
            files = [f for f in result.stdout.strip().split("\n") if f]
            return len(files)
        import sys as _sys
        print("  guard-warn: git diff 失败（非 git 仓库或无提交），变更计数不可用，按 0 处理",
              file=_sys.stderr)
    except Exception as e:
        import sys as _sys
        print(f"  guard-warn: git diff 异常（{type(e).__name__}），变更计数不可用，按 0 处理",
              file=_sys.stderr)
    return 0


def _check_file_type_mismatch(project_root: Path, task_type: str) -> tuple:
    """Check if modified files match the task_type.

    Returns (mismatch: bool, reason: str).
    For documentation/configuration tasks, warns if too many code files modified.
    Code tasks are universal — no mismatch possible.
    """
    if task_type == "code":
        return False, ""

    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(project_root),
            timeout=5,
        )
        if result.returncode != 0:
            import sys as _sys
            print("  guard-warn: git diff 失败，task_type 占比检测跳过", file=_sys.stderr)
            return False, ""

        files = [f for f in result.stdout.strip().split("\n") if f]
        code_files = [f for f in files if f.endswith(('.py', '.go', '.java', '.rs', '.ts', '.js'))]
        code_ratio = len(code_files) / len(files) if files else 0

        if len(code_files) >= 3 and code_ratio > 0.5:
            return True, (
                f"⚠️  task_type='{task_type}' 但已修改 {len(code_files)} 个代码文件 "
                f"({int(code_ratio * 100)}%)。建议转为 code change 或新开 code change 管理代码修改。"
            )
    except Exception as e:
        import sys as _sys
        print(f"  guard-warn: task_type 占比统计异常（{type(e).__name__}），检测跳过", file=_sys.stderr)
    return False, ""


def _count_batch_files_so_far(project_root: Path) -> int:
    """Estimate files touched in current batch by counting tracked changes."""
    return _count_changed_files(project_root)


def _find_open_batch(project_root: Path):
    """Find the currently open (unclosed) batch. Returns (batch_dir, batch_data) or (None, None)."""
    import yaml as _yaml
    batches_dir = project_root / ".fstdd" / "changes" / "_batch"
    if not batches_dir.is_dir():
        return None, None

    for batch_dir in sorted(
        [d for d in batches_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    ):
        stdd_yaml = batch_dir / ".fstdd.yaml"
        if stdd_yaml.exists():
            data = _yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
            if data and not data.get("closed_at"):
                return batch_dir, data
    return None, None


_ZOMBIE_DAYS = 7  # V3.0.1: changes inactive > 7 days are considered zombie

def _utc(dt):
    """naive -> UTC 归一（写入方即 UTC，D2 决策）；aware 原样返回。"""
    from datetime import timezone as _tz
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=_tz.utc)


def _is_zombie(change_dir: Path) -> bool:
    """Check if a change is zombie (stale > ZOMBIE_DAYS without phase progress)."""
    import yaml as _yaml
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    stdd_yaml = change_dir / ".fstdd.yaml"
    if not stdd_yaml.exists():
        return False
    data = _yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
    last_mod = data.get("last_modified", "")
    if not last_mod:
        return False
    try:
        lm = _utc(_dt.fromisoformat(last_mod))
        if _dt.now(_tz.utc) - lm > _td(days=_ZOMBIE_DAYS):
            return True
    except Exception:
        import sys as _sys
        print(f"  guard-warn: {change_dir.name} last_modified 不可解析，僵尸判定跳过",
              file=_sys.stderr)
    return False


def _find_active_change(project_root: Path) -> tuple:
    """Find the most recent active change. Returns (change_dir, phase) or (None, None).
    V3.0.1: Zombie changes (stale > 7 days) are skipped."""
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.is_dir():
        return None, None

    for change_dir in sorted(
        [d for d in changes_dir.iterdir() if d.is_dir() and d.name != "_batch"],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    ):
        stdd_yaml = change_dir / ".fstdd.yaml"
        if stdd_yaml.exists():
            import yaml
            data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
            if data:
                if _is_zombie(change_dir):
                    continue  # skip zombie
                status = data.get("status", "")
                phase = data.get("current_phase") or data.get("phase", "")
                # V3.0.5: normalize legacy 6-phase states (slice/verify → build)
                norm_phase = LEGACY_PHASE_MAP.get(phase, phase)
                if status in ("active", "in_progress", "pending") or norm_phase in (
                    "understand", "spec", "build", "deliver"
                ):
                    return change_dir, norm_phase

    # V3.0.5: batch pipeline — open batch 处于 build 阶段时，返回活跃子 change
    #（子 change 继承批级 Gate 1/2，current_phase=build，guard 据此放行代码编辑）
    batch_dir, batch_data = _find_open_batch(project_root)
    if batch_dir and batch_data:
        bphase = batch_data.get("current_phase", "")
        if bphase == "build":
            children_dir = batch_dir / "changes"
            if children_dir.is_dir():
                for child_dir in sorted(
                    [d for d in children_dir.iterdir() if d.is_dir()],
                    key=lambda d: d.stat().st_mtime,
                    reverse=True,
                ):
                    stdd_yaml = child_dir / ".fstdd.yaml"
                    if stdd_yaml.exists():
                        import yaml
                        data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8"))
                        if data and data.get("status") in ("active", "in_progress", "pending"):
                            child_phase = data.get("current_phase") or "build"
                            return child_dir, child_phase
    return None, None


def _read_hook_input() -> tuple:
    """V3.0.5: 读 Claude Code PreToolUse hook 的 stdin JSON。

    Hook JSON 形状:
        {"tool_name": "Edit|Write", "tool_input": {"file_path": "...", "content"/"new_string": "..."}}
    解析失败 → (None, None)（fail-open，不误伤编辑）。
    """
    import json
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None, None
        data = json.loads(raw)
        tool_input = data.get("tool_input") or {}
        file_path = tool_input.get("file_path", "") or ""
        content = tool_input.get("content") or tool_input.get("new_string") or ""
        return file_path, content
    except Exception:
        return None, None


def _is_gate_token_path(file_path: str) -> bool:
    """V3.0.5: GATE<N>_APPROVED token 文件 — 必须人工创建，AI 不得写入。"""
    name = Path(file_path).name
    return name in ("GATE1_APPROVED", "GATE2_APPROVED", "GATE3_APPROVED")


def _is_state_confirmation_edit(project_root: Path, file_path: str, content: str) -> bool:
    """V3.0.5: .fstdd.yaml 内容含 confirmed_at/confirmed_by → 阻断直接篡改确认字段。

    确认字段必须走 'stdd gate approve' CLI 通道（写审计链），不许 AI 用 Edit/Write 直接篡改。
    拿不到内容（content 空）→ 不阻断（fail-open）。
    """
    if not file_path.endswith(".fstdd.yaml"):
        return False
    if not content:
        return False
    return "confirmed_at" in content or "confirmed_by" in content


def _is_workflow_artifact(project_root: Path, change_dir: Path, file_path: str) -> bool:
    """V3.0.5: understand/spec 阶段放行的 YAML-first 流程产出物。

    change 内 canonical/ 下任何文件 + design.md/test-plan.md/proposal.md + specs/ 下 spec.md。
    .fstdd.yaml 由 CLI 管理，不算流程产出物（不放行，避免旁路）。
    """
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = project_root / p
        try:
            rel = p.relative_to(change_dir)
        except ValueError:
            return False
        parts = rel.parts
        if "canonical" in parts:
            return True
        if rel.name in ("design.md", "test-plan.md", "proposal.md"):
            return True
        if "specs" in parts and rel.name == "spec.md":
            return True
    except Exception:
        return False
    return False


def _guard_report(args: argparse.Namespace, msg: str) -> None:
    """Print a guard message (stderr for claude-code platform, stdout otherwise)."""
    import sys as _sys
    target = _sys.stderr if getattr(args, "platform", "cli") == "claude-code" else None
    print(f"  [STDD Guard] {msg}", file=target)


def _check_phase_integrity(data: dict, current_phase: str) -> tuple:
    """Check that the current phase was legitimately reached.

    Returns (ok: bool, reason: str).
    A phase is legitimate if all previous phases have status=="completed"
    AND all required gate phases have confirmed_at timestamps.
    """
    if current_phase not in _PHASE_ORDER:
        return False, f"Unknown phase: {current_phase}"

    idx = _PHASE_ORDER.index(current_phase)
    phases = data.get("phases", {})

    # Check all previous phases are completed
    for i in range(idx):
        prev = _PHASE_ORDER[i]
        prev_status = phases.get(prev, {}).get("status", "pending")
        if prev_status != "completed":
            return False, (
                f"Phase 完整性异常：当前 phase='{current_phase}' 但 "
                f"Phase '{prev}' 状态为 '{prev_status}'（应为 'completed'）。"
                " 请用 'stdd phase advance' 逐步推进，不要手动修改 .fstdd.yaml。"
            )

    # Check required gate phases have confirmed_at
    for gp in _GATE_PHASES:
        gp_idx = _PHASE_ORDER.index(gp)
        if gp_idx < idx:  # this gate should have been passed
            gp_data = phases.get(gp, {})
            if not gp_data.get("confirmed_at"):
                gate_label = _GATE_PHASES_DICT.get(gp, f"Gate {gp_idx + 1}")
                return False, (
                    f"Gate 缺失：Phase '{gp}' 经过了 Gate ({gate_label})"
                    " 但未确认 (confirmed_at 为空)。"
                    " 请先完成 Gate 确认。"
                )

    return True, ""


# ---- V2.9.3: Scope assessment & recommendation ----

def _assess_and_recommend(project_root: Path,
                          batch_dir=None,
                          batch_data: dict = None,
                          enforce: bool = True) -> dict:
    """Assess current change scope and return recommendation.

    Returns dict with keys:
        allow: bool          -- whether to allow the edit
        mode: str            -- recommended mode (batch / full-stdd)
        scope: str           -- classified scope level
        reason: str          -- human-readable explanation
        file_count: int      -- files changed so far
    """
    file_count = _count_changed_files(project_root)
    result = {
        "allow": True,
        "mode": "batch",
        "scope": _SCOPE_MICRO,
        "reason": "",
        "file_count": file_count,
    }

    if not enforce:
        result["reason"] = "enforce_stdd disabled"
        return result

    # If we have an open batch, check its description and current state
    if batch_dir and batch_data:
        # V3.0.5: batch pipeline (mini-STDD) — 阶段感知
        pipeline_phase = batch_data.get("current_phase", "")
        if pipeline_phase in ("understand", "spec"):
            gate_label = "Gate 1" if pipeline_phase == "understand" else "Gate 2"
            result["mode"] = "batch-pipeline"
            result["scope"] = _SCOPE_MICRO
            result["reason"] = (
                f"批级管线阶段: {pipeline_phase}（尚未通过 {gate_label}）"
                " — 仅允许文档编辑；代码编辑请先 'stdd batch gate' 推进"
            )
            return result

        desc = batch_data.get("description", "")
        desc_scope = _classify_description(desc)
        items = batch_data.get("items", [])

        # File-count based escalation
        if file_count > _BATCH_MAX_FILES_HARD:
            result["allow"] = False
            result["mode"] = "full-stdd"
            result["scope"] = _SCOPE_LARGE
            result["reason"] = (
                f"已修改 {file_count} 个文件，超出 batch 上限 ({_BATCH_MAX_FILES_HARD})。"
                " 请用 'stdd new' 创建 full change，走完整 STDD 流程。"
            )
            return result

        if file_count > _BATCH_MAX_FILES:
            result["scope"] = _SCOPE_MEDIUM
            result["mode"] = "full-stdd"
            # Still allow, but with strong warning
            result["reason"] = (
                f"⚠️  已修改 {file_count} 个文件 (batch 推荐上限 {_BATCH_MAX_FILES})。"
                " 建议转 full STDD: 'stdd new <change-name>'"
            )
            return result

        # Scope based on batch description
        if desc_scope == _SCOPE_LARGE:
            result["allow"] = False
            result["mode"] = "full-stdd"
            result["scope"] = _SCOPE_LARGE
            result["reason"] = (
                f"batch 描述 '{desc}' 判定为大型变更。"
                " 请用 full STDD 流程: /fstdd-understand 启动。"
            )
            return result

        if desc_scope == _SCOPE_MEDIUM:
            result["scope"] = _SCOPE_MEDIUM
            result["mode"] = "full-stdd"
            result["reason"] = (
                f"⚠️  batch 描述 '{desc}' 看起来是中大型变更。"
                " batch 适合微修复；建议转为 full STDD。"
                " 继续用 batch 请确保范围可控。"
            )
            # Still allow for medium — warn but don't block
            return result

        # Small/micro — batch is fine
        result["scope"] = desc_scope
        result["mode"] = "batch"
        result["reason"] = f"batch: {batch_dir.name} ({len(items)} items)"
        return result

    # No batch and no active change → assess what's happening
    if file_count > 0:
        if file_count <= 2:
            result["scope"] = _SCOPE_MICRO
            result["reason"] = (
                f"检测到 {file_count} 个文件改动，属于微修复范围。"
                " 用 'stdd batch open \"描述\"' 快速开始。"
            )
        elif file_count <= 5:
            result["scope"] = _SCOPE_SMALL
            result["reason"] = (
                f"检测到 {file_count} 个文件改动。"
                " 微修复用 'stdd batch open \"描述\"'，较大改动用 'stdd new'。"
            )
        else:
            result["scope"] = _SCOPE_MEDIUM
            result["reason"] = (
                f"检测到 {file_count} 个文件改动，建议走 full STDD。"
                " /fstdd-understand 启动完整流程。"
            )
    else:
        result["reason"] = (
            "无 active change。微修复用 'stdd batch open \"描述\"'，"
            "新功能/重构用 '/fstdd-understand'。"
        )

    result["mode"] = "none"
    return result


# ---- CLI commands ----

def _check_phase_integrity_guard(project_root: Path) -> list[str]:
    """V3.0.1: Check if any phase has been stuck/skipped too long. Returns warnings."""
    import yaml as _yaml
    from datetime import datetime as _dt, timezone as _tz
    warnings = []
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        return warnings
    for change_dir in sorted(changes_dir.iterdir()):
        if change_dir.name.startswith("_") or change_dir.name.startswith("."):
            continue
        state_file = change_dir / ".fstdd.yaml"
        if not state_file.exists():
            continue
        state = _yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        phases = state.get("phases", {})
        # V3.0.5: build is the merged SLICE+BUILD+VERIFY phase.
        # Legacy state files may still carry verify/slice status — tolerate them.
        build_done = _is_build_complete(state)
        deliver_done = phases.get("deliver", {}).get("status") == "completed"
        spec_done = phases.get("spec", {}).get("status") == "completed"
        build_time = phases.get("build", {}).get("completed_at", "")
        spec_time = phases.get("spec", {}).get("completed_at", "")
        now = _dt.now(_tz.utc)
        if build_done and not deliver_done:
            try:
                bt = _utc(_dt.fromisoformat(build_time))
                hours = (now - bt).total_seconds() / 3600
                if hours > 24:
                    warnings.append(f"  ⚠️ {change_dir.name}: Build完成 {hours:.0f}h 但 DELIVER 尚未开始（需 Gate 3 + test-report.md）")
            except Exception:
                warnings.append(f"  ⚠️ {change_dir.name}: build completed_at 不可解析（{build_time!r}），滞后检测跳过")
        if spec_done and not build_done:
            try:
                st = _utc(_dt.fromisoformat(spec_time))
                hours = (now - st).total_seconds() / 3600
                if hours > 24:
                    warnings.append(f"  ⚠️ {change_dir.name}: Spec完成 >24h 但 Build 尚未开始")
            except Exception:
                warnings.append(f"  ⚠️ {change_dir.name}: spec completed_at 不可解析（{spec_time!r}），滞后检测跳过")
    return warnings


def _is_build_complete(state: dict) -> bool:
    """V3.0.5: Build is complete if phases.build.status == completed,
    OR legacy 6-phase state has phases.verify.status == completed."""
    phases = state.get("phases", {}) if isinstance(state, dict) else {}
    if phases.get("build", {}).get("status") == "completed":
        return True
    # Legacy: verify completion implied build completion (verify was the last
    # build-family phase in the 6-phase model).
    return phases.get("verify", {}).get("status") == "completed"


def _check_agent_ops(operation: str, project_root: Path) -> tuple[bool, str]:
    """V3.0.1: Check if agent operation should be allowed. Returns (allowed, reason)."""
    agent_tools = {"Bash", "WebFetch", "WebSearch", "Task", "NotebookEdit"}
    if operation not in agent_tools:
        return True, ""
    changes_dir = project_root / ".fstdd" / "changes"
    if not changes_dir.exists():
        return True, ""
    active_changes = [d for d in (project_root / ".fstdd" / "changes").iterdir()
                      if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
                      and (d / ".fstdd.yaml").exists()]
    if active_changes:
        return True, ""
    return False, f"  [STDD Guard] Agent 操作 ({operation}) 需要在 active change 中执行。请先 /fstdd-understand。"


def _check_inertia(project_root: Path) -> str | None:
    """V3.0.1: Check if previous changes skipped gates. Returns warning if escalation needed."""
    import yaml as _yaml
    archives = sorted((project_root / ".fstdd" / "archive").iterdir(), reverse=True) if (project_root / ".fstdd" / "archive").exists() else []
    skip_count = 0
    for arch_dir in archives[:3]:
        state_file = arch_dir / ".fstdd.yaml"
        if not state_file.exists():
            continue
        state = _yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        if not _is_build_complete(state):
            skip_count += 1
    if skip_count >= 2:
        return "  🔒 [STDD Guard] 检测到连续 2 个 Change 未完成 Build/Verify。当前 Change 已升级为硬拦截模式。"
    return None


def cmd_guard_check(args: argparse.Namespace) -> int:
    """Check if currently in a valid STDD flow.

    V2.9.3: Intelligent classification. Instead of just allow/block,
    suggests the appropriate mode (batch vs full STDD) based on scope.

    Exit codes:
        0 — allowed (batch open, or active change in editable phase)
        2 — blocked (no active flow, or batch exceeded limits)
    """
    project_root = Path.cwd()

    # V3.0.5: --hook-stdin 模式 — 读 PreToolUse hook stdin JSON 拿目标路径与内容
    hook_path = None
    hook_content = ""
    if getattr(args, "hook_stdin", False):
        hook_path, hook_content = _read_hook_input()  # 解析失败 → (None, None) fail-open

    # Check if enforce_stdd is enabled
    enforce = True
    config_file = project_root / ".fstdd" / "config.d" / "project.yaml"
    if config_file.exists():
        import yaml
        config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        enforce = config.get("enforce_stdd", True)

    if not enforce:
        return 0

    # V3.0.5: --hook-stdin 路径感知 — 硬阻断（任何 phase）：
    #   GATE token 写入必须人工；.fstdd.yaml 确认字段直接篡改必须走 CLI
    if hook_path:
        if _is_gate_token_path(hook_path):
            _guard_report(args, "🚫 GATE<N>_APPROVED token 必须由用户人工创建，AI 不得写入。")
            return 2
        if _is_state_confirmation_edit(project_root, hook_path, hook_content):
            _guard_report(args, "🚫 不得直接修改 .fstdd.yaml 确认字段；请走 'stdd gate approve' CLI 通道。")
            return 2

    # find active change
    active_dir, phase = _find_active_change(project_root)

    # Full STDD change: check phase integrity + task_type permissions
    if active_dir:
        stdd_yaml = active_dir / ".fstdd.yaml"
        if stdd_yaml.exists():
            import yaml
            change_data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
            task_type = change_data.get("task_type", "code") or "code"

            # V2.9.4: Phase integrity check
            integrity_ok, integrity_reason = _check_phase_integrity(change_data, phase)
            if not integrity_ok:
                _guard_report(args, f"🚫 {integrity_reason}")
                return 2

            # V3.0.5: --hook-stdin — understand/spec 阶段放行 YAML-first 流程产出物
            #（修 YAML-first 冲突：canonical YAML 是流程内产物，允许 Edit|Write 填写）
            if hook_path and phase in ("understand", "spec") and _is_workflow_artifact(
                project_root, active_dir, hook_path
            ):
                if not getattr(args, "quiet", False):
                    print(f"  [STDD Guard] Active change: {active_dir.name} "
                          f"(phase: {phase}) — YAML-first 流程产出物放行 ✅")
                return 0

            # V2.9.4: task_type-aware editable phases
            editable = _EDITABLE_PHASES_BY_TYPE.get(task_type, _EDITABLE_PHASES)
            if phase in editable:
                # V2.9.4: file type mismatch check for active change
                mismatch, mismatch_reason = _check_file_type_mismatch(project_root, task_type)
                if mismatch:
                    if not getattr(args, "quiet", False):
                        print(f"  [STDD Guard] {mismatch_reason}")
                    # Non-blocking warning for now

                if not getattr(args, "quiet", False):
                    print(f"  [STDD Guard] Active change: {active_dir.name} "
                          f"(phase: {phase}, task: {task_type}) — ✅")
                return 0

    # Check for open batch → intelligent assessment
    batch_dir, batch_data = _find_open_batch(project_root)
    if batch_dir:
        # V2.9.4: file type mismatch check for batch
        mismatch, mismatch_reason = _check_file_type_mismatch(project_root, "code")
        if mismatch:
            if not getattr(args, "quiet", False):
                print(f"  [STDD Guard] {mismatch_reason}")
            # Non-blocking — warn only

        assessment = _assess_and_recommend(
            project_root, batch_dir=batch_dir, batch_data=batch_data, enforce=enforce
        )
        if not assessment["allow"]:
            # Batch exceeded limits — block
            if getattr(args, "platform", "cli") == "claude-code":
                import sys as _sys
                print(f"  [STDD Guard] 🚫 Blocked: {assessment['reason']}", file=_sys.stderr)
            else:
                print(f"  [STDD Guard] 🚫 Blocked: {assessment['reason']}")
            return 2

        if not getattr(args, "quiet", False):
            icon = "⚠️" if assessment["mode"] == "full-stdd" else "✅"
            print(f"  [STDD Guard] {icon} {assessment['reason']}")
        return 0

    # No active flow at all → block with intelligent suggestion
    assessment = _assess_and_recommend(project_root, enforce=enforce)

    # Check for allow_bypass
    allow_bypass = False
    if config_file.exists():
        import yaml
        config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        allow_bypass = config.get("allow_bypass", False)

    strict = getattr(args, "strict", False)
    if allow_bypass and not strict:
        print(f"  [STDD Guard] {assessment['reason']}")
        print("  [STDD Guard] allow_bypass is enabled — allowing anyway.")
        return 0

    # Block with intelligent suggestion
    platform = getattr(args, "platform", "cli")
    if active_dir:
        reason = f"当前 Phase '{phase}' 不允许编辑。只有 Phase 3 (BUILD)/Phase 4 (DELIVER) 允许。"
    else:
        reason = assessment["reason"]

    if platform == "claude-code":
        import sys as _sys
        print("  [STDD Guard] ⛔ Blocked — 未进入可编辑流程", file=_sys.stderr)
        print(f"  [STDD Guard] {reason}", file=_sys.stderr)
    else:
        print(f"  [STDD Guard] ⛔ Blocked — {reason}")
    return 2


def cmd_guard_status(args: argparse.Namespace) -> None:
    """Display current STDD guard status with scope assessment."""
    project_root = Path.cwd()
    batch_dir, batch_data = _find_open_batch(project_root)
    active_dir, phase = _find_active_change(project_root)

    config_file = project_root / ".fstdd" / "config.d" / "project.yaml"
    enforce = True
    allow_bypass = False
    if config_file.exists():
        import yaml
        config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        enforce = config.get("enforce_stdd", True)
        allow_bypass = config.get("allow_bypass", False)

    # V2.9.3: Intelligent assessment
    assessment = _assess_and_recommend(
        project_root, batch_dir=batch_dir, batch_data=batch_data, enforce=enforce
    )

    task_type = "code"
    editable = (phase in _EDITABLE_PHASES if phase else False) or (batch_dir is not None)
    if active_dir:
        stdd_yaml = active_dir / ".fstdd.yaml"
        if stdd_yaml.exists():
            change_data = yaml.safe_load(stdd_yaml.read_text(encoding="utf-8")) or {}
            task_type = change_data.get("task_type", "code") or "code"
            editable_phases = _EDITABLE_PHASES_BY_TYPE.get(task_type, _EDITABLE_PHASES)
            editable = phase in editable_phases
            integrity_ok, _ = _check_phase_integrity(change_data, phase)

    print("  STDD Guard Status (V2.9.4 智能门禁):")
    print(f"    enforce_stdd:  {enforce}")
    print(f"    allow_bypass:  {allow_bypass}")
    print(f"    task_type:      {task_type}")
    print(f"    editable phases: {sorted(_EDITABLE_PHASES_BY_TYPE.get(task_type, _EDITABLE_PHASES))}")
    print(f"    changed files:  {assessment['file_count']}")
    print(f"    scope:          {assessment['scope']}")
    print(f"    recommended:    {assessment['mode']}")
    if active_dir and not editable:
        print(f"    phase integrity: {'✅' if integrity_ok else '❌ BYPASS DETECTED'}")

    if batch_dir:
        desc = (batch_data or {}).get("description", "") if batch_data else ""
        items = (batch_data or {}).get("items", []) if batch_data else []
        desc_scope = _classify_description(desc)
        print(f"    open batch:     {batch_dir.name} — ✅ 可编辑")
        print(f"      description:  {desc}")
        print(f"      desc scope:   {desc_scope}")
        print(f"      items:        {len(items)}")
        if assessment["mode"] == "full-stdd" and assessment["allow"]:
            print(f"      ⚠️  {assessment['reason']}")

    if active_dir:
        status = "✅ 可编辑" if editable else "🔒 只读"
        print(f"    active change:  {active_dir.name} (phase: {phase}) — {status}")
    else:
        print("    active change:  None — 🔒 只读")

    # F-2 接线：滞后检测接入状态输出（不接 guard check 热路径，D4 决策）
    lag_warnings = _check_phase_integrity_guard(project_root)
    if lag_warnings:
        print("  Phase Lag 警告:")
        for w in lag_warnings:
            print(w)


def _write_guard_settings(settings_file: Path, guard_cmd: str) -> None:
    """把 Guard hook 写入指定 settings 文件（不存在则创建）。

    guard_cmd 必须是**绝对路径**调用（裸 `stdd guard check` 不在 PATH，且已改名 fstdd），
    否则 hook 调用失败即放行，Guard 形同虚设。
    """
    import json
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except Exception:
            settings = {"permissions": {"allow": []}}
    else:
        settings = {"permissions": {"allow": []}}

    settings.setdefault("hooks", {}).setdefault("PreToolUse", [])

    if not any(
        "guard check" in str(h.get("hooks", [])) for h in settings["hooks"]["PreToolUse"]
    ):
        settings["hooks"]["PreToolUse"].append({
            "matcher": "Edit|Write",
            "hooks": [{"type": "command", "command": guard_cmd}],
        })

    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def cmd_guard_init(args: argparse.Namespace) -> None:
    """Initialize guard hooks for the current project."""
    project_root = Path.cwd()
    platform = getattr(args, "platform", "claude-code")

    if platform in ("claude-code", "codebuddy"):
        import sys as _sys
        from ..utils import get_stdd_source as _get_src

        # 关键修复（此前 Guard 形同虚设的两个原因）：
        # 1) 命令用绝对路径 —— 裸 `stdd guard check` 不在 PATH，且已改名 fstdd
        # 2) 除 .claude/ 外，还要写 .codebuddy/ —— WorkBuddy 加载 .codebuddy，
        #    只写 .claude 对 WorkBuddy 无效（Edit|Write 不会被检查）。

        _cli = _get_src() / "bin" / "fstdd"
        _guard_cmd = (
            f'"{_sys.executable}" "{_cli}" guard check '
            "--platform claude-code --hook-stdin"
        )

        for _sub in (".claude", ".codebuddy"):
            _write_guard_settings(
                project_root / _sub / "settings.local.json", _guard_cmd
            )
            print(f"  [FSTDD Guard] PreToolUse hook -> {_sub}/settings.local.json")
        print("  [STDD Guard] All Edit/Write operations will be checked.")
    elif platform == "opencode":
        _guard_init_opencode(project_root)
    elif platform == "codex":
        _guard_init_codex(project_root)
    elif platform == "aider":
        _guard_init_aider(project_root)
    else:
        print(f"  [STDD Guard] Platform '{platform}' not supported for auto-init.")
        print("  [STDD Guard] See docs for manual guard configuration.")


def _guard_init_opencode(project_root: Path) -> None:
    """Install guard hook for OpenCode platform."""
    import json
    settings_file = project_root / ".opencode" / "settings.json"
    if settings_file.exists():
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        settings = {}
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PreToolUse" not in settings["hooks"]:
        settings["hooks"]["PreToolUse"] = []
    guard_exists = any("stdd guard" in str(h.get("hooks", [])) for h in settings["hooks"]["PreToolUse"])
    if not guard_exists:
        settings["hooks"]["PreToolUse"].append({
            "matcher": "Edit|Write",
            "hooks": [{"type": "command", "command": "stdd guard check --platform opencode"}]
        })
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  [STDD Guard] OpenCode PreToolUse hook deployed.")


def _guard_init_codex(project_root: Path) -> None:
    """Install guard for Codex CLI via AGENTS.md enforcement."""
    agents_file = project_root / "AGENTS.md"
    guard_marker = "<!-- STDD-GUARD-ENABLED -->"
    if agents_file.exists():
        content = agents_file.read_text(encoding="utf-8")
        if guard_marker in content:
            print("  [STDD Guard] Codex guard already active.")
            return
        content = guard_marker + "\n\n" + content
    else:
        content = guard_marker + "\n\n# AGENTS.md — STDD Guard Active\n\nAll Edit/Write requires active STDD change.\n"
    agents_file.write_text(content, encoding="utf-8")
    print("  [STDD Guard] Codex guard marker added to AGENTS.md.")


def _guard_init_aider(project_root: Path) -> None:
    """Inject guard check into Aider's .aider.conf.yml as pre-commit."""
    aider_conf = project_root / ".aider.conf.yml"
    import yaml as _yaml
    if aider_conf.exists():
        conf = _yaml.safe_load(aider_conf.read_text(encoding="utf-8")) or {}
    else:
        conf = {}
    if "pre-commit" not in conf:
        conf["pre-commit"] = []
    pre_commit = conf["pre-commit"] if isinstance(conf["pre-commit"], list) else [conf["pre-commit"]]
    guard_cmd = "stdd guard check --platform aider"
    if guard_cmd not in str(pre_commit):
        pre_commit.append(guard_cmd)
    conf["pre-commit"] = pre_commit
    aider_conf.write_text(_yaml.dump(conf, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print("  [STDD Guard] Aider pre-commit guard injected.")


def cmd_guard_disable(args: argparse.Namespace) -> None:
    """Temporarily remove the guard hook (reversible with 'enable')."""
    project_root = Path.cwd()
    import json
    settings_file = project_root / ".claude" / "settings.local.json"

    if not settings_file.exists():
        print("  [STDD Guard] No settings.local.json found. Nothing to disable.")
        return

    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {}).get("PreToolUse", [])

    removed = False
    new_hooks = []
    for hook in hooks:
        if "stdd guard" in str(hook.get("hooks", [])):
            removed = True
        else:
            new_hooks.append(hook)

    if removed:
        settings["hooks"]["PreToolUse"] = new_hooks
        if not new_hooks:
            del settings["hooks"]["PreToolUse"]
            if not settings["hooks"]:
                del settings["hooks"]
        settings_file.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("  [STDD Guard] Hook disabled. Run 'stdd guard enable' to re-enable.")
    else:
        print("  [STDD Guard] No guard hook found. Already disabled.")


def cmd_guard_enable(args: argparse.Namespace) -> None:
    """Re-enable the guard hook after disable."""
    cmd_guard_init(args)


def cmd_guard(args: argparse.Namespace) -> None:
    """Entry point for guard command."""
    action = getattr(args, "action", "check")

    if action == "check":
        exit_code = cmd_guard_check(args)
        if exit_code != 0:
            sys.exit(exit_code)
    elif action == "status":
        cmd_guard_status(args)
    elif action == "init":
        cmd_guard_init(args)
    elif action == "disable":
        cmd_guard_disable(args)
    elif action == "enable":
        cmd_guard_enable(args)
    else:
        print(f"  Unknown guard action: {action}")
        sys.exit(1)
