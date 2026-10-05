# -*- coding: utf-8 -*-
"""TC-UBL-001..006：上游基线快照文档（`docs/UPSTREAM_BASELINE.md`）静态一致性断言。

对应 test-plan.md「功能 2：上游基线对齐」（REQ-001..003 / SC-001..006）。

本文件**不联网**：只断言已固化的实测值在位、与机器可读源一致，且快照数字未在
`NOTICE.md` / `README.md` 处重复维护（单一事实源）。观测时点见文档 §一。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "UPSTREAM_BASELINE.md"
NOTICE = REPO_ROOT / "NOTICE.md"
README = REPO_ROOT / "README.md"
VERSION_YAML = REPO_ROOT / ".fstdd" / "version.yaml"
PROJECT_YAML = REPO_ROOT / ".fstdd" / "config.d" / "project.yaml"
KERNEL_PYPROJECT = REPO_ROOT / "upstream" / "pyproject.toml"

# E 轴实测锚（观测时点：2026-10-05T12:02:00+08:00，经 ssh fstdd-hub 只读）
E_TAG = "v3.0.5"
E_HEAD_SHA = "b9a4af62b5f4fd2747884c0a61febbc341792ac2"
E_PUSHED_AT = "2026-08-17T15:25:43Z"
EXP_REPO = "leonai42/stdd-experiences"
OUR_EXP_REPO = "2749817087qq/Fstdd-experiences"
EXP_PUSHED_AT = "2026-10-05T00:31:25Z"

OBSERVED_AT_RE = re.compile(
    r"observed_at\s*\|?\s*`?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z))`?"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc() -> str:
    assert DOC.exists(), f"缺少基线快照文档：{DOC}"
    return _read(DOC)


def test_ubl_001_snapshot_doc_has_required_evidence(doc):
    # TC-UBL-001 / SC-001
    """文档存在且含必备证据段：观测时点 / 基线 sha / E 全套 / 通道排除。"""
    assert OBSERVED_AT_RE.search(doc), "缺少带时区的 observed_at"
    assert re.search(r"observed_base_git_sha\s*\|?\s*`?[0-9a-f]{40}`?", doc), \
        "缺少 observed_base_git_sha（观测时本仓 base git sha）"
    for token in (E_TAG, E_HEAD_SHA, E_PUSHED_AT):
        assert token in doc, f"E 轴证据缺失：{token}"
    assert "Releases" in doc and ("空" in doc or "0 条" in doc), "缺少 Releases 状态"
    assert "master" in doc, "缺少分支状态"
    assert "Gitee" in doc and "PyPI" in doc, "缺少通道排除结论（Gitee / PyPI）"


def test_ubl_002_snapshot_values_match_measurement(doc):
    # TC-UBL-002 / SC-002
    """快照数值与实测一致，记录观测通道，且无凭证 / 内网私密路径。"""
    assert E_TAG in doc and E_HEAD_SHA in doc and E_PUSHED_AT in doc, "快照数值与实测不一致"
    assert "ssh fstdd-hub" in doc, "缺少观测通道记录"
    forbidden = (
        "ghp_", "github_pat_", "BEGIN OPENSSH PRIVATE KEY",
        "PRIVATE KEY-----", "Authorization:", "/home/ubuntu/.ssh", "api_token",
    )
    hits = [f for f in forbidden if f in doc]
    assert not hits, f"文档疑似含凭证 / 私密路径：{hits}"


def test_ubl_003_leading_gap_list_consistent_with_machine_sources(doc):
    # TC-UBL-003 / SC-003
    """领先量清单覆盖 K / R 两轴，且版本数值与机器可读源一致。"""
    version = yaml.safe_load(_read(VERSION_YAML))
    kernel = str(version["upstream_version"])
    release = str(version["fstdd_version"])

    with KERNEL_PYPROJECT.open("rb") as fh:
        pyproject = tomllib.load(fh)
    assert pyproject["project"]["version"] == kernel, \
        "upstream/pyproject.toml 与 .fstdd/version.yaml 的内核版本不一致"
    assert release in _read(PROJECT_YAML), \
        ".fstdd/config.d/project.yaml 未记录发行版号"

    assert f"`{kernel}`" in doc, f"领先量清单缺内核轴 K={kernel}"
    assert f"`{release}`" in doc, f"领先量清单缺发行版轴 R={release}"
    assert "内核" in doc and "发行版" in doc, "未标明 K / R 两轴语义"


def test_ubl_004_experience_repo_is_readonly_reference(doc):
    # TC-UBL-004 / SC-004
    """经验库对标段：非我方回传目标 + 指明我方目标 + 记录推送观测值。"""
    assert EXP_REPO in doc, "未记录上游经验库"
    assert "非我方回传目标" in doc, "未明确 leonai42/stdd-experiences 非回传目标"
    assert OUR_EXP_REPO in doc, "未指明我方回传目标"
    assert EXP_PUSHED_AT in doc, "未记录上游经验库最近推送观测值"


def test_ubl_005_our_node_prefix_count_is_measured(doc):
    # TC-UBL-005 / SC-005
    """给出我方 node 前缀条目数的实测值（0 亦为有效实测值）。"""
    lines = [ln for ln in doc.splitlines() if "我方 node 前缀条目数" in ln]
    assert lines, "缺少「我方 node 前缀条目数」记录"
    assert any("`0`" in ln for ln in lines), "未给出实测计数（0 为有效实测值）"
    assert "FSTDD003" in doc and "FSTDD-003" in doc, \
        "缺少计数口径（node 前缀形如 FSTDD003 / FSTDD-003）"
    assert "实测" in doc, "未标注为实测值而非估计"
    assert OBSERVED_AT_RE.search(doc), "计数未与观测时点绑定"


def test_ubl_006_snapshot_numbers_live_in_single_source(doc):
    # TC-UBL-006 / SC-006
    """NOTICE / README 不复制快照数字，只链接单一事实源。"""
    assert E_HEAD_SHA in doc and E_PUSHED_AT in doc, "快照数字未落在单一事实源"
    for path in (NOTICE, README):
        text = _read(path)
        assert E_HEAD_SHA not in text, \
            f"{path.name} 复制了快照 sha（应只链接 docs/UPSTREAM_BASELINE.md）"
        assert E_PUSHED_AT not in text, \
            f"{path.name} 复制了 pushed_at（应只链接 docs/UPSTREAM_BASELINE.md）"
        assert "UPSTREAM_BASELINE.md" in text, f"{path.name} 未链接基线快照文档"