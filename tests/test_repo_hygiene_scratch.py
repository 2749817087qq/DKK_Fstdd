"""
test_repo_hygiene_scratch.py — 非发布物 `_scratch/` 不入库
覆盖 TC-RH-001 / TC-RH-002 / TC-RH-003 / TC-RH-004（capability: repo-hygiene）

核心安全约束：取消跟踪**仅动索引**（`git rm -r --cached`），磁盘实体必须零变动。

`SCRATCH_INDEX_ENTITIES` 是修复前 `git ls-files _scratch/` 的 27 条快照
（25 x 100644 + 2 x 160000 gitlink），即「零丢失」契约。
快照证据：`.fstdd/changes/2026-10-06-legacy-debt-cleanup/audit/scratch-inventory.txt`。
"""
import subprocess
from pathlib import Path

import pytest

from conftest import repo_root


ROOT = repo_root()
SCRATCH = ROOT / "_scratch"
GITIGNORE = ROOT / ".gitignore"

# ⚠️ 可移植性：`_scratch/` 本身是 **gitignored 且未跟踪** 的本地目录
#    ⇒ fresh clone / CI 上根本不存在，磁盘零损失断言在那里不适用（应 skip 而非 fail）。
#    索引退出 + gitignore 生效这两条与本地是否存在无关，故**恒**执行。
SCRATCH_LOCAL = SCRATCH.is_dir()
_scratch_absent = pytest.mark.skipif(
    not SCRATCH_LOCAL,
    reason="本地无 _scratch/（fresh clone / CI / 已正当清理）—— 磁盘零损失断言不适用",
)

# 修复前索引快照：25 个普通文件
SCRATCH_TRACKED_FILES = (
    "_scratch/add_fin_kg.py",
    "_scratch/cc/fstdd-build/SKILL.md",
    "_scratch/cc/fstdd-spec/SKILL.md",
    "_scratch/cc/fstdd-understand/SKILL.md",
    "_scratch/cc/fstdd/SKILL.md",
    "_scratch/dispatch_tasks.py",
    "_scratch/green_final.log",
    "_scratch/green_pytest.log",
    "_scratch/green_pytest2.log",
    "_scratch/red_pytest.log",
    "_scratch/stdd-dev/stdd-baseline-5e3f9a3.tar.gz",
    "_scratch/test-wb/fstdd-build/SKILL.md",
    "_scratch/test-wb/fstdd-spec/SKILL.md",
    "_scratch/test-wb/fstdd-understand/SKILL.md",
    "_scratch/test-wb/fstdd/SKILL.md",
    "_scratch/test-workbuddy-now/fstdd-build/SKILL.md",
    "_scratch/test-workbuddy-now/fstdd-spec/SKILL.md",
    "_scratch/test-workbuddy-now/fstdd-understand/SKILL.md",
    "_scratch/test-workbuddy-now/fstdd/SKILL.md",
    "_scratch/verify-trae/fstdd-build/SKILL.md",
    "_scratch/verify-trae/fstdd-deliver/SKILL.md",
    "_scratch/verify-trae/fstdd-spec/SKILL.md",
    "_scratch/verify-trae/fstdd-understand/SKILL.md",
    "_scratch/verify-trae/fstdd-upgrade/SKILL.md",
    "_scratch/verify-trae/fstdd/SKILL.md",
)

# 修复前索引快照：2 个 gitlink（磁盘上为目录；实测为空目录 —— 子模块从未初始化）
SCRATCH_GITLINK_DIRS = (
    "_scratch/stdd-dev/stdd-repo",
    "_scratch/upstream-cli-sync",
)

# 修复前索引条目总数
SCRATCH_INDEX_COUNT = len(SCRATCH_TRACKED_FILES) + len(SCRATCH_GITLINK_DIRS)


def _git(*args) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.stdout or ""


def _tracked_scratch() -> list:
    return [l for l in _git("ls-files", "_scratch/").splitlines() if l.strip()]


def _gitignore_rules() -> list:
    return [l.strip() for l in GITIGNORE.read_text(encoding="utf-8").splitlines()]


def _status_scratch_paths() -> list:
    """`git status --porcelain` 中**路径**落在 `_scratch/` 下的行。

    注意：必须按路径前缀判定，不能对整行做子串匹配
    —— 否则本文件自身的名字 `test_repo_hygiene_scratch.py` 会误命中。
    """
    hits = []
    for line in _git("status", "--porcelain").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if path == "_scratch" or path.startswith("_scratch/"):
            hits.append(line)
    return hits


