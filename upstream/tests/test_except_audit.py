# -*- coding: utf-8 -*-
"""TC-AUD-001..005 — 吞异常审计表：完整性、零漂移、分类合法、理由覆盖、分级齐备。

审计表是 `.fstdd/changes|archive/<change>/audit/except-points.yaml`，
由 tools/audit_silent_except.py 的扫描结果人工分类产出。
本测试组确保证据链可信：表与代码实况零漂移（改代码不改表 = 红）。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]

AUDIT_MODULE = REPO / "tools" / "audit_silent_except.py"
VALID_CLASSES = {"合理容错", "意外吞错", "收窄建议"}
VALID_RESPONSES = {"放行", "加警告", "升级 change"}


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_silent_except", AUDIT_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _audit_table_path() -> Path:
    """活表优先：changes 下任一 change 的 audit/except-points.yaml（字典序首个），
    其次 archive 兜底。表随维护 change 迁移，不硬编码 change id。"""
    for base in ("changes", "archive"):
        hits = sorted((REPO / ".fstdd" / base).glob("*/audit/except-points.yaml"))
        if hits:
            return hits[0]
    raise FileNotFoundError("changes/ 与 archive/ 均找不到审计表")


# --------------------------------------------------------------------------- #
# TC-AUD-001 — 扫描器与审计表存在且可读
# --------------------------------------------------------------------------- #

def test_aud_001_scanner_and_table_exist():
    assert AUDIT_MODULE.is_file(), "缺 tools/audit_silent_except.py 扫描器"
    table = _audit_table_path()
    assert table.is_file(), f"缺审计表: {table}"
    data = yaml.safe_load(table.read_text(encoding="utf-8"))
    assert data.get("points"), "审计表 points 为空"


# --------------------------------------------------------------------------- #
# TC-AUD-002 — 表与实况扫描零漂移（指纹集合相等 + 行号容差）
# --------------------------------------------------------------------------- #

def test_aud_002_table_matches_live_scan():
    mod = _load_audit_module()
    live = mod.scan()  # 实况扫描
    table = yaml.safe_load(_audit_table_path().read_text(encoding="utf-8"))
    recorded = table["points"]

    def keyed(points):
        """指纹 = (file, stmt, handler, 同指纹序号)。同文件多处 pass 靠序号区分。"""
        seen: dict = {}
        out = []
        for p in points:
            k = (p["file"], p["stmt"].strip(), p["handler"])
            n = seen.get(k, 0)
            seen[k] = n + 1
            out.append((k, n, p))
        return out

    live_k = keyed(live)
    rec_k = keyed(recorded)
    live_keys = sorted((k, n) for k, n, _ in live_k)
    rec_keys = sorted((k, n) for k, n, _ in rec_k)
    assert live_keys == rec_keys, (
        f"审计表与实况扫描漂移: 新增未记录 {set(live_keys) - set(rec_keys)}; "
        f"记录了但已消失 {set(rec_keys) - set(live_keys)}"
    )
    # 行号容差 ±5（插入代码导致位移可容忍，指纹已保证同一处）
    live_by_key = {(k, n): p for k, n, p in live_k}
    for k, n, r in rec_k:
        l = live_by_key[(k, n)]
        assert abs(int(r["line"]) - int(l["line"])) <= 5, (
            f"{r['id']} 行号漂移过大: 表 {r['line']} vs 实况 {l['line']}"
        )


# --------------------------------------------------------------------------- #
# TC-AUD-003 — 分类合法、理由覆盖率 ≥90%
# --------------------------------------------------------------------------- #

def test_aud_003_classification_and_justification():
    table = yaml.safe_load(_audit_table_path().read_text(encoding="utf-8"))
    pts = table["points"]
    # 数量下限只是「扫描器没跑成」的哨兵：观测基线 29，随每轮失败有声改造
    # 单调递减（detection-silence-fixes 已修复 11 点 → 18）。低于 10 说明漏扫。
    assert len(pts) >= 10, f"吞异常点异常少: {len(pts)}（观测基线 29，修复后递减）"
    for p in pts:
        assert p["classification"] in VALID_CLASSES, (
            f"{p.get('id')} 分类非法: {p.get('classification')}"
        )
        assert p.get("justification", "").strip(), f"{p.get('id')} 缺分类理由"
    justified = sum(1 for p in pts if p.get("justification", "").strip())
    assert justified / len(pts) >= 0.9, "理由覆盖率 <90%"


# --------------------------------------------------------------------------- #
# TC-AUD-004 — 吞错点必须有严重度与响应分级；合理容错必须放行
# --------------------------------------------------------------------------- #

def test_aud_004_severity_and_response_consistency():
    table = yaml.safe_load(_audit_table_path().read_text(encoding="utf-8"))
    for p in table["points"]:
        pid = p.get("id", "?")
        if p["classification"] == "意外吞错":
            assert p.get("severity") in ("p1", "p2"), f"{pid} 吞错点缺严重度"
            assert p.get("response") in VALID_RESPONSES - {"放行"}, (
                f"{pid} 吞错点不允许「放行」"
            )
        elif p["classification"] == "合理容错":
            assert p.get("response") == "放行", f"{pid} 合理容错应放行"
        assert p.get("detection_path") in (True, False), f"{pid} 缺 detection_path 标记"


# --------------------------------------------------------------------------- #
# TC-AUD-005 — 检测路径上的吞错点（B3 家族）必须全部被识别
# --------------------------------------------------------------------------- #

def test_aud_005_detection_paths_flagged():
    table = yaml.safe_load(_audit_table_path().read_text(encoding="utf-8"))
    # 家族覆盖：文件必须位于扫描根内（扫描器不会忽略该家族）。
    # 注意：随失败有声改造推进，某家族可能已全部修完、点从 points 移除
    # （见 meta.voiced_by_change）。因此这里断言的是「扫描根覆盖该文件」，
    # 而不是「points 里还有该家族的点」—— 后者会把「家族被彻底修干净」误判为红。
    # 断言意图与下方 errata EA-027 一致：修 bug 不得让守卫失去对该家族的可见性。
    mod = _load_audit_module()
    for name in ("guard.py", "check_timestamps.py"):
        assert _in_scanned_roots(name, mod), (
            f"{name} 不在任何扫描根内 —— 扫描器对该家族视而不见"
        )
    assert any(_in_scanned_roots(n, mod) for n in ("baseline.py", "validate.py", "gate.py")), \
        "基线与校验家族（baseline/validate/gate）不在任何扫描根内"
    flagged = [
        p for p in table["points"]
        if p["classification"] == "意外吞错" and p.get("detection_path")
    ]
    assert flagged, "检测路径吞错点清单为空"


def _in_scanned_roots(name: str, mod) -> bool:
    """家族文件是否位于扫描根（DEFAULT_ROOTS）内。"""
    for root in mod.DEFAULT_ROOTS:
        base = REPO / root
        if base.is_dir() and any(base.rglob(name)):
            return True
    return False
