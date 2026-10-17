"""pytest fixtures — 提供临时文件系统和示例 change 目录。"""
import importlib.util
from pathlib import Path

import pytest
import yaml
from datetime import date


# ---------------------------------------------------------------------------
# 出站守卫（2026-10-18 审计 F2）
# ---------------------------------------------------------------------------
# `upstream/` 有自己的 pyproject.toml ⇒ 单跑 `pytest upstream/tests/` 时 rootdir 就是
# `upstream/`，conftest 链从它起算，**仓库根的 tests/conftest.py 根本不被加载**。
# 于是 tests/ 里那套 ssh/scp 生产守卫对这里完全失效 —— 而本目录的
# `test_silent_share.py` 恰恰要靠 fixture 手动禁用 scp 才不出站。
# 规则实现只有一份（tools/pytest_egress_guard.py），两侧 conftest 各自 install()。
def _install_egress_guard() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "fstdd_pytest_egress_guard", root / "tools" / "pytest_egress_guard.py")
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.install()


_install_egress_guard()


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """创建最小 STDD 项目骨架。"""
    (tmp_path / ".fstdd").mkdir(parents=True)
    (tmp_path / ".fstdd" / "changes").mkdir(parents=True)
    (tmp_path / ".fstdd" / "specs").mkdir(parents=True)
    (tmp_path / ".fstdd" / "archive").mkdir(parents=True)
    (tmp_path / ".fstdd" / "templates").mkdir()
    (tmp_path / ".fstdd" / "skills").mkdir()
    return tmp_path


@pytest.fixture
def sample_change(temp_project: Path) -> Path:
    """创建带 .fstdd.yaml 和基本文件的示例 change 目录。"""
    today = date.today().isoformat()
    change_dir = temp_project / ".fstdd" / "changes" / f"{today}-test-feature"
    change_dir.mkdir(parents=True)
    (change_dir / "specs").mkdir()

    state = {
        "version": "2.0",
        "change_id": f"{today}-test-feature",
        "status": "active",
        "current_phase": "understand",
        "phases": {
            "understand": {"status": "pending"},
            "spec": {"status": "pending"},
            "build": {"status": "pending"},
            "deliver": {"status": "pending"},
        },
    }
    with open(change_dir / ".fstdd.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    (change_dir / "proposal.md").write_text("# Proposal\n\nTest proposal", encoding="utf-8")
    (change_dir / "design.md").write_text("# Design\n\nTest design", encoding="utf-8")
    (change_dir / "test-plan.md").write_text("# Test Plan\n\nTest plan content", encoding="utf-8")

    return change_dir


@pytest.fixture
def sample_change_with_specs(sample_change: Path) -> Path:
    """在示例 change 中添加 spec 文件。"""
    spec_content = """# Capability: TEST

## NEW Requirements

### Requirement: 示例需求

#### Scenario: 正常场景

- **GIVEN** 用户输入有效
- **WHEN** 系统处理
- **THEN** 系统 SHALL 返回正确结果
- **AND** 结果格式为 JSON
"""
    (sample_change / "specs" / "test.md").write_text(spec_content, encoding="utf-8")
    # 更新 test-plan 包含匹配的 TC-ID（validate 检查 TC 数 >= Scenario 数）
    tp = """# Test Plan
#### 案例 1 — 正常场景
| **ID** | TC-TEST-001 |
| **预期结果** | 系统返回正确结果 |
"""
    (sample_change / "test-plan.md").write_text(tp, encoding="utf-8")
    return sample_change


@pytest.fixture
def archived_change(temp_project: Path) -> Path:
    """在 archive 中创建已归档的 change。"""
    today = date.today().isoformat()
    archive_dir = temp_project / ".fstdd" / "archive" / f"{today}-archived-feature"
    archive_dir.mkdir(parents=True)
    state = {
        "version": "2.0",
        "change_id": f"{today}-archived-feature",
        "status": "archived",
        "current_phase": "deliver",
        "phases": {
            "understand": {"status": "completed"},
            "spec": {"status": "completed"},
            "build": {"status": "completed"},
            "deliver": {"status": "completed"},
        },
    }
    with open(archive_dir / ".fstdd.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False)
    return archive_dir
