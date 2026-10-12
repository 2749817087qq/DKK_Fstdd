"""TC 追溯性（traceability）：change 2026-10-11-share-hardening-audit-fixes 的计划 TC 必须都有实现。

背景（框架缺陷，已记录）：`fstdd ci check-failures` 的「TC 实现覆盖」检查**硬编码**扫描
``project_root/tests``（见 `upstream/fstdd/cli/commands/ci.py`），而本仓框架侧测试位于
``upstream/tests/``，导致该检查对 upstream 测试恒为假红。

本测试把追溯性判据显式化并**同时扫描两棵测试树**，并把计划 TC 清单冻结为常量，
防止「test-plan 新增 TC 但无实现」与「实现漂移」两种退化。

两条 **suite 级** TC 的覆盖方式（非独立测试函数）：
  · TC-SEG-011 —— 运行 `upstream/tests/test_silent_share.py`（23 passed，见 C2 全量回归）；
  · TC-ISR-010 —— 运行 `pytest upstream/tests tests` 全量回归（无新增失败）。
二者在 `EXPECTED_TCS` 中登记，由本文件保证「计划 TC 清单不漂移」。
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHANGE_DIR = REPO / ".fstdd" / "changes" / "2026-10-11-share-hardening-audit-fixes"
TEST_TREES = (REPO / "tests", REPO / "upstream" / "tests")

# 冻结的计划 TC 清单（与 test-plan.md 一致）：
#   · 22 个本变更 TC（TC-SEG-001..012 + TC-ISR-001..010）
#   · 2 个既有交叉引用 TC：TC-SOS-001（§三 矩阵引用的既有脱敏基线）、
#     TC-EPR-002（§六 证据记录的观测时点要求）
EXPECTED_TCS = (
    "TC-SEG-001", "TC-SEG-002", "TC-SEG-003", "TC-SEG-004", "TC-SEG-005",
    "TC-SEG-006", "TC-SEG-007", "TC-SEG-008", "TC-SEG-009", "TC-SEG-010",
    "TC-SEG-011", "TC-SEG-012",
    "TC-ISR-001", "TC-ISR-002", "TC-ISR-003", "TC-ISR-004", "TC-ISR-005",
    "TC-ISR-006", "TC-ISR-007", "TC-ISR-008", "TC-ISR-009", "TC-ISR-010",
    "TC-SOS-001", "TC-EPR-002",
)

# 本变更自有 TC（不含既有交叉引用）
OWN_TCS = tuple(t for t in EXPECTED_TCS if t.startswith(("TC-SEG-", "TC-ISR-")))


def _planned_tcs() -> set:
    plan = (CHANGE_DIR / "test-plan.md").read_text(encoding="utf-8")
    return set(re.findall(r"(TC-[A-Z]+-\d{3})", plan))


def _implemented_tcs(planned: set) -> set:
    found = set()
    for tree in TEST_TREES:
        if not tree.exists():
            continue
        for f in tree.rglob("test_*.py"):
            content = f.read_text(encoding="utf-8")
            found |= {tc for tc in planned if tc in content}
    return found


def test_plan_tc_list_matches_frozen_expectation():
    """test-plan.md 的 TC 清单必须与冻结常量一致（防止计划与追溯表漂移）。"""
    assert _planned_tcs() == set(EXPECTED_TCS), (
        f"计划 TC 与冻结清单不一致: 计划={sorted(_planned_tcs())}"
    )


def test_all_planned_tcs_have_implementation():
    """每个计划 TC 都必须能在测试树（tests/ 或 upstream/tests/）中找到实现。"""
    planned = _planned_tcs()
    missing = sorted(planned - _implemented_tcs(planned))
    assert not missing, f"计划 TC 无实现测试: {missing}"


def test_planned_tc_count():
    """本变更自有 TC 数应为 22（TC-SEG-001..012 + TC-ISR-001..010）。"""
    assert len(OWN_TCS) == 22
    assert len(EXPECTED_TCS) == 24
    assert len(_planned_tcs()) == 24
