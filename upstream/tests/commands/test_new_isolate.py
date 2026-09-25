"""TC-ISO-* — change-isolation 测试。

Slice 1（隔离形态解析 + 配置回落 + 零漂移）：
  TC-ISO-003  --help 暴露 --isolate 与三取值
  TC-ISO-002  无 --isolate 且无配置 ⇒ 零漂移（**不得调用任何 git 命令**）
  TC-ISO-015  配置 isolation.default 被消费；显式参数覆盖配置
  TC-ISO-016  配置缺失 / YAML 坏 / 取值非法 ⇒ 一律回落 none，且 new 不抛异常

Slice 2（失败前置与 git 前置检查）：
  TC-ISO-006  非 git 仓 ⇒ 非 0 退出，且不留 change 目录
  TC-ISO-007  脏工作区 + branch ⇒ 非 0 退出
  TC-ISO-008  分支/路径已存在 ⇒ 非 0 退出，不删既有路径

Slice 3（worktree 创建 + 脚手架落点切换，**行为级真 git**）：
  TC-ISO-001  骨架落在 worktree 内；主仓不含该 dir
  TC-ISO-001b 模板源取主仓（裁定 ISO-4）
  TC-ISO-004  分支名由规则构造，无路径派生后缀
  TC-ISO-009  worktree 在项目根之外；主仓 status 干净
  TC-ISO-010  isolation.worktree_root 端到端生效

Slice 4（branch 形态，**行为级真 git**）：
  TC-ISO-005  只切分支、不建 worktree；骨架落在主仓

Slice 5（门禁随 worktree，裁定 ISO-1）：
  TC-ISO-019  hook 注册文件随 worktree 复制，内容逐字节一致
  TC-ISO-020  无 hook 注册 ⇒ 明确告警但 exit 仍 0（降级而非失败）

BUILD 分期守卫（Slice 1–3 期间存在，Slice 4 后删除）：
  未实现的隔离形态必须出声拒绝，而非静默按 none 执行。详见文件内说明。
"""
import argparse
import subprocess as _sp
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from fstdd.cli.commands.new import (
    _load_isolation_config,
    _resolve_isolate_mode,
    cmd_new,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _setup_templates(project: Path) -> None:
    (project / ".fstdd" / "templates").mkdir(parents=True, exist_ok=True)
    for t in ["proposal", "design", "test-plan"]:
        (project / ".fstdd" / "templates" / f"{t}.md").write_text(f"# {t}", encoding="utf-8")


def _write_project_config(project: Path, text: str) -> None:
    cfg_dir = project / ".fstdd" / "config.d"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "project.yaml").write_text(text, encoding="utf-8")


def _new_args(**kw) -> argparse.Namespace:
    """构造 cmd_new 参数；默认**不带** isolate 键 —— 模拟既有调用方（零漂移口径）。"""
    ns = argparse.Namespace(name="iso-demo", dry_run=False, verbose=0)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


# --- git 测试工具（Slice 2 起共用）------------------------------------------
# 置于模块前部：`_GIT_OK` 用于 @pytest.mark.skipif，装饰器在模块加载时求值。

def _git_available() -> bool:
    try:
        return _sp.run(["git", "--version"], capture_output=True).returncode == 0
    except (OSError, ValueError):
        return False


_GIT_OK = _git_available()


def _git(path: Path, *args: str):
    return _sp.run(["git", *args], cwd=str(path), capture_output=True, text=True)


def _init_git_repo(path: Path) -> None:
    """在 path 建一个带 1 次提交、**工作区干净**的 git 仓。

    用 `-c user.name/user.email` 传身份，不依赖用户 git 全局配置；
    `add -A` 把既有文件一并提交，使调用方从「干净」起点出发
    （需要脏树时由用例自己造未跟踪文件）。
    """
    _git(path, "init", "-q")
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-q", "-m", "seed")


def _no_git_ancestor(monkeypatch, project: Path) -> None:
    """把 git 的向上搜索止步于 project 的父目录。

    **环境事实**：本机 `C:/Users/Administrator` 本身就是一个 git 仓，而系统临时
    目录位于其下 ⇒ 不阻断时，`temp_project` 会被判定为「在 C:/Users/Administrator
    仓内」，所有「非 git 仓」用例失真（实测 4 例因此误报）。
    `GIT_CEILING_DIRECTORIES` 是 git 为这种场景提供的正规机制。
    """
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(project.parent))


