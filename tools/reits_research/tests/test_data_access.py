"""Slice 1 RED: 数据接入层测试 — 先写测试，再实现。

覆盖 Spec-BT-003 数据契约中定义的 6 类数据源读取。
使用 mock 替代真实数据库连接，确保测试可离线运行。
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


class TestDataAccessInit:
    """数据接入层初始化与配置加载。"""

    def test_init_with_valid_config(self):
        """GIVEN 有效的配置字典 WHEN 初始化 DataAccess THEN 实例创建成功。"""
        from src.data_access import DataAccess

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "test", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)
        assert da is not None

    def test_init_missing_pg_config_raises(self):
        """GIVEN 缺少 postgresql 配置 WHEN 初始化 THEN 抛出 ValueError。"""
        from src.data_access import DataAccess

        with pytest.raises(ValueError, match="postgresql"):
            DataAccess({"duckdb": {"path": ":memory:"}})

    def test_init_missing_duckdb_config_raises(self):
        """GIVEN 缺少 duckdb 配置 WHEN 初始化 THEN 抛出 ValueError。"""
        from src.data_access import DataAccess

        with pytest.raises(ValueError, match="duckdb"):
            DataAccess({"postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"}})


class TestDailyQuotes:
    """日线行情数据读取（DuckDB）。"""

    def test_get_daily_quotes_returns_dataframe(self):
        """GIVEN 有效日期范围 WHEN 获取日线 THEN 返回含 date/code/close/volume 列的 DataFrame。"""
        from src.data_access import DataAccess
        import pandas as pd

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        # Mock DuckDB 查询
        mock_df = pd.DataFrame({
            "date": [datetime.date(2024, 1, 2), datetime.date(2024, 1, 3)],
            "code": ["508000.SH", "508000.SH"],
            "close": [Decimal("3.452100"), Decimal("3.468200")],
            "volume": [1000000, 1200000],
        })
        with patch.object(da, "_query_duckdb", return_value=mock_df):
            result = da.get_daily_quotes("508000.SH", "2024-01-01", "2024-01-31")

        assert list(result.columns) == ["date", "code", "close", "volume"]
        assert len(result) == 2
        assert isinstance(result["close"].iloc[0], Decimal)

    def test_get_daily_quotes_empty_range(self):
        """GIVEN 无数据的日期范围 WHEN 获取日线 THEN 返回空 DataFrame（不报错）。"""
        from src.data_access import DataAccess
        import pandas as pd

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        with patch.object(da, "_query_duckdb", return_value=pd.DataFrame(columns=["date", "code", "close", "volume"])):
            result = da.get_daily_quotes("999999.SH", "2020-01-01", "2020-01-31")

        assert len(result) == 0


class TestNAVHistory:
    """NAV 历史数据读取（PostgreSQL）。"""

    def test_get_nav_history_returns_dataframe(self):
        """GIVEN 有效 REITs 代码 WHEN 获取 NAV THEN 返回含 date/nav 列的 DataFrame。"""
        from src.data_access import DataAccess
        import pandas as pd

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        mock_df = pd.DataFrame({
            "date": [datetime.date(2024, 6, 30)],
            "code": ["508000.SH"],
            "nav": [Decimal("3.5210")],
        })
        with patch.object(da, "_query_pg", return_value=mock_df):
            result = da.get_nav_history("508000.SH")

        assert "nav" in result.columns
        assert isinstance(result["nav"].iloc[0], Decimal)


class TestDividends:
    """分红记录读取（PostgreSQL）。"""

    def test_get_dividends_returns_dataframe(self):
        """GIVEN 有效代码 WHEN 获取分红 THEN 返回含 ex_date/amount 列的 DataFrame。"""
        from src.data_access import DataAccess
        import pandas as pd

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        mock_df = pd.DataFrame({
            "ex_date": [datetime.date(2024, 5, 15)],
            "code": ["508000.SH"],
            "amount_per_share": [Decimal("0.1200")],
        })
        with patch.object(da, "_query_pg", return_value=mock_df):
            result = da.get_dividends("508000.SH")

        assert "amount_per_share" in result.columns
        assert isinstance(result["amount_per_share"].iloc[0], Decimal)


class TestFundInfo:
    """REITs 基础信息读取（PostgreSQL）。"""

    def test_get_fund_info_returns_dict(self):
        """GIVEN 有效代码 WHEN 获取基础信息 THEN 返回含 code/name/type/listing_date 的字典。"""
        from src.data_access import DataAccess

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        mock_row = {"code": "508000.SH", "name": "华安张江光大REIT", "type": "产业园", "listing_date": datetime.date(2021, 6, 21)}
        with patch.object(da, "_query_pg_one", return_value=mock_row):
            result = da.get_fund_info("508000.SH")

        assert result["code"] == "508000.SH"
        assert result["type"] == "产业园"

    def test_get_fund_info_not_found_returns_none(self):
        """GIVEN 不存在的代码 WHEN 获取基础信息 THEN 返回 None。"""
        from src.data_access import DataAccess

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        with patch.object(da, "_query_pg_one", return_value=None):
            result = da.get_fund_info("999999.SH")

        assert result is None


class TestUniverse:
    """回测 universe 构建。"""

    def test_get_universe_filters_by_listing_days(self):
        """GIVEN min_listing_days=60 WHEN 获取 universe THEN 上市不足60天的标的被排除。"""
        from src.data_access import DataAccess
        import pandas as pd

        config = {
            "postgresql": {"host": "localhost", "port": 5432, "dbname": "t", "user": "u", "password_env": "X"},
            "duckdb": {"path": ":memory:"},
        }
        da = DataAccess(config)

        mock_funds = pd.DataFrame({
            "code": ["508000.SH", "508001.SH", "508099.SH"],
            "name": ["A", "B", "C"],
            "type": ["产业园", "仓储物流", "保租房"],
            "listing_date": [
                datetime.date(2021, 6, 21),   # > 60 days
                datetime.date(2021, 6, 21),   # > 60 days
                datetime.date(2026, 9, 1),    # < 60 days (relative to end_date)
            ],
        })
        with patch.object(da, "_query_pg", return_value=mock_funds):
            result = da.get_universe(end_date="2026-09-30", min_listing_days=60)

        assert "508099.SH" not in result["code"].values
        assert len(result) == 2
