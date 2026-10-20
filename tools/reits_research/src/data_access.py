"""Slice 1 GREEN: 数据接入层 — PostgreSQL + DuckDB 双源读取。

数据契约（Spec P2 §2.1）：
  - 日线收盘价 → DuckDB market.daily_quotes (Decimal(18,6), T+1)
  - NAV        → PG reits.nav_history (Decimal(18,4), 季度/半年度)
  - 分红记录   → PG reits.dividends (Decimal(18,4), 事件驱动)
  - 基础信息   → PG reits.fund_info (VARCHAR, 变更时更新)
  - 运营指标   → PG reits.asset_metrics (Decimal(18,4), 半年度)
  - 外部数据   → 网络搜索（不在本模块范围）

降级行为（Spec-BT-005）：
  - 缺失 ≤3天 → 最近有效值填充 + 标记 filled
  - 缺失 >3天 → 排除 + 标记 excluded
  - 本模块只负责读取，降级逻辑在 quality_gate.py (S4)
"""
from __future__ import annotations

import datetime
import os
from decimal import Decimal
from typing import Any, Optional

import pandas as pd


class DataAccess:
    """REITs 数据接入层：PostgreSQL + DuckDB 双源统一接口。

    Args:
        config: 数据库配置字典，需包含 postgresql 和 duckdb 两个节。

    Raises:
        ValueError: 缺少必需的数据库配置节。
    """

    def __init__(self, config: dict[str, Any]) -> None:
        if "postgresql" not in config:
            raise ValueError("配置缺少 postgresql 节")
        if "duckdb" not in config:
            raise ValueError("配置缺少 duckdb 节")

        self._pg_config = config["postgresql"]
        self._duckdb_config = config["duckdb"]
        self._pg_conn = None
        self._duckdb_conn = None

    # ── 连接管理 ────────────────────────────────────────────────────

    def _get_pg_connection(self):
        """延迟创建 PostgreSQL 连接。"""
        if self._pg_conn is None:
            import psycopg2
            password = os.environ.get(self._pg_config.get("password_env", ""), "")
            self._pg_conn = psycopg2.connect(
                host=self._pg_config["host"],
                port=self._pg_config["port"],
                dbname=self._pg_config["dbname"],
                user=self._pg_config["user"],
                password=password,
            )
        return self._pg_conn

    def _get_duckdb_connection(self):
        """延迟创建 DuckDB 连接。"""
        if self._duckdb_conn is None:
            import duckdb
            path = self._duckdb_config["path"]
            self._duckdb_conn = duckdb.connect(path, read_only=True)
        return self._duckdb_conn

    def close(self) -> None:
        """关闭所有数据库连接。"""
        if self._pg_conn is not None:
            self._pg_conn.close()
            self._pg_conn = None
        if self._duckdb_conn is not None:
            self._duckdb_conn.close()
            self._duckdb_conn = None

    # ── 查询抽象（可被 mock 替换） ──────────────────────────────────

    def _query_pg(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """执行 PG 查询，返回 DataFrame。"""
        conn = self._get_pg_connection()
        return pd.read_sql(sql, conn, params=params)

    def _query_pg_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """执行 PG 查询，返回单行字典或 None。"""
        conn = self._get_pg_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                return None
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))

    def _query_duckdb(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """执行 DuckDB 查询，返回 DataFrame。"""
        conn = self._get_duckdb_connection()
        return conn.execute(sql, params).fetchdf()

    # ── 数据契约接口 ────────────────────────────────────────────────

    def get_daily_quotes(
        self, code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取日线行情（DuckDB）。

        Returns:
            DataFrame[date, code, close(Decimal), volume]
        """
        sql = """
            SELECT date, code, close, volume
            FROM market.daily_quotes
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        df = self._query_duckdb(sql, (code, start_date, end_date))
        # 确保 close 列为 Decimal
        if not df.empty and "close" in df.columns:
            df["close"] = df["close"].apply(
                lambda x: Decimal(str(x)) if x is not None else None
            )
        return df

    def get_nav_history(self, code: str) -> pd.DataFrame:
        """获取 NAV 历史（PostgreSQL）。

        Returns:
            DataFrame[date, code, nav(Decimal)]
        """
        sql = """
            SELECT report_date AS date, fund_code AS code, nav
            FROM reits.nav_history
            WHERE fund_code = %s
            ORDER BY report_date
        """
        df = self._query_pg(sql, (code,))
        if not df.empty and "nav" in df.columns:
            df["nav"] = df["nav"].apply(
                lambda x: Decimal(str(x)) if x is not None else None
            )
        return df

    def get_dividends(self, code: str) -> pd.DataFrame:
        """获取分红记录（PostgreSQL）。

        Returns:
            DataFrame[ex_date, code, amount_per_share(Decimal)]
        """
        sql = """
            SELECT ex_date, fund_code AS code, amount_per_share
            FROM reits.dividends
            WHERE fund_code = %s
            ORDER BY ex_date
        """
        df = self._query_pg(sql, (code,))
        if not df.empty and "amount_per_share" in df.columns:
            df["amount_per_share"] = df["amount_per_share"].apply(
                lambda x: Decimal(str(x)) if x is not None else None
            )
        return df

    def get_fund_info(self, code: str) -> Optional[dict]:
        """获取 REITs 基础信息（PostgreSQL）。

        Returns:
            dict{code, name, type, listing_date} or None
        """
        sql = """
            SELECT fund_code AS code, fund_name AS name,
                   asset_type AS type, listing_date
            FROM reits.fund_info
            WHERE fund_code = %s
        """
        return self._query_pg_one(sql, (code,))

    def get_asset_metrics(self, code: str) -> pd.DataFrame:
        """获取底层资产运营指标（PostgreSQL）。

        Returns:
            DataFrame[report_date, code, occupancy_rate, noi, cap_rate, ebitda]
        """
        sql = """
            SELECT report_date, fund_code AS code,
                   occupancy_rate, noi, cap_rate, ebitda
            FROM reits.asset_metrics
            WHERE fund_code = %s
            ORDER BY report_date
        """
        df = self._query_pg(sql, (code,))
        for col in ("occupancy_rate", "noi", "cap_rate", "ebitda"):
            if col in df.columns and not df.empty:
                df[col] = df[col].apply(
                    lambda x: Decimal(str(x)) if x is not None else None
                )
        return df

    def get_universe(
        self, end_date: str, min_listing_days: int = 60
    ) -> pd.DataFrame:
        """构建回测 universe：上市满 min_listing_days 的全部 REITs。

        过滤在 Python 层执行（而非 SQL WHERE），因为 listing_date 的 cutoff
        计算依赖业务参数，放在应用层便于测试和审计。

        Returns:
            DataFrame[code, name, type, listing_date]
        """
        sql = """
            SELECT fund_code AS code, fund_name AS name,
                   asset_type AS type, listing_date
            FROM reits.fund_info
            ORDER BY code
        """
        df = self._query_pg(sql)
        if df.empty:
            return df
        # Python 层过滤：只保留上市满 min_listing_days 的标的
        cutoff = (
            datetime.date.fromisoformat(end_date)
            - datetime.timedelta(days=min_listing_days)
        )
        mask = df["listing_date"].apply(
            lambda d: d <= cutoff if isinstance(d, datetime.date) else False
        )
        return df[mask].reset_index(drop=True)
