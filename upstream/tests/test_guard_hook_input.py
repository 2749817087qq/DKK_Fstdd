# -*- coding: utf-8 -*-
"""TC-GHI-001..004 — Guard 钩子 stdin 解析健壮性（change 2026-09-21-guard-hook-input-robustness）。

背景（真实缺陷，实测自日志）：
  `guard.py` 的 `_read_hook_input()` 在"stdin JSON 不可用"的 fallback 分支里
  写成 `return x,`（**尾逗号**）⇒ 返回 **1 元组**；调用方 `cmd_guard_check` 按
  `hook_path, hook_content = _read_hook_input()` 解包 ⇒ `ValueError: not enough
  values to unpack (expected 2, got 1)` ⇒ 钩子以 exit 1 崩掉并 **fail-open**
  （每日约 74 次，见 `~/.workbuddy-ai/logs/*/fstdd-hub__*.log`）。

判据（本文件守护）：
  1. `_read_hook_input()` **任何路径都返回 2 元组**（可解包）；
  2. 输入非法时**不抛异常**，返回 (None, None) 或 (path, "") 的**显式 fail-open**；
  3. 端到端：`cmd_guard_check` 在 stdin 非法时**不得抛 ValueError**。
"""
from __future__ import annotations

import io
import sys

import pytest

from fstdd.cli.commands import guard as guard  # 必须走包导入（guard.py 内有相对导入）


def _with_stdin(monkeypatch, text: str):
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))


# --------------------------------------------------------------------------
# 1) 直接测 _read_hook_input：任何路径都必须返回 2 元组
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "",                                            # 空
    "not json at all",                             # 非 JSON
    '{"tool_name": "Write"',                       # 截断 JSON（大 payload 常见）
    '{"tool_input": {"file_path": "D:\\\\tools\\\\FSTDD\\\\a.py"}}',   # 未转义 Windows 路径
    '{"file_path": "C:/x/y.py"',                   # 有 file_path 但 JSON 坏
    '{"file_path": "C:/x/y.py", "content": "hi"}', # 完整合法
])
def test_ghi_001_always_two_tuple(monkeypatch, raw):
    """任何输入都返回可解包的 2 元组（不得 1 元组、不得抛异常）。"""
    _with_stdin(monkeypatch, raw)
    out = guard._read_hook_input()
    assert isinstance(out, tuple), f"应返回 tuple，实际 {type(out)}"
    assert len(out) == 2, f"应返回 2 元组（历史缺陷为 1 元组）：{out!r}"
    path, content = out  # 必须能解包 —— 这就是历史崩溃点
    assert path is None or isinstance(path, str)
    assert content is None or isinstance(content, str)


def test_ghi_002_illegal_input_no_exception(monkeypatch):
    """非法输入 ⇒ 显式 fail-open，不抛异常。"""
    _with_stdin(monkeypatch, "{{{ 完全不是 JSON")
    path, content = guard._read_hook_input()   # 不得抛
    assert (path, content) == (None, None), "非法输入应显式 fail-open 为 (None, None)"


def test_ghi_003_fallback_recovers_file_path(monkeypatch):
    """JSON 坏但含 file_path ⇒ fallback 正则恢复路径，content 为空串（而非缺失）。"""
    _with_stdin(monkeypatch, '{"tool_name": "Write", "tool_input": {"file_path": "D:\\\\tools\\\\FSTDD\\\\x.py"')
    path, content = guard._read_hook_input()
    assert path is not None, "fallback 应恢复 file_path"
    assert "x.py" in path.replace("\\", "/")
    assert content == "", "content 缺失时必须是空串，不能是缺项"


# --------------------------------------------------------------------------
# 2) 端到端：cmd_guard_check 不得因 stdin 非法而抛 ValueError
# --------------------------------------------------------------------------

def test_ghi_004_end_to_end_no_valueerror(monkeypatch, tmp_path):
    """--hook-stdin 且 stdin 非法 ⇒ 走 fail-open，返回 int，不抛 ValueError。"""
    _with_stdin(monkeypatch, '{"file_path": "D:\\\\tools\\\\FSTDD\\\\x.py"')  # 坏 JSON
    monkeypatch.chdir(tmp_path)

    class _Args:
        hook_stdin = True
        check = True
        enforce_stdd = None
        json = False

    try:
        rc = guard.cmd_guard_check(_Args())
    except ValueError as e:      # 历史缺陷在这里炸
        pytest.fail(f"cmd_guard_check 不应抛 ValueError：{e}")
    assert isinstance(rc, int)


# --------------------------------------------------------------------------
# 5) 回归：无活跃 change 时「拦截」分支不得因作用域变量未绑定而崩（TC-GHI-005）
# --------------------------------------------------------------------------

def test_ghi_005_block_path_without_active_change_returns_2(monkeypatch, tmp_path):
    """无活跃流程时应返回 **2（拦截）**，不得抛 UnboundLocalError。

    实测缺陷：`scope_patterns` / `scope_in` 原先只在 `if active_dir:` 且
    `.fstdd.yaml` 存在的嵌套分支内赋值，而拦截分支在块外引用它们
    ⇒ `UnboundLocalError: cannot access local variable 'scope_in'`，
    钩子以 exit 1 结束。按 guard.py 约定（0=放行 / 2=拦截），exit 1 属
    **非阻塞错误** ⇒ 该拦截路径实际 fail-open，编辑被放行。

    为什么原 TC-GHI-004 没抓到：它用 `D:\\tools\\FSTDD\\x.py` 这类
    **Windows 绝对路径**，在 Windows 上被 `_is_inside_project` 判为「不在本项目内」
    而提前 return 0，走不到拦截分支；Linux 上它只是一个含反斜杠的文件名，
    相对解析后落在项目内，才触发。故本用例**显式使用项目内相对路径**，与平台无关。
    """
    _with_stdin(monkeypatch, '{"file_path": "x.py"}')
    monkeypatch.chdir(tmp_path)

    class _Args:
        hook_stdin = True
        check = True
        enforce_stdd = None
        json = False

    rc = guard.cmd_guard_check(_Args())
    assert rc == 2, (
        "无活跃流程时应以 2 拦截；实测 rc=%r —— 若为 1 则说明走了异常路径，"
        "平台会把钩子当成「非阻塞错误」而放行编辑" % rc
    )