# ============================================================
# TC-RH-001 / SC-001 — `_scratch/` 已退出 git 索引
# ============================================================
def test_tc_rh_001_scratch_not_tracked():
    tracked = _tracked_scratch()
    assert not tracked, (
        f"_scratch/ 仍被 git 跟踪（{len(tracked)} 条，修复前为 {SCRATCH_INDEX_COUNT}）:\n"
        + "\n".join(tracked[:10])
    )


# ============================================================
# TC-RH-002 / SC-002 — 磁盘实体完整保留（取消跟踪不等于删除）
# ============================================================
@_scratch_absent
def test_tc_rh_002_scratch_disk_entities_preserved():
    """⚠️ 本用例只在**本地存在 `_scratch/`** 时有意义（见 SCRATCH_LOCAL 注释）。

    `SCRATCH_TRACKED_FILES` 是「取消跟踪不得丢实体」的**变更期验收契约**。
    日后若正当清理该目录，应同步修订此契约 —— 否则会在此处得到一条
    「契约过期」而非「实体丢失」的假失败。
    """
    assert SCRATCH.is_dir(), "_scratch/ 磁盘目录丢失（取消跟踪绝不能删工作树实体）"

    missing_files = [p for p in SCRATCH_TRACKED_FILES if not (ROOT / p).is_file()]
    assert not missing_files, (
        f"取消跟踪后丢失 {len(missing_files)} 个普通文件实体:\n" + "\n".join(missing_files)
    )

    missing_dirs = [p for p in SCRATCH_GITLINK_DIRS if not (ROOT / p).is_dir()]
    assert not missing_dirs, (
        f"取消跟踪后丢失 {len(missing_dirs)} 个 gitlink 磁盘目录:\n" + "\n".join(missing_dirs)
    )


@_scratch_absent
def test_tc_rh_002b_scratch_entities_are_non_empty_where_expected():
    """实体不能退化成空文件（内容丢失的隐性形态）。"""
    empty = [
        p for p in SCRATCH_TRACKED_FILES
        if (ROOT / p).is_file() and (ROOT / p).stat().st_size == 0
    ]
    assert not empty, f"以下实体被清空（0 字节）:\n" + "\n".join(empty)


# ============================================================
# TC-RH-003 / SC-003 — `.gitignore` 忽略 + 不再以 untracked 形态出现
# ============================================================
def test_tc_rh_003_gitignore_ignores_scratch():
    rules = [r.rstrip("/") for r in _gitignore_rules()]
    assert "_scratch" in rules, (
        ".gitignore 未含忽略 _scratch/ 的规则（须为 _scratch/ 或 /_scratch/）"
    )


def test_tc_rh_003b_git_status_has_no_untracked_scratch_entry():
    """除「已暂存的删除」外，`git status` 不得再出现 `_scratch/` 条目。

    BUILD 阶段 `git rm -r --cached` 会留下 `D ` 形态的暂存删除（工作树文件仍在）；
    DELIVER 提交后该形态消失 —— 故本断言对「提交前 / 提交后」两态均成立。
    """
    bad = [l for l in _status_scratch_paths() if l[:2] not in ("D ", "D")]
    assert not bad, (
        "git status 仍出现非「暂存删除」的 _scratch/ 条目:\n" + "\n".join(bad)
    )


def test_tc_rh_003c_scratch_is_gitignored():
    """`git check-ignore` 确认 `_scratch/` 已被忽略规则命中。"""
    r = subprocess.run(
        ["git", "check-ignore", "-v", "_scratch"],
        cwd=str(ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0 and (r.stdout or "").strip(), (
        f"_scratch/ 未被 .gitignore 命中（rc={r.returncode}）"
    )


# ============================================================
# TC-RH-004 / SC-004 — 三条件同时成立，且不波及 `_scratch/` 之外
# ============================================================
def test_tc_rh_004_three_conditions_simultaneously():
    assert not _tracked_scratch(), "条件1失败：`git ls-files _scratch/` 非空"
    assert "_scratch" in [r.rstrip("/") for r in _gitignore_rules()], \
        "条件2失败：`.gitignore` 无 `_scratch/` 规则"
    if SCRATCH_LOCAL:
        assert SCRATCH.is_dir() and any(SCRATCH.iterdir()), \
            "条件3失败：`_scratch/` 磁盘实体不在"


def test_tc_rh_004b_no_non_scratch_tracked_file_removed():
    """取消跟踪 SHALL NOT 波及 `_scratch/` 之外的任何已跟踪文件。"""
    removed = [
        l for l in _git("diff", "--cached", "--name-only", "--diff-filter=D").splitlines()
        if l.strip() and not l.startswith("_scratch/")
    ]
    assert not removed, (
        "索引中出现了 `_scratch/` 之外的删除:\n" + "\n".join(removed)
    )