def _change_dirs(project: Path) -> list:
    return list((project / ".fstdd" / "changes").iterdir())


# ---------------------------------------------------------------------------
# TC-ISO-003 — --help 暴露开关
# ---------------------------------------------------------------------------

def test_iso_003_help_exposes_isolate():
    """TC-ISO-003: `new --help` 列出 --isolate 及 none/worktree/branch。

    走**子进程**调真 CLI，而不是在进程内 `main()`：
    `utils.fix_windows_encoding()` 会用
    `io.TextIOWrapper(sys.stdout.buffer, ...)` **替换 sys.stdout**，
    绕过 capsys 的捕获（实测 stdout 为空），且该替换会残留影响后续用例。
    子进程既避开这个全局副作用，又是真正的端到端证据。
    """
    repo = Path(__file__).resolve().parents[3]
    cli = repo / "upstream" / "bin" / "fstdd"

    result = _sp.run(
        [sys.executable, str(cli), "new", "--help"],
        capture_output=True, text=True, cwd=str(repo),
    )

    assert result.returncode == 0, f"`new --help` 退出码 {result.returncode}: {result.stderr}"
    assert "--isolate" in result.stdout, f"--help 未列出 --isolate: {result.stdout!r}"
    for mode in ("none", "worktree", "branch"):
        assert mode in result.stdout, f"--help 未列出取值 {mode}: {result.stdout!r}"


# ---------------------------------------------------------------------------
# TC-ISO-002 — 零漂移（本 change 的成败线）
# ---------------------------------------------------------------------------

