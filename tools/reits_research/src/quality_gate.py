"""Slice 4 GREEN: 数据质量门禁 + 降级处理。

Spec-BT-003: 数据质量门禁
  - 行情缺失率 ≤ max_missing_rate（否则排除 + 告警）
  - NAV 最新日期距今 ≤ stale_nav_days（否则标记 stale）
  - 分红记录完整性 ≥ 95%（否则标注 incomplete）

Spec-BT-005: 降级处理
  - 缺失 ≤ max_gap_days → 最近有效值填充 + 标记 filled
  - 缺失 > max_gap_days → 排除 + 标记 excluded
  - 禁止静默处理，所有降级写入 audit_log
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import pandas as pd


class QualityGate:
    """REITs 数据质量门禁。

    Args:
        max_missing_rate: 最大允许缺失率（默认 5%）。
        stale_nav_days: NAV 过期天数阈值（默认 90）。
    """

    def __init__(
        self,
        max_missing_rate: float = 0.05,
        stale_nav_days: int = 90,
    ) -> None:
        self.max_missing_rate = max_missing_rate
        self.stale_nav_days = stale_nav_days
        self._audit_log: list[dict[str, Any]] = []

    # ── 审计日志 ────────────────────────────────────────────────────

    def log_check(self, check: str, code: str, status: str, detail: str = "") -> None:
        """记录一条质量检查结果。"""
        self._audit_log.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "check": check,
            "code": code,
            "status": status,
            "detail": detail,
        })

    def get_audit_log(self) -> list[dict[str, Any]]:
        """获取完整审计日志。"""
        return list(self._audit_log)

    # ── Spec-BT-003: 行情缺失率检查 ────────────────────────────────

    def check_quotes_completeness(
        self, quotes: pd.DataFrame, expected_dates: list[datetime.date]
    ) -> dict[str, list[str]]:
        """检查每个标的的行情缺失率。

        Returns:
            {"excluded": [codes], "passed": [codes]}
        """
        total = len(expected_dates)
        excluded, passed = [], []

        for code in quotes["code"].unique():
            code_dates = set(quotes[quotes["code"] == code]["date"])
            missing = sum(1 for d in expected_dates if d not in code_dates)
            rate = missing / total if total > 0 else 0

            if rate > self.max_missing_rate:
                excluded.append(code)
                self.log_check("quotes_completeness", code, "excluded", f"missing_rate={rate:.4f}")
            else:
                passed.append(code)
                if missing > 0:
                    self.log_check("quotes_completeness", code, "passed_with_gaps", f"missing_rate={rate:.4f}")

        return {"excluded": excluded, "passed": passed}

    # ── Spec-BT-003: NAV 时效性检查 ────────────────────────────────

    def check_nav_freshness(
        self, nav_data: pd.DataFrame, as_of: datetime.date
    ) -> dict[str, list[str]]:
        """检查 NAV 是否过期。

        Returns:
            {"stale": [codes], "fresh": [codes]}
        """
        stale, fresh = [], []

        for code in nav_data["code"].unique():
            code_nav = nav_data[nav_data["code"] == code].sort_values("date")
            if code_nav.empty:
                stale.append(code)
                self.log_check("nav_freshness", code, "stale", "no NAV data")
                continue

            latest = code_nav["date"].iloc[-1]
            days_since = (as_of - latest).days

            if days_since > self.stale_nav_days:
                stale.append(code)
                self.log_check("nav_freshness", code, "stale", f"last_update={latest}, days={days_since}")
            else:
                fresh.append(code)

        return {"stale": stale, "fresh": fresh}

    # ── Spec-BT-005: 降级处理 ─────────────────────────────────────

    def fill_short_gaps(
        self,
        quotes: pd.DataFrame,
        expected_dates: list[datetime.date],
        max_gap_days: int = 3,
    ) -> tuple[pd.DataFrame, list[dict]]:
        """对短缺口用最近有效值填充，长缺口标记排除。

        Args:
            quotes: 原始行情数据。
            expected_dates: 期望的完整日期序列。
            max_gap_days: 最大可填充缺口天数。

        Returns:
            (filled_quotes, degradation_log)
        """
        log: list[dict] = []
        new_rows: list[dict] = []

        for code in quotes["code"].unique():
            code_quotes = quotes[quotes["code"] == code].sort_values("date")
            existing_dates = set(code_quotes["date"])
            last_valid_close = None

            consecutive_missing = 0
            gap_start = None

            for d in expected_dates:
                if d in existing_dates:
                    row = code_quotes[code_quotes["date"] == d].iloc[0]
                    last_valid_close = row["close"]
                    # 如果之前有短缺口，回填
                    if consecutive_missing > 0 and consecutive_missing <= max_gap_days:
                        for gd in range(consecutive_missing):
                            fill_date = d - datetime.timedelta(days=consecutive_missing - gd)
                            if fill_date not in existing_dates:
                                new_rows.append({
                                    "date": fill_date,
                                    "code": code,
                                    "close": last_valid_close,
                                    "volume": 0,
                                    "_status": "filled",
                                })
                                log.append({"code": code, "date": str(fill_date), "status": "filled"})
                    elif consecutive_missing > max_gap_days:
                        log.append({
                            "code": code,
                            "gap_start": str(gap_start),
                            "gap_days": consecutive_missing,
                            "status": "excluded",
                        })
                    consecutive_missing = 0
                    gap_start = None
                else:
                    consecutive_missing += 1
                    if gap_start is None:
                        gap_start = d

            # 尾部缺口处理
            if consecutive_missing > max_gap_days:
                log.append({
                    "code": code,
                    "gap_start": str(gap_start),
                    "gap_days": consecutive_missing,
                    "status": "excluded",
                })

        if new_rows:
            filled = pd.concat([quotes, pd.DataFrame(new_rows)], ignore_index=True)
            filled = filled.sort_values(["code", "date"]).reset_index(drop=True)
        else:
            filled = quotes.copy()

        return filled, log
