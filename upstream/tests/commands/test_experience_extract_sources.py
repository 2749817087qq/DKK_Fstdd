"""Slice 1 契约测试：experience extract 抽取源扩展（C1 / REQ-001，TC-EEXT-001..005）。

背景：`_cmd_extract` 原本只认 `test-report.md`（仅 12 类失败模式表格）。
本变更把抽取源扩至 `design-adjustments.md`（设计偏离留痕）与
`adjudication-log.tsv`（同 eid 多版本裁决留痕），并保持 test-report 路径逐条不回归。

对应 spec：
- SC-001 默认源仍从 test-report 抽取（既有路径不退化）
- SC-002 `--source design-adjustments` 从设计偏离产出草稿
- SC-003 `--source adjudication` 从裁定日志产出草稿
- SC-004 `--all` 三类源合并、按 experience_id/pattern 去重
- SC-005 扩展后 test-report 路径结果与扩展前逐条一致（无回归）
"""
import argparse
from pathlib import Path

import yaml

CHANGE_NAME = "2026-10-11-fixture-change"

# ── 夹具内容 ────────────────────────────────────────────────────────────

TEST_REPORT = """# Test Report

## 失败模式检查

| 失败模式 | 状态 | 说明 |
|---------|------|------|
| contract_gap | FAIL | 契约断层：声明字段与实现不一致 |
| hallucination | PASS | 无幻觉 |
| runtime_deviation | WARNING | 存在不稳定测试 |
"""

DESIGN_ADJUSTMENTS = """# 设计调整说明

## 调整汇总

| # | 调整类型 | 涉及文档 | 严重程度 | 调整阶段 | 影响 TC | 用户已知 |
|---|---------|---------|---------|---------|---------|---------|
| 1 | 技术方案变更 | design.md | Major | Phase 3 | TC-AAA-001 | 是 |
| 2 | spec Scenario 补充 | spec.md | Minor | Phase 3 | TC-BBB-001 | 是 |

## 调整详细说明

### 调整 1: 加密实现由 cryptography 库改为 openssl 子进程

- **原始设计**: 使用 cryptography 库的 AESGCM
- **调整内容**: 改为调用 openssl CLI 子进程
- **调整原因**: 运行环境 cryptography 为空的命名空间包
- **影响范围**: _exp_crypto.py
- **影响 TC**: TC-AAA-001
- **调整阶段**: Phase 3
- **用户已知**: 是

### 调整 2: 补充一条边界 Scenario

- **原始设计**: 仅覆盖 318B 上限
- **调整内容**: 增加 319B 拒绝场景
- **调整原因**: 边界值需双向断言
- **影响范围**: spec.md
- **影响 TC**: TC-BBB-001
- **调整阶段**: Phase 3
- **用户已知**: 是
"""

ADJUDICATION_LOG = (
    "EXP-2026-0013\tKEEP_STDD_REPO\tversions=2\tfrom=['stdd-repo', 'FSTDD003']\n"
    "EXP-2026-0014\tKEEP_STDD_REPO\tversions=3\tfrom=['stdd-repo', 'FSTDD003', 'home-FSTDD']\n"
    "EXP-2026-0013\tKEEP_STDD_REPO\tversions=2\tfrom=['stdd-repo', 'FSTDD003']\n"
)


# ── 工具 ────────────────────────────────────────────────────────────────


def _make_args(subcommand="extract", **kwargs):
    ns = argparse.Namespace(command="experience", subcommand=subcommand, dry_run=False, verbose=0)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _setup_project(root: Path) -> Path:
    """建最小项目骨架 + 一个 change 目录（含三类源夹具）。"""
    (root / ".fstdd" / "config.d").mkdir(parents=True, exist_ok=True)
    (root / ".fstdd" / "experiences").mkdir(parents=True, exist_ok=True)
    (root / ".fstdd" / "config.d" / "project.yaml").write_text(
        "project:\n  language: python\n", encoding="utf-8"
    )
    change = root / ".fstdd" / "changes" / CHANGE_NAME
    change.mkdir(parents=True, exist_ok=True)
    (change / "test-report.md").write_text(TEST_REPORT, encoding="utf-8")
    (change / "design-adjustments.md").write_text(DESIGN_ADJUSTMENTS, encoding="utf-8")
    (change / "adjudication-log.tsv").write_text(ADJUDICATION_LOG, encoding="utf-8")
    return change