def test_iso_002_no_isolation_never_invokes_git(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-002: 无 --isolate 且无配置 ⇒ 主工作区建骨架，且**全程不调用 git**。

    用「git 被调用即失败」做断言，比「检查没有 worktree」强：后者在没有 .git 的
    沙箱里天然成立，属于假阳性；前者直接锁住「none 路径零 git 副作用」。
    """
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)

    def _boom(*a, **k):
        raise AssertionError("无 --isolate 时 cmd_new 不得调用 git")

    monkeypatch.setattr(_sp, "run", _boom)

    cmd_new(_new_args(name="iso-zero-drift"))

    dirs = _change_dirs(temp_project)
    assert len(dirs) == 1, f"应恰好建 1 个 change 目录，实际 {len(dirs)}"
    assert dirs[0].name.endswith("iso-zero-drift"), dirs[0].name
    assert (dirs[0] / ".fstdd.yaml").exists()

    out = capsys.readouterr().out
    assert "隔离形态: none" in out, f"未输出 none 形态提示: {out!r}"


def test_iso_002b_new_does_not_write_isolation_config(temp_project: Path, monkeypatch):
    """TC-ISO-002: `new` 不得顺手写隔离配置（写配置是 init 的职责）。"""
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)
    cmd_new(_new_args(name="iso-no-cfg-write"))

    assert not (temp_project / ".fstdd" / "config.d" / "project.yaml").exists(), \
        "cmd_new 不应创建 project.yaml"


# ---------------------------------------------------------------------------
# TC-ISO-015 — 配置默认值被消费 / 显式参数优先
# ---------------------------------------------------------------------------

def test_iso_015_config_default_is_consumed(temp_project: Path):
    """TC-ISO-015: isolation.default: worktree 被读取。"""
    _write_project_config(temp_project, "isolation:\n  default: worktree\n")
    assert _resolve_isolate_mode(_new_args(), temp_project) == "worktree"


def test_iso_015b_explicit_flag_overrides_config(temp_project: Path):
    """TC-ISO-015: 显式 --isolate none 必须压过配置的 worktree。

    这条是「default=None 而非 'none'」这一设计决策的锚点：若 argparse 用
    default='none'，显式与缺省无法区分，配置项就永远无法生效。
    """
    _write_project_config(temp_project, "isolation:\n  default: worktree\n")
    assert _resolve_isolate_mode(_new_args(isolate="none"), temp_project) == "none"


# ---------------------------------------------------------------------------
# TC-ISO-016 — 配置读取失败一律回落 none（方向锁）
# ---------------------------------------------------------------------------

def test_iso_016a_config_missing_falls_back_to_none(temp_project: Path):
    """TC-ISO-016①: 配置缺失 ⇒ {} 且回落 none。"""
    assert _load_isolation_config(temp_project) == {}
    assert _resolve_isolate_mode(_new_args(), temp_project) == "none"


def test_iso_016b_bad_yaml_falls_back_to_none(temp_project: Path):
    """TC-ISO-016②: YAML 不可解析 ⇒ {} 且回落 none（**不是** worktree）。"""
    _write_project_config(temp_project, "isolation: [unclosed\n  default: worktree\n")
    assert _load_isolation_config(temp_project) == {}
    assert _resolve_isolate_mode(_new_args(), temp_project) == "none"


def test_iso_016c_illegal_value_falls_back_to_none(temp_project: Path):
    """TC-ISO-016③: 取值非法 ⇒ 回落 none。"""
    _write_project_config(temp_project, "isolation:\n  default: banana\n")
    assert _resolve_isolate_mode(_new_args(), temp_project) == "none"


def test_iso_016d_wrong_shape_falls_back_to_none(temp_project: Path):
    """TC-ISO-016 补充：isolation 不是映射（如写成字符串）⇒ 回落 none。"""
    _write_project_config(temp_project, "isolation: worktree\n")
    assert _load_isolation_config(temp_project) == {}
    assert _resolve_isolate_mode(_new_args(), temp_project) == "none"


def test_iso_016e_new_survives_bad_config(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-016: 坏配置不得让 `new` 报错退出 —— 回落 none 并正常建骨架。"""
    _setup_templates(temp_project)
    _write_project_config(temp_project, "isolation: [oops\n")
    monkeypatch.chdir(temp_project)

    cmd_new(_new_args(name="iso-bad-cfg"))

    assert len(_change_dirs(temp_project)) == 1
    assert "隔离形态: none" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# BUILD 分期守卫已随 Slice 4 删除
# ---------------------------------------------------------------------------
# Slice 1–3 期间存在一条 `test_unimplemented_mode_fails_loud`，断言
# `--isolate worktree|branch` 在实现落地前必须**出声拒绝**（exit 1 且无残留）。
# 它存在的意义是防止「参数已注册、实则永不生效」——正是本 change 要消灭的
# `--parallel` 死开关缺陷。`worktree`（Slice 3）与 `branch`（Slice 4）均已实现，
# 故守卫及其用例一并移除。
# ⚠️ 后续若再新增隔离形态（如 `container`），**必须重新加回等价守卫**，
#    而不是让它静默按 none 执行。


# ===========================================================================
# Slice 2：失败前置与 git 前置检查
#   TC-ISO-006  非 git 仓 + worktree|branch ⇒ 非 0 退出，且不留 change 目录
#   TC-ISO-007  脏工作区 + branch ⇒ 非 0 退出、提示改用 worktree、分支未变
#   TC-ISO-008  分支已存在 / 目标路径已存在 ⇒ 非 0 退出、给清理命令、不删既有路径
#   TC-ISO-009/010（路径解析部分）默认 worktree 根在项目外；可被配置覆盖
#
# 注意：Slice 2 新增的符号在**函数内部**导入，而非模块顶层 —— 这样在实现落地前
# 走 cmd_new 的用例会以「断言失败」（行为级 RED）暴露，而不是整模块 collection error。
# ===========================================================================


# ---------------------------------------------------------------------------
# TC-ISO-006 — 非 git 仓拒绝（且不留半成品）
# ---------------------------------------------------------------------------

def test_iso_006_non_git_repo_refuses_worktree(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-006: 非 git 工作树内 `--isolate worktree` ⇒ 非 0 退出，且不建 change 目录。"""
    _setup_templates(temp_project)
    _no_git_ancestor(monkeypatch, temp_project)
    monkeypatch.chdir(temp_project)
    assert not (temp_project / ".git").exists(), "测试前提：此处不是 git 仓"
    # 前提自检：确认祖先仓确已被阻断，否则本用例会因「找到祖先仓」而失真
    from fstdd.cli.commands.new import _git_worktree_root
    assert _git_worktree_root(temp_project) is None, "祖先 git 仓未被阻断，用例前提不成立"

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name="iso-nongit", isolate="worktree"))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "git 工作树" in out, f"未说明真实原因: {out!r}"
    assert _change_dirs(temp_project) == [], "失败路径不得留下 change 目录"


def test_iso_006b_non_git_repo_refuses_branch(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-006: branch 形态同样拒绝，不静默降级为 none。"""
    _setup_templates(temp_project)
    _no_git_ancestor(monkeypatch, temp_project)
    monkeypatch.chdir(temp_project)

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name="iso-nongit-b", isolate="branch"))

    assert exc.value.code == 1
    assert "git 工作树" in capsys.readouterr().out
    assert _change_dirs(temp_project) == []


