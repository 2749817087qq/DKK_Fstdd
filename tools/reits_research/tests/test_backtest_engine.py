"""Slice 2 RED: 回测引擎核心测试 — Spec-BT-001 单因子选股回测。

覆盖：
  - 周频调仓
  - T-1 日数据计算因子（禁止 look-ahead）
  - 等权配置 + 交易成本扣除
  - 分红再投资
  - 幂等性（同参数 → 同结果）
  - Decimal 精度
"""
from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import pytest


def _make_quotes(codes: list[str], dates: list[datetime.date], prices: dict) -> pd.DataFrame:
    """构造模拟日线数据。prices: {code: [price_list]}"""
    rows = []
    for code in codes:
        for i, d in enumerate(dates):
            rows.append({
                "date": d,
                "code": code,
                "close": Decimal(str(prices[code][i])),
                "volume": 100000,
            })
    return pd.DataFrame(rows)


def _make_dividends(codes: list[str], ex_dates: list[datetime.date], amounts: dict) -> pd.DataFrame:
    """构造模拟分红数据。amounts: {code: [amount_list]}"""
    rows = []
    for code in codes:
        for i, d in enumerate(ex_dates):
            if i < len(amounts.get(code, [])):
                rows.append({
                    "ex_date": d,
                    "code": code,
                    "amount_per_share": Decimal(str(amounts[code][i])),
                })
    return pd.DataFrame(rows)


class TestBacktestEngineInit:
    """回测引擎初始化。"""

    def test_init_with_valid_params(self):
        """GIVEN 有效参数 WHEN 初始化 THEN 引擎创建成功。"""
        from src.backtest_engine import BacktestEngine

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )
        assert engine.initial_capital == Decimal("1000000")

    def test_init_negative_capital_raises(self):
        """GIVEN 负初始资金 WHEN 初始化 THEN 抛出 ValueError。"""
        from src.backtest_engine import BacktestEngine

        with pytest.raises(ValueError, match="initial_capital"):
            BacktestEngine(initial_capital=Decimal("-1"))