def _drafts(exp_dir: Path) -> list[dict]:
    out = []
    for p in sorted(exp_dir.glob("EXP-*.md")):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm = yaml.safe_load(text.split("---", 2)[1]) or {}
        fm["_file"] = p.name
        out.append(fm)
    return out


def _extract(exp_dir: Path):
    from fstdd.cli.commands.experience import _cmd_extract
    return _cmd_extract


# ── TC-EEXT-001..005 ────────────────────────────────────────────────────


def test_eext001_default_extract_from_test_report(tmp_path, monkeypatch):
    """TC-EEXT-001 / SC-001：默认源仍从 test-report 抽取，条数 > 0，且不退化。"""
    monkeypatch.chdir(tmp_path)
    exp_dir = _setup_project(tmp_path)  # noqa: F841
    edir = tmp_path / ".fstdd" / "experiences"
    _extract(edir)(_make_args(), edir)
    drafts = _drafts(edir)
    assert len(drafts) > 0
    assert all(d.get("lifecycle_state") == "discovered" for d in drafts)
    # 既有行为：contract_gap FAIL 必须被抽到
    assert any(d.get("category") == "contract_gap" for d in drafts)


def test_eext002_extract_from_design_adjustments(tmp_path, monkeypatch):
    """TC-EEXT-002 / SC-002：--source design-adjustments 从设计偏离产出草稿。

    夹具含 2 个 `### 调整 N:` 小节 → 应产出 2 条草稿，且内容取自偏离记录
    （不是 test-report）。
    """
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    _extract(edir)(_make_args(source="design-adjustments"), edir)
    drafts = _drafts(edir)
    assert len(drafts) == 2, [d.get("pattern") for d in drafts]
    blob = " ".join((d.get("pattern") or "") + (d.get("root_cause") or "")
                    + (d.get("detection_trigger") or "") for d in drafts)
    assert "openssl" in blob or "加密实现" in blob
    assert "Scenario" in blob or "边界" in blob


def test_eext003_extract_from_adjudication(tmp_path, monkeypatch):
    """TC-EEXT-003 / SC-003：--source adjudication 从裁定日志产出草稿。

    夹具 3 行、其中 EXP-2026-0013 重复 → 去重后 2 条，且必须携带 eid 信息。
    """
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    _extract(edir)(_make_args(source="adjudication"), edir)
    drafts = _drafts(edir)
    assert len(drafts) == 2, [d.get("pattern") for d in drafts]
    blob = " ".join((d.get("pattern") or "") for d in drafts)
    assert "EXP-2026-0013" in blob and "EXP-2026-0014" in blob


def test_eext004_extract_all_merges_and_dedups(tmp_path, monkeypatch):
    """TC-EEXT-004 / SC-004：--all 三类源合并，按 experience_id/pattern 去重。"""
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"
    _extract(edir)(_make_args(all=True), edir)
    all_drafts = _drafts(edir)

    blob = " ".join((d.get("pattern") or "") for d in all_drafts)
    # 三类源的标志性条目都应出现
    assert any(d.get("category") == "contract_gap" for d in all_drafts), "缺 test-report 源"
    assert "openssl" in blob or "加密实现" in blob, "缺 design-adjustments 源"
    assert "EXP-2026-0013" in blob, "缺 adjudication 源"
    # 去重：无重复 pattern
    pats = [d.get("pattern") for d in all_drafts]
    assert len(pats) == len(set(pats))


def test_eext005_test_report_path_no_regression(tmp_path, monkeypatch):
    """TC-EEXT-005 / SC-005：扩展后 test-report 路径结果与扩展前逐条一致。"""
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    edir = tmp_path / ".fstdd" / "experiences"

    # 仅 test-report（显式 source 与默认 source 结果一致）
    _extract(edir)(_make_args(source="test-report"), edir)
    explicit = _drafts(edir)
    for f in edir.glob("EXP-*.md"):
        f.unlink()
    _extract(edir)(_make_args(), edir)
    default = _drafts(edir)

    assert len(explicit) == len(default)
    assert [d.get("pattern") for d in explicit] == [d.get("pattern") for d in default]
    # 既有行为：test-report 的 contract_gap FAIL 应被抽到
    assert any(d.get("category") == "contract_gap" for d in default)