# ---------------------------------------------------------------------------
# TC-ISO-007 — 脏工作区拒绝 branch 形态
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GIT_OK, reason="需要 git")
def test_iso_007_dirty_tree_refuses_branch(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-007: 脏工作区（含未跟踪文件）+ branch ⇒ 拒绝，且分支未变化。"""
    _setup_templates(temp_project)
    _init_git_repo(temp_project)          # 干净起点
    (temp_project / "dirty-untracked.txt").write_text("wip\n", encoding="utf-8")
    assert _git(temp_project, "status", "--porcelain").stdout.strip(), "测试前提：工作区应为脏"

    monkeypatch.chdir(temp_project)
    branch_before = _git(temp_project, "branch", "--show-current").stdout.strip()

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name="iso-dirty", isolate="branch"))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "未提交改动" in out, f"未说明真实原因: {out!r}"
    assert "--isolate worktree" in out, f"未给出替代路径: {out!r}"

    branch_after = _git(temp_project, "branch", "--show-current").stdout.strip()
    assert branch_after == branch_before, "拒绝路径不得切换分支"


# ---------------------------------------------------------------------------
# TC-ISO-008 — 冲突预检，且不自行删除
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GIT_OK, reason="需要 git")
def test_iso_008a_existing_branch_refuses_worktree(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-008: 分支已存在 ⇒ 创建前拒绝，输出清理命令，既有分支保留。"""
    dir_name = "2026-09-26-iso-branch-clash"   # 已含日期前缀 ⇒ dir_name 可预测
    _setup_templates(temp_project)
    _init_git_repo(temp_project)
    _git(temp_project, "branch", f"fstdd/{dir_name}")

    monkeypatch.chdir(temp_project)

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name=dir_name, isolate="worktree"))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "分支已存在" in out, f"未说明真实原因: {out!r}"
    assert f"fstdd/{dir_name}" in out
    assert "git branch -D" in out, f"未给清理命令: {out!r}"

    verify = _git(temp_project, "rev-parse", "--verify", f"refs/heads/fstdd/{dir_name}")
    assert verify.returncode == 0, "既有分支被删除了"
    assert _change_dirs(temp_project) == []


