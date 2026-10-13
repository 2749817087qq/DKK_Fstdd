"""TC-TTR-005 —— 反向守卫：真实异常照抛，且实现不得宽捕获。

对应 spec: canonical/specs/code/test-teardown-resilience.yaml → SC-003

纪律出处：EXP-2026-0014（`except Exception: pass` 静默降级）+ KG-092（失败静默腐烂）。
本用例是 SC-001（放行 SystemExit）的**反向对照**：韧性层只能放行守卫签名，
不得演变成「吞掉一切」——否则会把真实故障一起埋掉，比原问题更危险。
"""
import re
from pathlib import Path

import pytest

import conftest as cf

CONFTEST = Path(cf.__file__)


def test_ttr_005_real_exception_propagates(tmp_path):
    """TC-TTR-005 / SC-003：非 SystemExit 的异常必须原样抛出（不被吞）。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")

    def _inner(_p):
        raise PermissionError("模拟真实删除失败")

    with pytest.raises(PermissionError):
        cf._guarded_delete(_inner, target)


def test_ttr_005_other_baseexception_propagates(tmp_path):
    """TC-TTR-005 / SC-003（AND）：其它 BaseException 子类同样照抛（不止 OSError 家族）。"""
    target = tmp_path / "victim.txt"
    target.write_text("x", encoding="utf-8")

    def _inner(_p):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        cf._guarded_delete(_inner, target)


def test_ttr_005_no_broad_catch_in_source():
    """TC-TTR-005 / SC-003：源码层面不得出现宽捕获（结构性保证，不靠行为抽样）。"""
    src = CONFTEST.read_text(encoding="utf-8")
    # 只取「可执行代码」的判据：注释/文档串里出现字样不算违规 ⇒ 逐行剥离注释后再判
    code_lines = []
    for line in src.splitlines():
        stripped = line.split("#", 1)[0]
        code_lines.append(stripped)
    code = "\n".join(code_lines)

    for pattern in (r"except\s+Exception", r"except\s+BaseException", r"except\s*:"):
        assert not re.search(pattern, code), (
            f"conftest.py 出现宽捕获 `{pattern}` —— 违反 SC-003（不得静默/不得吞真实异常）"
        )
