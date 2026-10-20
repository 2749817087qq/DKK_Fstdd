"""Slice 5 GREEN: 绩效计算 + 敏感性分析。

口径定义（Spec P2 §2.2）：
  - 年化收益率: (1+总收益)^(252/交易天数) - 1, ROUND_HALF_UP 4位
  - 夏普比率: (年化收益-无风险利率)/年化波动率, 3位
  - 最大回撤: min((peak-trough)/peak), 4位
  - Calmar比率: 年化收益/|最大回撤|, 3位

Spec-BT-004: 参数敏感性分析
  - 单因子扫描 → DataFrame[param_value, metrics...]
  - 热力图数据结构
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

import numpy as np
import pandas as pd


class PerformanceCalculator:
    """回测绩效计算器。

    Args:
        nav_df: DataFrame[date, nav_value(Decimal)]。
        risk_free_rate: 无风险利率（年化，默认 2%）。
        trading_days: 年交易日数（默认 252）。
    """

    def __init__(
        self,
        nav_df: pd.DataFrame,
        risk_free_rate: Decimal = Decimal("0.02"),
        trading_days: int = 252,
    ) -> None:
        self.nav_df = nav_df.sort_values("date").reset_index(drop=True)
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days

    def _to_float_series(self) -> np.ndarray:
        """将 Decimal 净值转为 float numpy 数组用于数值计算。"""
        return np.array([float(v) for v in self.nav_df["nav_value"]])

    def annualized_return(self) -> Decimal:
        """几何年化收益率。"""
        vals = self._to_float_series()
        if len(vals) < 2:
            return Decimal("0")
        total_return = vals[-1] / vals[0] - 1
        n_days = len(vals)
        ann = (1 + total_return) ** (self.trading_days / n_days) - 1
        return Decimal(str(ann)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def max_drawdown(self) -> Decimal:
        """最大回撤。"""
        vals = self._to_float_series()
        if len(vals) < 2:
            return Decimal("0")
        peaks = np.maximum.accumulate(vals)
        drawdowns = (peaks - vals) / peaks
        mdd = float(np.max(drawdowns))
        return Decimal(str(mdd)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def sharpe_ratio(self) -> Decimal:
        """夏普比率。"""
        vals = self._to_float_series()
        if len(vals) < 2:
            return Decimal("0")
        returns = np.diff(vals) / vals[:-1]
        if np.std(returns) == 0:
            return Decimal("0")
        ann_ret = float(self.annualized_return())
        ann_vol = float(np.std(returns) * np.sqrt(self.trading_days))
        sharpe = (ann_ret - float(self.risk_free_rate)) / ann_vol if ann_vol > 0 else 0
        return Decimal(str(sharpe)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def calmar_ratio(self) -> Decimal:
        """Calmar 比率 = 年化收益 / |最大回撤|。"""
        ann_ret = float(self.annualized_return())
        mdd = float(self.max_drawdown())
        if mdd == 0:
            return Decimal("0")
        calmar = ann_ret / mdd
        return Decimal(str(calmar)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def summary(self) -> dict[str, Decimal]:
        """返回全部绩效指标摘要。"""
        return {
            "annualized_return": self.annualized_return(),
            "max_drawdown": self.max_drawdown(),
            "sharpe_ratio": self.sharpe_ratio(),
            "calmar_ratio": self.calmar_ratio(),
        }


class SensitivityAnalyzer:
    """参数敏感性分析器（Spec-BT-004）。"""

    def scan_parameter(
        self,
        param_name: str,
        param_values: list[Decimal],
        backtest_fn: Callable[[Decimal], dict[str, Decimal]],
    ) -> pd.DataFrame:
        """对单个参数进行扫描回测。

        Args:
            param_name: 参数名称。
            param_values: 待扫描的参数值列表。
            backtest_fn: 接受参数值、返回绩效字典的函数。

        Returns:
            DataFrame[param_value, metric1, metric2, ...]
        """
        rows = []
        for val in param_values:
            metrics = backtest_fn(val)
            row = {"param_value": val}
            row.update(metrics)
            rows.append(row)
        return pd.DataFrame(rows)

    @staticmethod
    def to_heatmap_data(
        scan_results: pd.DataFrame,
        metric: str,
    ) -> pd.DataFrame:
        """将扫描结果转换为热力图数据格式。

        Returns:
            DataFrame[param_value, metric_value]
        """
        return scan_results[["param_value", metric]].rename(
            columns={metric: "metric_value"}
        )
