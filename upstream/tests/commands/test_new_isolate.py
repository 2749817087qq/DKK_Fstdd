"""TC-ISO-* — change-isolation 切片 1：隔离形态解析 + 配置回落 + 零漂移。

覆盖：
  TC-ISO-003  --help 暴露 --isolate 与三取值
  TC-ISO-002  无 --isolate 且无配置 ⇒ 零漂移（**不得调用任何 git 命令**）
  TC-ISO-015  配置 isolation.default 被消费；显式参数覆盖配置
  TC-ISO-016  配置缺失 / YAML 坏 / 取值非法 ⇒ 一律回落 none，且 new 不抛异常

另含一条 **BUILD 分期守卫** 用例（无 spec TC-ID）：Slice 1 阶段
worktree/branch 尚未实现，必须出声拒绝而非静默按 none 执行。
"""
import argparse
import subprocess as _sp
import sys
from pathlib import Path

import pytest

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
# BUILD 分期守卫（无 spec TC-ID；Slice 3/4 实现后连同守卫一起删除）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["worktree", "branch"])
def test_stage1_unimplemented_mode_fails_loud(temp_project: Path, monkeypatch, capsys, mode):
    """未实现的隔离形态必须**出声拒绝**，且不得留下 change 目录。

    若此处改成静默按 none 执行，本 change 就复制了它要消灭的缺陷
    （`--parallel`：argparse 表面接受、实则永不生效）。
    """
    _setup_templates(temp_project)
    monkeypatch.chdir(temp_project)

    with pytest.raises(SystemExit) as exc:
        cmd_new(_new_args(name="iso-unimplemented", isolate=mode))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "尚未实现" in out, f"未出声拒绝: {out!r}"
    assert _change_dirs(temp_project) == [], "拒绝路径不得留下 change 目录"
