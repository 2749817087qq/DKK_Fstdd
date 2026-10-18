# -*- coding: utf-8 -*-
"""仓库根 conftest —— 只做一件事：把出站守卫装到**所有** pytest 子树。

为什么需要它（2026-10-18 审计 D5-07）：
守卫原本只装在 `tests/conftest.py` 与 `upstream/tests/conftest.py`，而
`tools/tests/` 既不在 `tests/` 子树、也没有自己的 conftest ⇒ 跑
`pytest tools/tests/` 时守卫**完全不安装**（实测 `15 passed` 但
`is_installed()` 为 False）。在 `tools/tests/` 下新增任何 ssh/scp 用例都不会被兜住。

放在仓库根的好处：`pytest tests/`、`pytest tools/tests/` 的 rootdir 都是仓库根，
conftest 链必经此文件。`pytest upstream/tests/` 的 rootdir 是 `upstream/`
（那边有自己的 pyproject.toml），本文件不会被加载 —— 那条链由
`upstream/tests/conftest.py` 自行安装。

只 `install()` 不 `flush()`：会话汇总由各子树 conftest 负责，避免同一份计数
被打印两遍。
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _install_egress_guard() -> None:
    spec = importlib.util.spec_from_file_location(
        "fstdd_pytest_egress_guard_root", _ROOT / "tools" / "pytest_egress_guard.py")
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.install()


_install_egress_guard()
