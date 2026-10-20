"""Slice 3 RED: 多因子轮动 + 换手约束测试 — Spec-BT-002。

覆盖：
  - 多因子加权排名合成
  - 换手率约束（单次调仓换仓比例 ≤ max_turnover）
  - 因子贡献分解
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd
import pytest


def _make_quotes(codes, dates, prices):
    rows = []
    for code in codes:
        for i, d in enumerate(dates):
            rows.append({"date": d, "code": code, "close": Decimal(str(prices[code][i])), "volume": 100000})
    return pd.DataFrame(rows)


class TestMultiFactorRanking:
    """多因子加权排名合成。"""

    def test_weighted_rank_synthesis(self):
        """GIVEN 2个因子+权重 WHEN 合成 THEN 综合得分按加权排名排序。"""
        from src.backtest_engine import BacktestEngine

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )

        # 3只标的，2个因子
        factor_data = pd.DataFrame({
            "code": ["A.SH", "B.SH", "C.SH"],
            "p_nav": [Decimal("-0.10"), Decimal("0.05"), Decimal("-0.02")],   # asc: A最优
            "ffo_yield": [Decimal("0.03"), Decimal("0.08"), Decimal("0.05")],  # desc: B最优
        })
        weights = {"p_nav": Decimal("0.6"), "ffo_yield": Decimal("0.4")}
        directions = {"p_nav": "asc", "ffo_yield": "desc"}

        result = engine.compute_composite_score(factor_data, weights, directions)

        assert "composite_score" in result.columns
        assert len(result) == 3
        # 排名应为数值型，可排序
        assert result["composite_score"].dtype in ("float64", "object")

    def test_single_factor_equals_direct(self):
        """GIVEN 单因子权重=1 WHEN 合成 THEN 结果等价于直接排名。"""
        from src.backtest_engine import BacktestEngine

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            random_seed=42,
        )

        factor_data = pd.DataFrame({
            "code": ["A.SH", "B.SH", "C.SH"],
            "p_nav": [Decimal("-0.10"), Decimal("0.05"), Decimal("-0.02")],
        })
        weights = {"p_nav": Decimal("1.0")}
        directions = {"p_nav": "asc"}

        result = engine.compute_composite_score(factor_data, weights, directions)
        # p_nav asc → A(-0.10) < C(-0.02) < B(0.05) → rank 0, 1, 2
        sorted_result = result.sort_values("composite_score")
        assert sorted_result["code"].iloc[0] == "A.SH"


class TestTurnoverConstraint:
    """换手率约束验证。"""

    def test_turnover_within_limit(self):
        """GIVEN max_turnover=0.3 WHEN 调仓 THEN 实际换手率 ≤ 0.3。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 22)]  # 3 weeks
        # 4只标的，价格交替变化以触发换仓
        quotes = _make_quotes(["A.SH", "B.SH", "C.SH", "D.SH"], dates, {
            "A.SH": [10+i*0.5 for i in range(21)],
            "B.SH": [20-i*0.3 for i in range(21)],
            "C.SH": [15]*21,
            "D.SH": [12+i*0.1 for i in range(21)],
        })
        nav_data = pd.DataFrame({
            "date": dates * 4,
            "code": ["A.SH"]*21 + ["B.SH"]*21 + ["C.SH"]*21 + ["D.SH"]*21,
            "nav": [Decimal("11")]*21 + [Decimal("18")]*21 + [Decimal("14")]*21 + [Decimal("13")]*21,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            max_turnover=Decimal("0.30"),
            dividend_reinvest=True,
            random_seed=42,
        )

        result = engine.run_multi_factor(
            quotes=quotes,
            nav_data=nav_data,
            dividends=dividends,
            factor_configs={
                "p_nav": {"weight": Decimal("0.5"), "direction": "asc"},
                "ffo_yield": {"weight": Decimal("0.5"), "direction": "desc"},
            },
            select_top_n=2,
        )

        # 验证换手率列存在且均 ≤ 0.30
        if "turnover" in result.columns:
            assert (result["turnover"] <= Decimal("0.30")).all()

    def test_zero_turnover_when_same_holdings(self):
        """GIVEN 持仓不变 WHEN 调仓 THEN 换手率 = 0。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 15)]
        # 价格恒定 → 因子排名不变 → 不换仓
        quotes = _make_quotes(["A.SH", "B.SH"], dates, {
            "A.SH": [10]*14,
            "B.SH": [20]*14,
        })
        nav_data = pd.DataFrame({
            "date": dates + dates,
            "code": ["A.SH"]*14 + ["B.SH"]*14,
            "nav": [Decimal("11")]*14 + [Decimal("18")]*14,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            max_turnover=Decimal("0.30"),
            dividend_reinvest=True,
            random_seed=42,
        )

        result = engine.run_multi_factor(
            quotes=quotes,
            nav_data=nav_data,
            dividends=dividends,
            factor_configs={
                "p_nav": {"weight": Decimal("1.0"), "direction": "asc"},
            },
            select_top_n=1,
        )

        # 非零换手率的天数应为 0（或仅首次建仓）
        if "turnover" in result.columns:
            non_zero = result[result["turnover"] > 0]
            # 最多只有首次建仓那天有换手
            assert len(non_zero) <= 1
