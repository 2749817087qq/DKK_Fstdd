"""Slice 4 RED: 数据质量门禁 + 降级处理测试 — Spec-BT-003/005。

覆盖：
  - 行情缺失率检查（>5% → 排除 + 告警）
  - NAV 时效性检查（>90天 → stale 标记）
  - 分红完整性检查（<95% → incomplete 标记）
  - 降级处理：缺失 ≤3天填充 + >3天排除
  - 门禁结果写入 audit_log
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd
import pytest


class TestMissingRateCheck:
    """行情缺失率检查。"""

    def test_high_missing_rate_excludes_code(self):
        """GIVEN 标的缺失率>5% WHEN 检查 THEN 该标的被排除。"""
        from src.quality_gate import QualityGate

        dates = [datetime.date(2024, 1, d) for d in range(1, 21)]  # 20 days
        # A.SH 缺 5 天 (25%)，B.SH 完整
        rows = []
        for d in dates:
            if d.day not in (3, 7, 11, 15, 19):  # skip 5 days for A
                rows.append({"date": d, "code": "A.SH", "close": Decimal("10")})
            rows.append({"date": d, "code": "B.SH", "close": Decimal("20")})
        quotes = pd.DataFrame(rows)

        gate = QualityGate(max_missing_rate=0.05)
        result = gate.check_quotes_completeness(quotes, dates)

        assert "A.SH" in result["excluded"]
        assert "B.SH" not in result["excluded"]

    def test_low_missing_rate_passes(self):
        """GIVEN 标的缺失率≤5% WHEN 检查 THEN 通过。"""
        from src.quality_gate import QualityGate

        dates = [datetime.date(2024, 1, d) for d in range(1, 21)]
        # A.SH 只缺 1 天 (5%)
        rows = []
        for d in dates:
            if d.day != 10:
                rows.append({"date": d, "code": "A.SH", "close": Decimal("10")})
        quotes = pd.DataFrame(rows)

        gate = QualityGate(max_missing_rate=0.05)
        result = gate.check_quotes_completeness(quotes, dates)

        assert "A.SH" not in result["excluded"]


class TestNAVStaleness:
    """NAV 时效性检查。"""

    def test_stale_nav_flagged(self):
        """GIVEN NAV 超90天未更新 WHEN 检查 THEN 标记 stale。"""
        from src.quality_gate import QualityGate

        nav_data = pd.DataFrame({
            "date": [datetime.date(2023, 6, 30)],
            "code": ["A.SH"],
            "nav": [Decimal("3.5")],
        })

        gate = QualityGate(stale_nav_days=90)
        result = gate.check_nav_freshness(nav_data, as_of=datetime.date(2024, 1, 15))

        assert "A.SH" in result["stale"]

    def test_fresh_nav_passes(self):
        """GIVEN NAV 在90天内 WHEN 检查 THEN 不标记 stale。"""
        from src.quality_gate import QualityGate

        nav_data = pd.DataFrame({
            "date": [datetime.date(2023, 12, 31)],
            "code": ["A.SH"],
            "nav": [Decimal("3.5")],
        })

        gate = QualityGate(stale_nav_days=90)
        result = gate.check_nav_freshness(nav_data, as_of=datetime.date(2024, 1, 15))

        assert "A.SH" not in result["stale"]


class TestDegradation:
    """降级处理（Spec-BT-005）。"""

    def test_short_gap_filled(self):
        """GIVEN 缺失≤3天 WHEN 降级处理 THEN 用最近有效值填充 + 标记 filled。"""
        from src.quality_gate import QualityGate

        dates = [datetime.date(2024, 1, d) for d in range(1, 8)]
        # A.SH 缺第3、4天（2天 ≤ 3）
        rows = [
            {"date": datetime.date(2024, 1, 1), "code": "A.SH", "close": Decimal("10")},
            {"date": datetime.date(2024, 1, 2), "code": "A.SH", "close": Decimal("10.1")},
            {"date": datetime.date(2024, 1, 5), "code": "A.SH", "close": Decimal("10.3")},
            {"date": datetime.date(2024, 1, 6), "code": "A.SH", "close": Decimal("10.4")},
            {"date": datetime.date(2024, 1, 7), "code": "A.SH", "close": Decimal("10.5")},
        ]
        quotes = pd.DataFrame(rows)

        gate = QualityGate()
        filled, log = gate.fill_short_gaps(quotes, dates, max_gap_days=3)

        assert len(filled) == 7  # 原始5 + 填充2
        assert any(r.get("status") == "filled" for r in log)

    def test_long_gap_excluded(self):
        """GIVEN 缺失>3天 WHEN 降级处理 THEN 排除 + 标记 excluded。"""
        from src.quality_gate import QualityGate

        dates = [datetime.date(2024, 1, d) for d in range(1, 11)]
        # A.SH 缺第3-7天（5天 > 3）
        rows = [
            {"date": datetime.date(2024, 1, 1), "code": "A.SH", "close": Decimal("10")},
            {"date": datetime.date(2024, 1, 2), "code": "A.SH", "close": Decimal("10.1")},
            {"date": datetime.date(2024, 1, 8), "code": "A.SH", "close": Decimal("10.5")},
            {"date": datetime.date(2024, 1, 9), "code": "A.SH", "close": Decimal("10.6")},
            {"date": datetime.date(2024, 1, 10), "code": "A.SH", "close": Decimal("10.7")},
        ]
        quotes = pd.DataFrame(rows)

        gate = QualityGate()
        filled, log = gate.fill_short_gaps(quotes, dates, max_gap_days=3)

        # 长缺口不应被填充
        assert any(r.get("status") == "excluded" for r in log)


class TestAuditLog:
    """审计日志记录。"""

    def test_audit_log_records_checks(self):
        """GIVEN 执行多项检查 WHEN 获取审计日志 THEN 包含所有检查结果。"""
        from src.quality_gate import QualityGate

        gate = QualityGate()
        gate.log_check("quotes_completeness", "A.SH", "excluded", "missing_rate=0.25")
        gate.log_check("nav_freshness", "B.SH", "stale", "last_update=2023-06-30")

        log = gate.get_audit_log()
        assert len(log) == 2
        assert log[0]["check"] == "quotes_completeness"
        assert log[1]["code"] == "B.SH"
