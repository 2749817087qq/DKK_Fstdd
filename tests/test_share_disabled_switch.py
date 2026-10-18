# -*- coding: utf-8 -*-
"""静默回传总开关的读取健壮性（2026-10-18 审计 F7）。

两处缺陷：

① `except (OSError, yaml.YAMLError)` 漏 `UnicodeDecodeError`
   —— 实测 `issubclass(UnicodeDecodeError, OSError) is False`，
   配置文件含非法 UTF-8 字节时异常会逃逸到 `_cmd_auto_deposit`，
   可能把 DELIVER 流程带崩。而本开关的契约是「读不到就按开启处理」，
   绝不能因为编码问题阻断主流程。

② 用 `Path.cwd()` 定位配置
   —— 从项目**子目录**运行 CLI 时 cwd 下没有 `.fstdd/`，配置读不到 ⇒
   开关被误判成「未配置 ⇒ 开启」，与 `tools/share_experience.py` 的判定分叉。
   改为从 cwd 向上找第一个含 `.fstdd/` 的目录（git 惯例）。

运行：
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \\
        python -m pytest tests/test_share_disabled_switch.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "upstream") not in sys.path:
    sys.path.insert(0, str(REPO / "upstream"))

from fstdd.cli.commands import experience as EXP  # noqa: E402


def _write_cfg(root: Path, enabled: bool) -> Path:
    cfg = root / ".fstdd" / "config.d" / "experience.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("share:\n  silent:\n    enabled: %s\n" % ("true" if enabled else "false"),
                   encoding="utf-8")
    return cfg


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("FSTDD_NO_SHARE", raising=False)


def test_env_flag_wins(monkeypatch, tmp_path):
    """`FSTDD_NO_SHARE` 优先于配置（配置说开启，env 说关闭）。"""
    _write_cfg(tmp_path, enabled=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FSTDD_NO_SHARE", "1")
    assert EXP._share_disabled() is True


def test_config_disabled(tmp_path, monkeypatch):
    _write_cfg(tmp_path, enabled=False)
    monkeypatch.chdir(tmp_path)
    assert EXP._share_disabled() is True


def test_config_enabled(tmp_path, monkeypatch):
    _write_cfg(tmp_path, enabled=True)
    monkeypatch.chdir(tmp_path)
    assert EXP._share_disabled() is False


def test_missing_config_defaults_to_enabled(tmp_path, monkeypatch):
    """配置缺失 ⇒ 按开启处理（契约不由文件是否存在决定）。"""
    monkeypatch.chdir(tmp_path)
    assert EXP._share_disabled() is False


def test_undecodable_config_does_not_raise(tmp_path, monkeypatch):
    """TC-CLOSURE-014（SC-013）配置含非法 UTF-8 字节时必须吞掉 UnicodeDecodeError，不得逃逸。

    审计 F7 ① 的回归锁：`UnicodeDecodeError` 不是 `OSError` 子类，
    旧 except 元组抓不到，异常会一路冒到 `_cmd_auto_deposit`。
    """
    cfg = tmp_path / ".fstdd" / "config.d" / "experience.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_bytes(b"share:\n  silent:\n    enabled: \xff\xfe\x00bad\n")
    monkeypatch.chdir(tmp_path)

    # 不抛即通过；返回值按「读不到 ⇒ 开启」契约
    assert EXP._share_disabled() is False


def test_config_found_from_subdirectory(tmp_path, monkeypatch):
    """TC-CLOSURE-014（SC-014）从项目子目录运行时也必须读到根上的配置（审计 F7 ②）。"""
    _write_cfg(tmp_path, enabled=False)
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)

    assert EXP._find_project_root() == tmp_path.resolve()
    assert EXP._share_disabled() is True


def test_find_project_root_falls_back_to_cwd(tmp_path, monkeypatch):
    """向上找不到**项目根**时返回起点本身，不得上溯到盘根或用户主目录。"""
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    monkeypatch.chdir(lonely)
    assert EXP._find_project_root() == lonely.resolve()


def test_registry_only_dotfstdd_is_not_a_project_root(tmp_path, monkeypatch):
    """TC-CLOSURE-014（SC-014）只有 `projects.yaml` 的 `.fstdd/` 是全局注册表，不是项目根。

    实测环境事实：`C:/Users/Administrator/.fstdd/` 只有 projects.yaml、无 config.d。
    若判据只是「目录下有 .fstdd/」，从任何用户目录下的路径向上找都会命中它，
    把用户主目录误当项目根（2026-10-18 实测踩到）。
    """
    registry = tmp_path / "home"
    (registry / ".fstdd").mkdir(parents=True)
    (registry / ".fstdd" / "projects.yaml").write_text("projects: []\n", encoding="utf-8")
    work = registry / "work" / "proj"
    work.mkdir(parents=True)
    monkeypatch.chdir(work)

    assert EXP._looks_like_project(registry) is False
    assert EXP._find_project_root() == work.resolve()
    # 没有 config.d ⇒ 开关按「未配置 ⇒ 开启」处理
    assert EXP._share_disabled() is False


def test_real_project_skeleton_is_recognised(tmp_path, monkeypatch):
    """带 config.d 的 `.fstdd/` 才算项目根。"""
    proj = tmp_path / "proj"
    (proj / ".fstdd" / "config.d").mkdir(parents=True)
    assert EXP._looks_like_project(proj) is True
    monkeypatch.chdir(proj)
    assert EXP._find_project_root() == proj.resolve()
