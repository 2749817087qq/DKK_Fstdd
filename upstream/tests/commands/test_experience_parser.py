"""契约测试：_load_experience 双块 / 单块 / 冲突键解析（C5，TC-ELC-001..003）。

背景：inbox 导入的经验文件为「HTML 注释头 + 第1块 {exported_at, sanitized}
+ 第2块真身 {experience_id, category, severity}」结构。原实现
``split("---", 2)[1]`` 只取首个块，导致真身被静默丢弃（P1 bug）。
本测试验证修复后解析全部块并合并（后块覆盖前块冲突键）。
"""
from pathlib import Path

import pytest


def _load_experience():
    from fstdd.cli.commands.experience import _load_experience as fn
    return fn


def test_elc001_dual_block_returns_true_body(tmp_path):
    """TC-ELC-001: inbox 双块文件应返回合并后的真身（experience_id/category/severity 非空）。"""
    text = (
        "<!-- fstdd-inbox\n"
        "experience_id: EXP-DUAL-A1\n"
        "author: anonymous\n"
        "node_id: FSTDD001\n"
        "-->\n\n"
        "---\n"
        "exported_at: 2026-09-26\n"
        "sanitized: true\n"
        "---\n"
        "<!-- fstdd-inbox\n"
        "experience_id: EXP-DUAL-A1\n"
        "author: (anonymous)\n"
        "-->\n\n"
        "---\n"
        "experience_id: EXP-DUAL-A1\n"
        "category: tooling\n"
        "severity: medium\n"
        "occurrences: 1\n"
        "lifecycle_state: deposited\n"
        "---\n"
        "## body\n"
    )
    p = tmp_path / "EXP-DUAL-A1.md"
    p.write_text(text, encoding="utf-8")
    data = _load_experience()(p)
    assert data is not None
    assert data.get("experience_id") == "EXP-DUAL-A1"
    assert data.get("category") == "tooling"
    assert data.get("severity") == "medium"
    assert data.get("lifecycle_state") == "deposited"


def test_elc002_single_block_consistent(tmp_path):
    """TC-ELC-002: 单块文件返回完整字段，与修复前行为一致（回归保底）。"""
    text = (
        "<!-- fstdd-inbox\n"
        "experience_id: EXP-SINGLE-1\n"
        "-->\n\n"
        "---\n"
        "experience_id: EXP-SINGLE-1\n"
        "category: runtime_pitfall\n"
        "severity: high\n"
        "occurrences: 2\n"
        "---\n"
        "# body\n"
    )
    p = tmp_path / "EXP-SINGLE-1.md"
    p.write_text(text, encoding="utf-8")
    data = _load_experience()(p)
    assert data is not None
    assert data["experience_id"] == "EXP-SINGLE-1"
    assert data["category"] == "runtime_pitfall"
    assert data["severity"] == "high"
    # occurrences 经 _coerce_numeric_fields 归一为整数
    assert data["occurrences"] == 2
    assert isinstance(data["occurrences"], int)


def test_elc003_conflict_later_block_wins(tmp_path):
    """TC-ELC-003: 两 block 含同键异值时，以靠后 block 为准。"""
    text = (
        "---\n"
        "experience_id: EXP-CONF-1\n"
        "severity: low\n"
        "---\n"
        "---\n"
        "experience_id: EXP-CONF-1\n"
        "severity: high\n"
        "---\n"
        "body\n"
    )
    p = tmp_path / "EXP-CONF-1.md"
    p.write_text(text, encoding="utf-8")
    data = _load_experience()(p)
    assert data is not None
    assert data["severity"] == "high"  # 后块覆盖前块
    assert data["experience_id"] == "EXP-CONF-1"


def test_elc_no_frontmatter_returns_none(tmp_path):
    """边界：无 frontmatter 的纯 markdown 返回 None。"""
    p = tmp_path / "EXP-PLAIN.md"
    p.write_text("# just markdown\nno frontmatter here\n", encoding="utf-8")
    assert _load_experience()(p) is None


def test_elc_integration_real_dual_block_files():
    """回归：stdd-repo 既有双块经验文件（如 EXP-20260915-A1）修复后能回读真身。"""
    exp_dir = Path(__file__).resolve().parents[3] / ".fstdd" / "experiences"
    if not exp_dir.exists():
        pytest.skip("stdd-repo experiences dir not found")
    sample = exp_dir / "EXP-20260915-A1.md"
    if not sample.exists():
        pytest.skip("sample dual-block file not present")
    data = _load_experience()(sample)
    assert data is not None
    assert data.get("experience_id") == "EXP-20260915-A1"
    assert data.get("category") == "tooling"
    assert data.get("severity") == "medium"