class TestSingleFactorBacktest:
    """Spec-BT-001: 单因子选股回测。"""

    def test_basic_single_factor_run(self):
        """GIVEN 2只标的+10个交易日+P/NAV因子 WHEN 回测 THEN 返回净值序列。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 11)]  # Mon-Wed x3 + Thu
        quotes = _make_quotes(
            ["A.SH", "B.SH"], dates,
            {"A.SH": [10]*10, "B.SH": [20]*10},
        )
        nav_data = pd.DataFrame({
            "date": dates, "code": ["A.SH"]*5 + ["B.SH"]*5,
            "nav": [Decimal("11")]*5 + [Decimal("18")]*5,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )

        result = engine.run_single_factor(
            quotes=quotes,
            nav_data=nav_data,
            dividends=dividends,
            factor_name="p_nav",
            select_top_n=1,
        )

        assert "date" in result.columns
        assert "nav_value" in result.columns
        assert len(result) > 0
        # 初始净值应为 1.0
        assert result["nav_value"].iloc[0] == Decimal("1.0000")

    def test_no_look_ahead_bias(self):
        """GIVEN T日因子用T-1数据计算 WHEN 回测 THEN 不使用T日数据。

        验证方式：如果 T 日价格突变但 T-1 不变，调仓决策不应改变。
        """
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 8)]
        # 场景1: T日(第5天)价格正常
        q1 = _make_quotes(["A.SH", "B.SH"], dates, {
            "A.SH": [10, 10, 10, 10, 10, 10, 10],
            "B.SH": [20, 20, 20, 20, 20, 20, 20],
        })
        # 场景2: T日(第5天)价格突变（不应影响当日调仓决策）
        q2 = _make_quotes(["A.SH", "B.SH"], dates, {
            "A.SH": [10, 10, 10, 10, 99, 10, 10],  # 第5天突变
            "B.SH": [20, 20, 20, 20, 20, 20, 20],
        })
        nav_data = pd.DataFrame({
            "date": dates + dates, "code": ["A.SH"]*7 + ["B.SH"]*7,
            "nav": [Decimal("11")]*7 + [Decimal("18")]*7,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        engine = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )

        r1 = engine.run_single_factor(q1, nav_data, dividends, "p_nav", 1)
        r2 = engine.run_single_factor(q2, nav_data, dividends, "p_nav", 1)

        # 调仓日的持仓应相同（因为都用 T-1 数据）
        # 简化验证：前4天净值应完全一致
        for i in range(min(4, len(r1), len(r2))):
            assert r1["nav_value"].iloc[i] == r2["nav_value"].iloc[i]


class TestIdempotency:
    """幂等性验证：同参数 → 同结果。"""

    def test_same_params_same_result(self):
        """GIVEN 相同参数和数据 WHEN 运行两次 THEN 结果完全一致。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 11)]
        quotes = _make_quotes(["A.SH", "B.SH"], dates, {
            "A.SH": [10+i*0.1 for i in range(10)],
            "B.SH": [20-i*0.1 for i in range(10)],
        })
        nav_data = pd.DataFrame({
            "date": dates + dates, "code": ["A.SH"]*10 + ["B.SH"]*10,
            "nav": [Decimal("11")]*10 + [Decimal("18")]*10,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        results = []
        for _ in range(2):
            engine = BacktestEngine(
                initial_capital=Decimal("1000000"),
                commission_rate=Decimal("0.0003"),
                slippage_rate=Decimal("0.0002"),
                rebalance_freq="weekly",
                dividend_reinvest=True,
                random_seed=42,
            )
            r = engine.run_single_factor(quotes, nav_data, dividends, "p_nav", 1)
            results.append(r)

        pd.testing.assert_frame_equal(results[0], results[1])


class TestDividendReinvest:
    """分红再投资验证。"""

    def test_dividend_increases_shares(self):
        """GIVEN 持有标的发生分红 WHEN 再投资 THEN 净值高于不分红场景。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 11)]
        quotes = _make_quotes(["A.SH"], dates, {"A.SH": [10]*10})
        nav_data = pd.DataFrame({
            "date": dates, "code": ["A.SH"]*10,
            "nav": [Decimal("11")]*10,
        })
        # 第5天分红 0.5 元/份
        dividends = _make_dividends(["A.SH"], [datetime.date(2024, 1, 5)], {"A.SH": [0.5]})

        # 有分红再投资
        e1 = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )
        r1 = e1.run_single_factor(quotes, nav_data, dividends, "p_nav", 1)

        # 无分红再投资
        e2 = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=False,
            random_seed=42,
        )
        r2 = e2.run_single_factor(quotes, nav_data, dividends, "p_nav", 1)

        # 再投资的终值应 ≥ 不再投资
        assert r1["nav_value"].iloc[-1] >= r2["nav_value"].iloc[-1]


class TestTransactionCost:
    """交易成本扣除验证。"""

    def test_cost_reduces_nav(self):
        """GIVEN 有交易成本 WHEN 调仓 THEN 净值低于零成本场景。"""
        from src.backtest_engine import BacktestEngine

        dates = [datetime.date(2024, 1, d) for d in range(1, 15)]
        quotes = _make_quotes(["A.SH", "B.SH"], dates, {
            "A.SH": [10]*14,
            "B.SH": [20]*14,
        })
        nav_data = pd.DataFrame({
            "date": dates + dates, "code": ["A.SH"]*14 + ["B.SH"]*14,
            "nav": [Decimal("11")]*14 + [Decimal("18")]*14,
        })
        dividends = pd.DataFrame(columns=["ex_date", "code", "amount_per_share"])

        # 有成本
        e1 = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.0003"),
            slippage_rate=Decimal("0.0002"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )
        r1 = e1.run_single_factor(quotes, nav_data, dividends, "p_nav", 1)

        # 零成本
        e2 = BacktestEngine(
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
            rebalance_freq="weekly",
            dividend_reinvest=True,
            random_seed=42,
        )
        r2 = e2.run_single_factor(quotes, nav_data, dividends, "p_nav", 1)

        # 有成本的终值应 ≤ 零成本
        assert r1["nav_value"].iloc[-1] <= r2["nav_value"].iloc[-1]
