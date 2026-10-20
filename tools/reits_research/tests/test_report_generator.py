"""Slice 6 RED: 报告生成器测试。

覆盖：
  - Markdown 五章结构完整
  - 量化章节绑定回测证据（Spec 引用 + 绩效数据）
  - 数据质量声明嵌入
  - 审计日志摘要附录
  - 图表占位符生成
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd
import pytest


class TestReportStructure:
    """报告五章结构验证。"""

    def test_report_has_five_chapters(self):
        """GIVEN 完整输入 WHEN 生成报告 THEN 包含五个主章节。"""
        from src.report_generator import ReportGenerator

        gen = ReportGenerator(
            title="2026Q3 REITs 投研报告",
            data_cutoff="2026-09-30",
            code_version="abc1234",
        )

        perf_summary = {
            "annualized_return": Decimal("0.1250"),
            "max_drawdown": Decimal("0.0830"),
            "sharpe_ratio": Decimal("1.520"),
            "calmar_ratio": Decimal("1.506"),
        }
        quality_log = [
            {"check": "quotes_completeness", "code": "508000.SH", "status": "passed_with_gaps", "detail": "missing_rate=0.02"},
        ]
        audit_log = [
            {"timestamp": "2026-10-19T00:00:00Z", "check": "backtest", "code": "-", "status": "completed", "detail": "params_hash=abc"},
        ]

        report = gen.generate(
            performance=perf_summary,
            quality_results={"excluded": [], "stale": ["508099.SH"]},
            quality_log=quality_log,
            audit_log=audit_log,
            sensitivity_data=None,
        )

        assert "# 1." in report or "## 1." in report  # 宏观
        assert "# 2." in report or "## 2." in report  # 行业
        assert "# 3." in report or "## 3." in report  # 估值
        assert "# 4." in report or "## 4." in report  # 策略
        assert "# 5." in report or "## 5." in report  # 风险

    def test_report_contains_performance_data(self):
        """GIVEN 绩效摘要 WHEN 生成报告 THEN 报告中包含具体数值。"""
        from src.report_generator import ReportGenerator

        gen = ReportGenerator(title="Test", data_cutoff="2026-09-30", code_version="v1")
        perf = {
            "annualized_return": Decimal("0.1250"),
            "max_drawdown": Decimal("0.0830"),
            "sharpe_ratio": Decimal("1.520"),
            "calmar_ratio": Decimal("1.506"),
        }

        report = gen.generate(performance=perf, quality_results={}, quality_log=[], audit_log=[])

        assert "0.1250" in report or "12.50%" in report
        assert "1.520" in report

    def test_report_contains_quality_declaration(self):
        """GIVEN 质量检查结果 WHEN 生成报告 THEN 包含数据质量声明。"""
        from src.report_generator import ReportGenerator

        gen = ReportGenerator(title="Test", data_cutoff="2026-09-30", code_version="v1")
        report = gen.generate(
            performance={"annualized_return": Decimal("0.1"), "max_drawdown": Decimal("0.05"), "sharpe_ratio": Decimal("1.0"), "calmar_ratio": Decimal("2.0")},
            quality_results={"excluded": ["X.SH"], "stale": ["Y.SH"]},
            quality_log=[],
            audit_log=[],
        )

        assert "X.SH" in report  # excluded 标的应被提及
        assert "Y.SH" in report  # stale 标的应被提及

    def test_report_contains_audit_appendix(self):
        """GIVEN 审计日志 WHEN 生成报告 THEN 附录中包含审计摘要。"""
        from src.report_generator import ReportGenerator

        gen = ReportGenerator(title="Test", data_cutoff="2026-09-30", code_version="v1")
        audit = [{"timestamp": "2026-10-19T00:00:00Z", "check": "backtest", "code": "-", "status": "ok", "detail": ""}]
        report = gen.generate(
            performance={"annualized_return": Decimal("0.1"), "max_drawdown": Decimal("0.05"), "sharpe_ratio": Decimal("1.0"), "calmar_ratio": Decimal("2.0")},
            quality_results={},
            quality_log=[],
            audit_log=audit,
        )

        assert "附录" in report or "Appendix" in report
        assert "2026-10-19" in report
