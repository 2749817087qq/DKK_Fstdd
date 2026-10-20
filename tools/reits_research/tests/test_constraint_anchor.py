"""约束锚定与漂移检测测试。

覆盖三层防护：
  Layer 1: 规格冻结 + 哈希校验
  Layer 2: 变更审计日志
  Layer 3: 红线不可退化断言
"""
from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest


class TestSpecFreeze:
    """Layer 1: 规格冻结与哈希校验。"""

    def test_frozen_hash_deterministic(self):
        """GIVEN 相同约束 WHEN 计算哈希 THEN 结果一致。"""
        from src.constraint_anchor import ConstraintAnchor

        a1 = ConstraintAnchor(strict_mode=False)
        a2 = ConstraintAnchor(strict_mode=False)
        assert a1.get_frozen_hash() == a2.get_frozen_hash()

    def test_verify_passes_with_unchanged_constraints(self):
        """GIVEN 未修改约束 WHEN 校验 THEN 通过。"""
        from src.constraint_anchor import ConstraintAnchor

        anchor = ConstraintAnchor(strict_mode=False)
        ok, msg = anchor.verify()
        assert ok is True
        assert "通过" in msg

    def test_verify_detects_drift(self):
        """GIVEN 约束被修改 WHEN 校验 THEN 检测到漂移。"""
        from src.constraint_anchor import ConstraintAnchor, FROZEN_CONSTRAINTS

        anchor = ConstraintAnchor(strict_mode=False)
        tampered = dict(FROZEN_CONSTRAINTS)
        tampered["data.max_missing_rate"] = 0.10  # 从 0.05 放松到 0.10

        ok, msg = anchor.verify(tampered)
        assert ok is False
        assert "漂移" in msg
        assert "max_missing_rate" in msg

    def test_strict_mode_raises_on_drift(self):
        """GIVEN strict_mode=True + 约束漂移 WHEN 校验 THEN 抛出异常。"""
        from src.constraint_anchor import ConstraintAnchor, ConstraintDriftError, FROZEN_CONSTRAINTS

        anchor = ConstraintAnchor(strict_mode=True)
        tampered = dict(FROZEN_CONSTRAINTS)
        tampered["backtest.max_turnover"] = 0.50

        with pytest.raises(ConstraintDriftError, match="漂移"):
            anchor.verify(tampered)


class TestChangeAudit:
    """Layer 2: 变更审计日志。"""

    def test_record_change_appends_log(self):
        """GIVEN 一次约束变更 WHEN 记录 THEN changelog 追加一条。"""
        from src.constraint_anchor import ConstraintAnchor, FROZEN_CONSTRAINTS

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "changelog.yaml"
            anchor = ConstraintAnchor(changelog_path=str(log_path), strict_mode=False)

            new_constraints = dict(FROZEN_CONSTRAINTS)
            new_constraints["data.max_missing_rate"] = 0.03  # 收紧

            anchor.record_change(
                change_id="CONSTRAINT-2026-001",
                author="analyst@ccreits.cn",
                reason="提高数据质量要求，缺失率阈值从5%收紧到3%",
                old_constraints=FROZEN_CONSTRAINTS,
                new_constraints=new_constraints,
            )

            log = anchor.get_changelog()
            assert len(log) == 1
            assert log[0]["change_id"] == "CONSTRAINT-2026-001"
            assert log[0]["author"] == "analyst@ccreits.cn"
            assert len(log[0]["diffs"]) == 1
            assert log[0]["diffs"][0]["key"] == "data.max_missing_rate"

    def test_changelog_is_append_only(self):
        """GIVEN 两次变更 WHEN 读取日志 THEN 两条记录均存在。"""
        from src.constraint_anchor import ConstraintAnchor, FROZEN_CONSTRAINTS

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "changelog.yaml"
            anchor = ConstraintAnchor(changelog_path=str(log_path), strict_mode=False)

            for i in range(2):
                new_c = dict(FROZEN_CONSTRAINTS)
                new_c["data.stale_nav_days"] = 90 - i * 10
                anchor.record_change(
                    change_id=f"CONSTRAINT-2026-00{i+2}",
                    author="test",
                    reason=f"调整 #{i+2}",
                    old_constraints=FROZEN_CONSTRAINTS,
                    new_constraints=new_c,
                )

            log = anchor.get_changelog()
            assert len(log) == 2


class TestRedLineRegression:
    """Layer 3: 红线不可退化断言。"""

    def test_valid_config_passes(self):
        """GIVEN 合规配置 WHEN 断言 THEN 无违规。"""
        from src.constraint_anchor import assert_red_lines_not_weakened

        config = {
            "universe": {"max_missing_rate": 0.05, "exclude_stale_nav_days": 90},
            "backtest": {"max_turnover": 0.30, "commission_rate": 0.0003, "slippage_rate": 0.0002, "dividend_reinvest": True},
        }
        violations = assert_red_lines_not_weakened(config)
        assert len(violations) == 0

    def test_weakened_missing_rate_caught(self):
        """GIVEN max_missing_rate=0.10 WHEN 断言 THEN 捕获违规。"""
        from src.constraint_anchor import assert_red_lines_not_weakened

        config = {
            "universe": {"max_missing_rate": 0.10, "exclude_stale_nav_days": 90},
            "backtest": {"max_turnover": 0.30, "commission_rate": 0.0003, "slippage_rate": 0.0002, "dividend_reinvest": True},
        }
        violations = assert_red_lines_not_weakened(config)
        assert any("max_missing_rate" in v for v in violations)

    def test_zero_cost_caught(self):
        """GIVEN 交易成本均为0 WHEN 断言 THEN 捕获违规。"""
        from src.constraint_anchor import assert_red_lines_not_weakened

        config = {
            "universe": {"max_missing_rate": 0.05, "exclude_stale_nav_days": 90},
            "backtest": {"max_turnover": 0.30, "commission_rate": 0, "slippage_rate": 0, "dividend_reinvest": True},
        }
        violations = assert_red_lines_not_weakened(config)
        assert any("交易成本" in v for v in violations)

    def test_tightened_constraints_pass(self):
        """GIVEN 约束被收紧（更严格） WHEN 断言 THEN 通过。"""
        from src.constraint_anchor import assert_red_lines_not_weakened

        config = {
            "universe": {"max_missing_rate": 0.02, "exclude_stale_nav_days": 60},  # 更严格
            "backtest": {"max_turnover": 0.20, "commission_rate": 0.0005, "slippage_rate": 0.0003, "dividend_reinvest": True},
        }
        violations = assert_red_lines_not_weakened(config)
        assert len(violations) == 0

    def test_dividend_reinvest_off_warns(self):
        """GIVEN dividend_reinvest=false WHEN 断言 THEN 产生 WARNING。"""
        from src.constraint_anchor import assert_red_lines_not_weakened

        config = {
            "universe": {"max_missing_rate": 0.05, "exclude_stale_nav_days": 90},
            "backtest": {"max_turnover": 0.30, "commission_rate": 0.0003, "slippage_rate": 0.0002, "dividend_reinvest": False},
        }
        violations = assert_red_lines_not_weakened(config)
        assert any("WARNING" in v and "dividend_reinvest" in v for v in violations)
