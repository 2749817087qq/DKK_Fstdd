"""TC 追溯性（traceability）：change 2026-10-22-installation-id-backfill 的计划 TC 必须都有实现测试。

背景（框架缺陷，已记录于 2026-10-11-experience-center-node-sync）：
`fstdd ci check-failures` 的「TC 实现覆盖」检查**硬编码**扫描
``project_root/tests``（见 `upstream/fstdd/cli/commands/ci.py` 的
``tests_dir = project_root / "tests"``），而本仓框架侧测试位于 ``upstream/tests/``，
导致该检查对 upstream 测试**恒为 0/N 假红**。

本测试把追溯性判据显式化并**同时扫描两棵测试树**，同时把计划 TC 清单冻结为常量，
防止「test-plan 新增 TC 但无实现」与「实现漂移」两种退化。
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST_TREES = (REPO / "tests", REPO / "upstream" / "tests")


def _change_dir() -> Path:
    """change 目录可能在 ``changes/``（在办）或 ``archive/``（已归档）。"""
    name = "2026-10-22-installation-id-backfill"
    for base in ("changes", "archive"):
        p = REPO / ".fstdd" / base / name
        if p.is_dir():
            return p
    return REPO / ".fstdd" / "changes" / name


CHANGE_DIR = _change_dir()

# 冻结的计划 TC 清单（与 test-plan.md 的 9 个 TC 一致）
EXPECTED_TCS = (
    "TC-IID-008", "TC-IID-009", "TC-IID-010", "TC-IID-011",
    "TC-IID-012", "TC-IID-013", "TC-IID-014", "TC-IID-015",
    "TC-IID-016",
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
            content = f.read_text(encoding="utf-8", errors="replace")
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
    """本变更的计划 TC 数应为 9（IID 008~016）。"""
    assert len(_planned_tcs()) == 9
    assert all(t.startswith("TC-IID-") for t in EXPECTED_TCS)


def test_ci_check_scope_is_known_false_red():
    """固化「ci check-failures 的 TC 覆盖对 upstream 测试假红」这一已知缺陷。

    判据：`ci.py` 里 tests_dir 仍是 `project_root / "tests"`。
    哪天上游把它改成同时扫两棵树，本用例会红 —— 那时应删除本用例并改真实断言。
    """
    ci_src = (REPO / "upstream" / "fstdd" / "cli" / "commands" / "ci.py").read_text(
        encoding="utf-8"
    )
    assert 'tests_dir = project_root / "tests"' in ci_src, (
        "ci.py 的 TC 覆盖扫描范围已变化，请更新本用例（可能已修复假红）"
    )
