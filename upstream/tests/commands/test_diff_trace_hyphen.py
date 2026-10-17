"""TC-CTR-004 — diff/trace 对连字符命名测试文件的识别（REQ-CTR-001）。

同根因：下游多层次agent 的 EXP-2026-0001 类假红（本仓同名编号为 Guard 阶段门，非此语义）。

subprocess 级 CLI 测试。diff.py:99 / trace.py:95 原各自 `rglob("test_*.py")`，
对 `tests/test-*.py` 结构性失明（本仓及下游的测试文件命名惯例）：

- RED目标（修复前）：
  - `fstdd trace TC-HYP-001`：能定位 test-plan，但 tests/ 扫描无产出
    （无「测试: tests/test-hyphen.py」行）；
  - `fstdd diff <change>`：源码列能显示 tests\\test-hyphen.py（引用搜索走 *.py），
    但「测试函数」列为空（函数定位走 test_*.py 失明）。
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # upstream/
FSTDD_CLI = REPO_ROOT / "bin" / "fstdd"

CHANGE_NAME = "2026-01-01-hyphen-change"
TEST_PLAN_BODY = """\
# Test Plan

#### 案例 1 — 连字符命名测试文件识别

| **ID** | TC-HYP-001 |
|---|---|
| **预置条件** | tests/ 下仅存在 test-hyphen.py |
| **输入** | `fstdd trace TC-HYP-001` / `fstdd diff` |
| **预期结果** | 识别连字符命名测试文件及其测试函数 |
"""

TEST_FILE_BODY = """\
def test_hyphen_named_file():
    # TC-HYP-001 应被 diff/trace 识别
    assert True
"""


def _setup_project(tmp_path):
    """造一个含 test-plan（TC-HYP-001）+ tests/test-hyphen.py 的临时项目。"""
    change_dir = tmp_path / ".fstdd" / "changes" / CHANGE_NAME
    change_dir.mkdir(parents=True)
    (change_dir / ".fstdd.yaml").write_text("change_id: test", encoding="utf-8")
    (change_dir / "test-plan.md").write_text(TEST_PLAN_BODY, encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test-hyphen.py").write_text(TEST_FILE_BODY, encoding="utf-8")


def _run_cli(tmp_path, *cli_args):
    """跑 fstdd CLI（对齐仓库既有 run_cli 模式：UTF-8 父子编码 + timeout 防抖）。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(FSTDD_CLI), *cli_args],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    return result


class TestDiffTraceHyphenRecognition:
    """TC-CTR-004：diff/trace 子命令经 iter_test_files 识别连字符测试文件。"""

    def test_trace_finds_hyphen_named_test_file(self, tmp_path):
        """TC-CTR-004a: `fstdd trace TC-HYP-001` 定位 tests/test-hyphen.py 及其函数。"""
        _setup_project(tmp_path)

        result = _run_cli(tmp_path, "trace", "TC-HYP-001")
        assert result.returncode == 0, f"trace 非零退出: {result.stdout}{result.stderr}"
        assert "测试: tests/test-hyphen.py" in result.stdout.replace("\\", "/"), (
            f"trace 未识别连字符测试文件: {result.stdout}"
        )
        assert "函数: def test_hyphen_named_file" in result.stdout, (
            f"trace 未定位测试函数: {result.stdout}"
        )

    def test_diff_fills_test_function_for_hyphen_named_file(self, tmp_path):
        """TC-CTR-004b: `fstdd diff` 的「测试函数」列填上连字符文件中的函数。"""
        _setup_project(tmp_path)

        result = _run_cli(tmp_path, "diff", CHANGE_NAME)
        assert result.returncode == 0, f"diff 非零退出: {result.stdout}{result.stderr}"
        assert "test_hyphen_named_file" in result.stdout, (
            f"diff 测试函数列为空（连字符文件漏扫）: {result.stdout}"
        )
        assert "未覆盖" not in result.stdout, f"diff 误报未覆盖: {result.stdout}"