@pytest.mark.skipif(not _GIT_OK, reason="需要 git")
def test_iso_008b_existing_path_refuses_worktree(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-008: worktree 目标路径已存在 ⇒ 拒绝，且**不删除**既有路径。"""
    dir_name = "2026-09-26-iso-path-clash"
    _setup_templates(temp_project)
    _init_git_repo(temp_project)
    _write_project_config(temp_project, "isolation:\n  worktree_root: wtroot\n")
    target = temp_project / "wtroot" / dir_name
    target.mkdir(parents=True)
    sentinel = target / "DO-NOT-DELETE.txt"
    sentinel.write_text("keep me\n", encoding="utf-8")

    monkeypatch.chdir(temp_project)

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name=dir_name, isolate="worktree"))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "已存在" in out, f"未说明真实原因: {out!r}"
    assert "git worktree remove" in out, f"未给清理命令: {out!r}"
    assert sentinel.exists(), "既有路径被删除了 —— 失败路径不得执行删除"
    assert sentinel.read_text(encoding="utf-8") == "keep me\n"
    assert _change_dirs(temp_project) == []


# ---------------------------------------------------------------------------
# 辅助函数单测（git 探测的三态与保守方向）
# ---------------------------------------------------------------------------

def test_slice2_git_probes_on_non_git_dir_are_conservative(temp_project: Path, monkeypatch):
    """非 git 仓：探测返回 None/False，且 `脏` 判定取**保守方向**（True）。"""
    _no_git_ancestor(monkeypatch, temp_project)
    from fstdd.cli.commands.new import (
        _branch_exists,
        _git_worktree_root,
        _is_worktree_dirty,
    )

    assert _git_worktree_root(temp_project) is None
    assert _branch_exists(temp_project, "whatever") is False
    # 测不准 ⇒ 判脏 ⇒ 拒绝；绝不静默放行（ISO-3 取向）
    assert _is_worktree_dirty(temp_project) is True


@pytest.mark.skipif(not _GIT_OK, reason="需要 git")
def test_slice2_git_probes_in_git_repo(temp_project: Path):
    """真 git 仓：工作树根可定位、干净判定为 False、未跟踪文件也算脏。"""
    from fstdd.cli.commands.new import (
        _branch_exists,
        _git_worktree_root,
        _is_worktree_dirty,
    )

    _init_git_repo(temp_project)

    root = _git_worktree_root(temp_project)
    assert root is not None and (root / ".git").exists(), f"工作树根定位失败: {root}"
    assert _is_worktree_dirty(temp_project) is False, "刚提交完应为干净"
    assert _branch_exists(temp_project, "no-such-branch") is False

    _git(temp_project, "branch", "probe-branch")
    assert _branch_exists(temp_project, "probe-branch") is True

    (temp_project / "untracked.txt").write_text("x", encoding="utf-8")
    assert _is_worktree_dirty(temp_project) is True, "未跟踪文件也必须算脏"


# ---------------------------------------------------------------------------
# TC-ISO-009 / TC-ISO-010（路径解析部分，创建动作在 Slice 3）
# ---------------------------------------------------------------------------

def test_iso_009_default_worktree_root_is_outside_project(temp_project: Path, monkeypatch):
    """TC-ISO-009: 无配置时 worktree 根位于项目根**之外**。"""
    _no_git_ancestor(monkeypatch, temp_project)   # 保证走「无 git 仓」分支
    from fstdd.cli.commands.new import _resolve_worktree_root

    p = _resolve_worktree_root(temp_project, "2026-09-26-x")
    assert p == temp_project.parent / f"{temp_project.name}.worktrees" / "2026-09-26-x"
    assert temp_project not in p.parents, "默认 worktree 根不得落在项目内（会污染 git status）"


def test_iso_010_configured_worktree_root_is_honored(temp_project: Path):
    """TC-ISO-010: isolation.worktree_root 生效（相对路径按项目根解析）。"""
    from fstdd.cli.commands.new import _resolve_worktree_root

    _write_project_config(temp_project, "isolation:\n  worktree_root: wtroot\n")
    assert _resolve_worktree_root(temp_project, "2026-09-26-x") == \
        temp_project / "wtroot" / "2026-09-26-x"


def test_branch_name_default_and_configured_prefix(temp_project: Path):
    """TC-ISO-004 的分支名规则：默认 fstdd/ 前缀，可被 branch_prefix 覆盖。"""
    from fstdd.cli.commands.new import _branch_name

    assert _branch_name(temp_project, "2026-09-26-x") == "fstdd/2026-09-26-x"
    _write_project_config(temp_project, 'isolation:\n  branch_prefix: "team/"\n')
    assert _branch_name(temp_project, "2026-09-26-x") == "team/2026-09-26-x"


# ---------------------------------------------------------------------------
# Slice 3 — worktree 创建 + 脚手架落点切换（行为级，真 git）
# ---------------------------------------------------------------------------

def _expected_dir_name(short: str) -> str:
    return f"{date.today().isoformat()}-{short}"


def _wt_root_for(project: Path) -> Path:
    return project.parent / f"{project.name}.worktrees"


def _isolated_git_project(temp_project: Path, monkeypatch) -> Path:
    """沙箱 git 仓：模板先落盘再 commit（使 worktree 内自带模板），并 chdir。

    顺序刻意如此 —— `git worktree add` 只签出**已跟踪**文件，
    先 commit 才能保证 worktree 里 `.fstdd/templates/` 随行。
    """
    _setup_templates(temp_project)
    _init_git_repo(temp_project)
    _no_git_ancestor(monkeypatch, temp_project)
    monkeypatch.chdir(temp_project)
    return temp_project


def _worktree_lines(project: Path) -> list:
    out = _git(project, "worktree", "list").stdout
    return [ln for ln in out.splitlines() if ln.strip()]


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_001_skeleton_lands_in_worktree(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-001: worktree 真建出来，骨架落在 worktree 内，主仓不含该 dir。"""
    project = _isolated_git_project(temp_project, monkeypatch)
    cmd_new(_new_args(name="iso-one", isolate="worktree"))

    dir_name = _expected_dir_name("iso-one")
    wt = _wt_root_for(project) / dir_name
    change_in_wt = wt / ".fstdd" / "changes" / dir_name

    assert wt.is_dir(), f"worktree 未建出: {wt}\n输出: {capsys.readouterr().out}"
    assert (change_in_wt / ".fstdd.yaml").exists(), "状态文件未落在 worktree 内"
    assert (change_in_wt / "specs").is_dir(), "specs 子目录未落在 worktree 内"
    assert (change_in_wt / "canonical" / "proposals" / f"{dir_name}.yaml").exists(), \
        "canonical 骨架未落在 worktree 内"
    assert (change_in_wt / "design.md").exists(), "模板 design.md 未复制到 worktree 内"

    assert not (project / ".fstdd" / "changes" / dir_name).exists(), \
        "主仓不得出现该 change 目录（隔离失效）"
    assert len(_worktree_lines(project)) == 2, "git worktree list 应出现第 2 条"


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_001b_template_source_is_main_repo(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-001（补充，裁定 ISO-4）: 模板源取**主仓**，不是 target_root。

    worktree 是 HEAD 的签出，**未提交**文件不会随行。若模板源取 target_root，
    主仓里未提交的模板会被静默跳过（`if tmpl.exists()`），产出缺
    design.md / test-plan.md 的半成品骨架 —— 属静默失败类缺陷。
    """
    project = _isolated_git_project(temp_project, monkeypatch)
    # init 之后才写 ⇒ 该内容未被提交 ⇒ 不会出现在新 worktree 的 templates 里
    marker = "# design-v2-UNCOMMITTED"
    (project / ".fstdd" / "templates" / "design.md").write_text(marker, encoding="utf-8")

    cmd_new(_new_args(name="iso-late", isolate="worktree"))

    dir_name = _expected_dir_name("iso-late")
    wt = _wt_root_for(project) / dir_name
    copied = (wt / ".fstdd" / "changes" / dir_name / "design.md")
    assert copied.exists(), f"未提交模板被静默跳过\n输出: {capsys.readouterr().out}"
    assert copied.read_text(encoding="utf-8") == marker, \
        "模板源不是主仓 —— 取到了 worktree 内的旧版本"


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_004_branch_name_is_rule_derived(temp_project: Path, monkeypatch, capsys):
    """TC-ISO-004: 分支名精确等于 <branch_prefix><dir_name>，无路径派生后缀。"""
    project = _isolated_git_project(temp_project, monkeypatch)
    cmd_new(_new_args(name="iso-four", isolate="worktree"))

    dir_name = _expected_dir_name("iso-four")
    wt = _wt_root_for(project) / dir_name

    branch = _git(wt, "branch", "--show-current").stdout.strip()
    assert branch == f"fstdd/{dir_name}", f"分支名不符: {branch!r}\n输出: {capsys.readouterr().out}"
    for suffix in ("-explore", "-research"):
        assert suffix not in branch, f"分支名残留路径派生后缀 {suffix}: {branch!r}"


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_009_worktree_outside_project_and_main_repo_clean(
    temp_project: Path, monkeypatch, capsys
):
    """TC-ISO-009: 默认 worktree 根 = 项目根**父目录**下；主仓 status 保持干净。"""
    project = _isolated_git_project(temp_project, monkeypatch)
    cmd_new(_new_args(name="iso-nine", isolate="worktree"))

    dir_name = _expected_dir_name("iso-nine")
    wt = _wt_root_for(project) / dir_name

    assert wt.parent == project.parent / f"{project.name}.worktrees"
    assert project not in wt.parents, "worktree 不得落在项目内"
    assert _git(project, "status", "--porcelain").stdout.strip() == "", \
        f"主仓被污染\n输出: {capsys.readouterr().out}"


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_010_configured_worktree_root_is_honored_e2e(
    temp_project: Path, monkeypatch, capsys
):
    """TC-ISO-010: isolation.worktree_root 端到端生效（绝对路径）。"""
    project = _isolated_git_project(temp_project, monkeypatch)
    base = temp_project.parent / "custom-wt"
    _write_project_config(
        project,
        yaml.safe_dump({"isolation": {"worktree_root": str(base)}}, allow_unicode=True),
    )

    cmd_new(_new_args(name="iso-ten", isolate="worktree"))

    dir_name = _expected_dir_name("iso-ten")
    assert (base / dir_name).is_dir(), \
        f"worktree 未落在配置路径\n输出: {capsys.readouterr().out}"
    assert (base / dir_name / ".fstdd" / "changes" / dir_name / ".fstdd.yaml").exists()


# ---------------------------------------------------------------------------
# Slice 4 — branch 形态（行为级，真 git）
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_005_branch_mode_switches_branch_only(
    temp_project: Path, monkeypatch, capsys
):
    """TC-ISO-005: branch 形态只切分支，**不建 worktree**；骨架落在主仓。

    与 worktree 形态的关键区别：落点仍是主仓（工作区共享），
    隔离性来自「分支」而非「目录」。因此 target_root 不变。
    """
    project = _isolated_git_project(temp_project, monkeypatch)
    before = _git(project, "branch", "--show-current").stdout.strip()

    cmd_new(_new_args(name="iso-five", isolate="branch"))

    dir_name = _expected_dir_name("iso-five")
    out = capsys.readouterr().out

    current = _git(project, "branch", "--show-current").stdout.strip()
    assert current == f"fstdd/{dir_name}", f"分支未切换: {current!r}\n输出: {out}"
    assert current != before, "分支必须真的换掉，而不是停在原分支上"

    assert len(_worktree_lines(project)) == 1, \
        f"branch 形态不得创建 worktree\n输出: {out}"

    # 骨架落在主仓（branch 模式共享工作区）
    assert (project / ".fstdd" / "changes" / dir_name / ".fstdd.yaml").exists(), \
        "branch 模式骨架应落在主仓"
    assert (project / ".fstdd" / "changes" / dir_name / "canonical").is_dir()


# ---------------------------------------------------------------------------
# Slice 5 — 门禁随 worktree 生效（裁定 ISO-1）
# ---------------------------------------------------------------------------

_HOOK_RELS = (".claude/settings.local.json", ".codebuddy/settings.local.json")


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
@pytest.mark.parametrize("rel", _HOOK_RELS)
def test_iso_019_guard_hooks_propagate_into_worktree(
    temp_project: Path, monkeypatch, capsys, rel: str
):
    """TC-ISO-019: 门禁 hook 注册随 worktree 复制，且内容与主仓一致。

    这是裁定 ISO-1 的锚点。缺口根因：`git worktree add` **只签出已跟踪文件**，
    而 hook 注册（`.claude/settings.local.json` 等）通常被 gitignore
    —— 于是新 worktree 里没有任何门禁，隔离就变成绕过 Guard 的通道。
    """
    project = _isolated_git_project(temp_project, monkeypatch)

    # 前提自检：hook 文件必须**未被跟踪**，否则 git 会自行签出，
    # 本用例就无法区分「实现生效」与「git 顺带带过来」。
    tracked = _git(project, "ls-files", "--error-unmatch", rel).returncode == 0
    assert not tracked, f"{rel} 已被 git 跟踪，本用例前提不成立"

    payload = '{"hooks": {"PreToolUse": [{"command": "stdd guard check"}]}}'
    hook_src = project / rel
    hook_src.parent.mkdir(parents=True, exist_ok=True)
    hook_src.write_text(payload, encoding="utf-8")

    cmd_new(_new_args(name="iso-hook", isolate="worktree"))

    dir_name = _expected_dir_name("iso-hook")
    wt = _wt_root_for(project) / dir_name
    copied = wt / rel

    assert copied.is_file(), \
        f"门禁 hook 未随 worktree 复制: {rel}\n输出: {capsys.readouterr().out}"
    assert copied.read_text(encoding="utf-8") == payload, "复制内容与主仓不一致"


@pytest.mark.skipif(not _GIT_OK, reason="git 不可用")
def test_iso_020_missing_hooks_warns_but_succeeds(
    temp_project: Path, monkeypatch, capsys
):
    """TC-ISO-020: 无任何 hook 注册 ⇒ 明确告警，但 exit 仍 0。

    门禁缺失是**可继续的降级**，不是失败 —— 若在此处 exit 1，
    在尚未接入 Guard 的项目里 `--isolate worktree` 将完全不可用。
    但**绝不能静默通过**：用户必须知道该 worktree 内门禁未激活。
    """
    project = _isolated_git_project(temp_project, monkeypatch)

    cmd_new(_new_args(name="iso-nohook", isolate="worktree"))

    out = capsys.readouterr().out
    assert "门禁" in out, f"未就门禁缺失出声: {out!r}"
    assert "⚠️" in out, f"告警缺少显著标记: {out!r}"

    dir_name = _expected_dir_name("iso-nohook")
    wt = _wt_root_for(project) / dir_name
    assert (wt / ".fstdd" / "changes" / dir_name / ".fstdd.yaml").exists(), \
        "告警不应阻断 change 创建（exit 必须为 0）"
