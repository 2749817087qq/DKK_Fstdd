"""TC-CHI-001 / TC-CHI-002 / TC-CHI-003 —— canonical 双轨哈希一致性。

背景（change 2026-10-06-legacy-debt-cleanup）：
    V2.9.2 Canonical-First 下 `canonical/proposals/<change>.yaml` 是**唯一事实源**，
    `proposal.md` 是渲染产物，其 `source_hash` 的语义是「渲染自哪个 YAML 版本」。
    维护者手工改 YAML 后若忘了重渲染，MD 的 `source_hash` 就会与实际内容脱节，
    表现为 `canon verify` 的 DC-HASH 判据 1/2 —— 一种**永久门禁噪声**。

    本模块把「YAML 与 MD 指纹一致」固化为回归断言，防止同类欠账再次积累。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "upstream" / "bin" / "fstdd"
PROPOSALS_DIR = REPO / "canonical" / "proposals"
THIS_CHANGE = "2026-10-06-legacy-debt-cleanup"


def _canon_verify(change: str) -> str:
    """执行 `fstdd canon verify <change>` 并返回合并输出。"""
    result = subprocess.run(
        [sys.executable, str(CLI), "canon", "verify", change],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO), timeout=120,
    )
    return (result.stdout or "") + (result.stderr or "")


def test_tc_chi_001_archived_inbox_proposal_verifies_2_of_2():
    """TC-CHI-001: 归档 2026-09-18-inbox-api-only-write 的 canon verify 达 2/2。"""
    out = _canon_verify("2026-09-18-inbox-api-only-write")
    assert "2/2" in out, (
        "canon verify 2026-09-18-inbox-api-only-write 未达 2/2"
        "（YAML 与归档 proposal.md 的 source_hash 不一致）：\n" + out
    )


def test_tc_chi_002_all_project_proposals_verify_2_of_2():
    """TC-CHI-002: 根 canonical/proposals 下全部 proposal 的 canon verify 均达 2/2。"""
    names = sorted(path.stem for path in PROPOSALS_DIR.glob("*.yaml"))
    assert names, f"未找到任何 proposal：{PROPOSALS_DIR}"
    failures = {}
    for name in names:
        out = _canon_verify(name)
        if "2/2" not in out:
            failures[name] = out.strip().replace("\n", " | ")
    assert failures == {}, (
        "以下 proposal 的 canon verify 未达 2/2（YAML 与 MD 指纹脱节）：\n  "
        + "\n  ".join(f"{k}: {v}" for k, v in failures.items())
    )


def test_tc_chi_003_this_change_canon_verify_is_2_of_2():
    """TC-CHI-003: 本 change 自身的 canonical 双轨一致（2/2）。"""
    out = _canon_verify(THIS_CHANGE)
    assert "2/2" in out, f"本 change canon verify 未达 2/2：\n{out}"
