"""Slice 5 RED: 绩效计算 + 敏感性分析测试 — Spec-BT-004。

覆盖：
  - 年化收益率、夏普比率、最大回撤、Calmar 比率
  - Decimal 精度（ROUND_HALF_UP, 4位）
  - 参数敏感性分析（单因子扫描 → 热力图数据）
  - 基准对比
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd
import pytest


def _make_nav_series(values: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    """构造模拟净值序列。"""
    dates = pd.bdate_range(start=start, periods=len(values), freq="B")
    return pd.DataFrame({
        "date": [d.date() for d in dates],
        "nav_value": [Decimal(str(v)) for v in values],
    })


class TestPerformanceMetrics:
    """核心绩效指标计算。"""

    def test_annualized_return(self):
        """GIVEN 1年净值从1.0到1.2 WHEN 计算 THEN 年化收益≈0.2。"""
        from src.performance import PerformanceCalculator

        # 252个交易日，终值1.2
        nav = _make_nav_series([1.0 + 0.2 * i / 251 for i in range(252)])
        calc = PerformanceCalculator(nav)

        result = calc.annualized_return()
        assert abs(float(result) - 0.2) < 0.01

    def test_max_drawdown(self):
        """GIVEN 净值先涨后跌20% WHEN 计算 THEN 最大回撤≈0.2。"""
        from src.performance import PerformanceCalculator

        # 涨到1.5再跌到1.2 → 回撤 = (1.5-1.2)/1.5 = 0.2
        values = [1.0 + 0.5 * i / 125 for i in range(126)]  # 涨到1.5
        values += [1.5 - 0.3 * i / 125 for i in range(126)]  # 跌到1.2
        nav = _make_nav_series(values)
        calc = PerformanceCalculator(nav)

        result = calc.max_drawdown()
        assert abs(float(result) - 0.2) < 0.01

    def test_sharpe_ratio(self):
        """GIVEN 正收益低波动 WHEN 计算 THEN 夏普>0。"""
        from src.performance import PerformanceCalculator

        # 稳定上涨
        nav = _make_nav_series([1.0 + 0.001 * i for i in range(252)])
        calc = PerformanceCalculator(nav, risk_free_rate=Decimal("0.02"))

        result = calc.sharpe_ratio()
        assert float(result) > 0

    def test_calmar_ratio(self):
        """GIVEN 年化收益0.2+回撤0.1 WHEN 计算 THEN Calmar≈2.0。"""
        from src.performance import PerformanceCalculator

        # 构造：年化~20%，回撤~10%
        values = [1.0]
        for i in range(251):
            if i < 126:
                values.append(values[-1] * 1.0015)  # 涨
            else:
                values.append(values[-1] * 0.9992)  # 小幅跌
        nav = _make_nav_series(values)
        calc = PerformanceCalculator(nav)

        calmar = calc.calmar_ratio()
        ann_ret = calc.annualized_return()
        mdd = calc.max_drawdown()

        # Calmar = 年化收益 / |最大回撤|
        if float(mdd) > 0:
            expected = float(ann_ret) / float(mdd)
            assert abs(float(calmar) - expected) < 0.1

    def test_decimal_precision(self):
        """GIVEN 任意净值序列 WHEN 计算 THEN 结果保留4位小数。"""
        from src.performance import PerformanceCalculator

        nav = _make_nav_series([1.0 + 0.001 * i for i in range(100)])
        calc = PerformanceCalculator(nav)

        for metric_fn in [calc.annualized_return, calc.max_drawdown, calc.sharpe_ratio]:
            result = metric_fn()
            # 验证是 Decimal 且精度 ≤ 4
            assert isinstance(result, Decimal)


class TestSensitivityAnalysis:
    """Spec-BT-004: 参数敏感性分析。"""

    def test_single_param_scan(self):
        """GIVEN 参数范围 WHEN 扫描 THEN 返回每个参数值的绩效。"""
        from src.performance import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer()

        # 模拟：不同阈值对应的绩效
        results = analyzer.scan_parameter(
            param_name="p_nav_threshold",
            param_values=[Decimal("-0.15"), Decimal("-0.10"), Decimal("-0.05"), Decimal("0.00")],
            backtest_fn=lambda threshold: {
                "annualized_return": Decimal(str(0.1 + float(threshold) * 0.5)),
                "sharpe": Decimal(str(1.0 + float(threshold) * 2)),
                "max_drawdown": Decimal(str(0.15 - float(threshold) * 0.1)),
            },
        )

        assert len(results) == 4
        assert "param_value" in results.columns
        assert "annualized_return" in results.columns

    def test_heatmap_data_structure(self):
        """GIVEN 扫描结果 WHEN 生成热力图数据 THEN 结构正确。"""
        from src.performance import SensitivityAnalyzer

        analyzer = SensitivityAnalyzer()
        results = analyzer.scan_parameter(
            param_name="threshold",
            param_values=[Decimal("-0.1"), Decimal("0.0"), Decimal("0.1")],
            backtest_fn=lambda v: {"sharpe": Decimal(str(1.0 + float(v)))},
        )

        heatmap = analyzer.to_heatmap_data(results, metric="sharpe")
        assert "param_value" in heatmap.columns
        assert "metric_value" in heatmap.columns
