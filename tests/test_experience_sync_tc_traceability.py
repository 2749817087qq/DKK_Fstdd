"""TC 追溯性（traceability）：change 2026-10-11-experience-center-node-sync 的计划 TC 必须都有实现测试。

背景（框架缺陷，已记录）：`fstdd ci check-failures` 的「TC 实现覆盖」检查**硬编码**扫描
``project_root/tests``（见 `upstream/fstdd/cli/commands/ci.py` 的 ``tests_dir = project_root / "tests"``），
而本仓框架侧测试位于 ``upstream/tests/``，导致该检查对 upstream 测试**恒为 0/N 假红**。

本测试把追溯性判据显式化并**同时扫描两棵测试树**，同时把计划 TC 清单冻结为常量，
防止「test-plan 新增 TC 但无实现」与「实现漂移」两种退化。
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST_TREES = (REPO / "tests", REPO / "upstream" / "tests")


def _change_dir() -> Path:
    """change 目录可能在 ``changes/``（在办）或 ``archive/``（已归档）。

    2026-10-11 修复：本 change 已 DELIVER 归档，原实现硬编码 ``changes/`` 路径
    ⇒ 归档后 3 个用例全部 FileNotFoundError。追溯性必须在归档后仍然成立。
    """
    name = "2026-10-11-experience-center-node-sync"
    for base in ("changes", "archive"):
        p = REPO / ".fstdd" / base / name
        if p.is_dir():
            return p
    return REPO / ".fstdd" / "changes" / name


CHANGE_DIR = _change_dir()

# 冻结的计划 TC 清单（与 test-plan.md 的 24 个本变更 TC + 1 个既有交叉引用 TC 一致）
EXPECTED_TCS = (
    "TC-EEXT-001", "TC-EEXT-002", "TC-EEXT-003", "TC-EEXT-004", "TC-EEXT-005",
    "TC-EAUT-001", "TC-EAUT-002", "TC-EAUT-003", "TC-EAUT-004",
    "TC-ECNS-001", "TC-ECNS-002", "TC-ECNS-003", "TC-ECNS-004", "TC-ECNS-005",
    "TC-ESEC-001", "TC-ESEC-002", "TC-ESEC-003", "TC-ESEC-004", "TC-ESEC-005",
    "TC-ECON-001", "TC-ECON-002", "TC-ECON-003",
    "TC-ESAF-001", "TC-ESAF-002",
    "TC-EPR-002",
)


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
    implemented = _implemented_tcs(planned)
    missing = sorted(planned - implemented)
    assert not missing, f"计划 TC 无实现测试: {missing}"


def test_planned_tc_count():
    """本变更的计划 TC 数应为 24（+1 既有交叉引用 TC-EPR-002）。"""
    assert len(_planned_tcs()) == 25
    assert len([t for t in EXPECTED_TCS if t != "TC-EPR-002"]) == 24
