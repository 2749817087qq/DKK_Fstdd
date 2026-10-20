"""约束锚定与漂移检测模块。

核心问题：回测系统的约束（红线、口径、参数）会随时间静默漂移。
本模块提供三层防护：

  Layer 1 — 规格冻结（Spec Freeze）
    将关键约束序列化为 YAML 并计算 SHA-256 哈希。
    运行时加载配置后重新计算哈希，不一致则阻断或告警。

  Layer 2 — 变更审计（Change Audit）
    每次约束变更必须附带 change_id + reason + author。
    变更记录 append-only 写入 constraint_changelog.yaml。

  Layer 3 — 红线不可退化测试（Red Line Regression）
    一组「约束断言」测试，确保红线只能收紧不能放松。
    例如：max_missing_rate 只能 ≤ 0.05，不能改成 0.10。

设计原则：
  - 约束是**契约**，不是建议。违反 = 阻断，不是警告。
  - 变更是**事件**，不是覆盖。每次变更留痕。
  - 测试是**守卫**，不是文档。CI 中红线测试失败 = 不允许合并。
"""
from __future__ import annotations

import datetime
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import yaml


# ── 约束规格定义 ────────────────────────────────────────────────────

# 这些是「不可漂移」的核心约束。任何变更必须走 change proposal。
FROZEN_CONSTRAINTS = {
    # 金融红线
    "red_lines.precision": "Decimal ROUND_HALF_UP 4位",
    "red_lines.idempotency": "同参数+同数据 → 确定性相同结果",
    "red_lines.auditability": "每次回测绑定数据快照+参数hash+代码版本",
    "red_lines.reconciliation": "季度末回测vs真实持仓差异 ≤ 0.5%",
    "red_lines.degradation": "缺失>3天 → 排除+标记，禁止静默填充",
    "red_lines.compliance": "仅自有库+公开信息，外部注明出处",
    "red_lines.no_hardcode": "所有模型参数走YAML配置",

    # 数据契约阈值
    "data.max_missing_rate": 0.05,
    "data.stale_nav_days": 90,
    "data.min_dividend_completeness": 0.95,

    # 回测引擎约束
    "backtest.look_ahead": "T-1 only, never T",
    "backtest.max_turnover": 0.30,
    "backtest.cost_model": "commission + slippage, no free trades",
}


class ConstraintAnchor:
    """约束锚定器：冻结、校验、记录变更。

    Args:
        changelog_path: 变更日志文件路径（append-only）。
        strict_mode: True = 哈希不匹配时抛异常；False = 仅告警。
    """

    def __init__(
        self,
        changelog_path: str = "constraint_changelog.yaml",
        strict_mode: bool = True,
    ) -> None:
        self.changelog_path = Path(changelog_path)
        self.strict_mode = strict_mode
        self._frozen_hash = self._compute_hash(FROZEN_CONSTRAINTS)

    @staticmethod
    def _compute_hash(constraints: dict) -> str:
        """将约束字典序列化为确定性 JSON 后计算 SHA-256。"""
        serialized = json.dumps(constraints, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def get_frozen_hash(self) -> str:
        """返回当前冻结约束的哈希值。"""
        return self._frozen_hash

    def verify(self, runtime_constraints: Optional[dict] = None) -> tuple[bool, str]:
        """校验运行时约束是否与冻结规格一致。

        Args:
            runtime_constraints: 运行时实际约束。None = 使用内置 FROZEN_CONSTRAINTS。

        Returns:
            (is_valid, message)
        """
        target = runtime_constraints or FROZEN_CONSTRAINTS
        runtime_hash = self._compute_hash(target)

        if runtime_hash == self._frozen_hash:
            return True, f"约束校验通过 (hash={runtime_hash})"

        msg = (
            f"⚠️ 约束漂移检测！\n"
            f"  冻结哈希: {self._frozen_hash}\n"
            f"  运行时哈希: {runtime_hash}\n"
            f"  请检查以下约束是否被未授权修改:\n"
        )
        # 逐项对比找出差异
        for key in set(list(FROZEN_CONSTRAINTS.keys()) + list(target.keys())):
            frozen_val = FROZEN_CONSTRAINTS.get(key, "<新增>")
            runtime_val = target.get(key, "<删除>")
            if str(frozen_val) != str(runtime_val):
                msg += f"    [{key}] 冻结={frozen_val} → 运行时={runtime_val}\n"

        if self.strict_mode:
            raise ConstraintDriftError(msg)
        return False, msg

    def record_change(
        self,
        change_id: str,
        author: str,
        reason: str,
        old_constraints: dict,
        new_constraints: dict,
    ) -> None:
        """记录一次约束变更（append-only）。

        Args:
            change_id: 变更提案 ID（如 "CONSTRAINT-2026-001"）。
            author: 变更作者。
            reason: 变更原因。
            old_constraints: 变更前约束。
            new_constraints: 变更后约束。
        """
        # 计算差异
        diffs = []
        all_keys = set(list(old_constraints.keys()) + list(new_constraints.keys()))
        for key in sorted(all_keys):
            old_val = old_constraints.get(key, "<不存在>")
            new_val = new_constraints.get(key, "<不存在>")
            if str(old_val) != str(new_val):
                diffs.append({"key": key, "old": str(old_val), "new": str(new_val)})

        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "change_id": change_id,
            "author": author,
            "reason": reason,
            "old_hash": self._compute_hash(old_constraints),
            "new_hash": self._compute_hash(new_constraints),
            "diffs": diffs,
        }

        # Append-only 写入
        self.changelog_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.changelog_path, "a", encoding="utf-8") as f:
            f.write("---\n")
            f.write(yaml.safe_dump(entry, allow_unicode=True, sort_keys=False))

    def get_changelog(self) -> list[dict]:
        """读取完整变更日志。"""
        if not self.changelog_path.exists():
            return []
        entries = []
        with open(self.changelog_path, "r", encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if doc:
                    entries.append(doc)
        return entries


class ConstraintDriftError(Exception):
    """约束漂移异常：strict_mode 下哈希不匹配时抛出。"""
    pass


# ── Layer 3: 红线不可退化断言 ───────────────────────────────────────

def assert_red_lines_not_weakened(config: dict) -> list[str]:
    """验证配置中的红线参数未被放松。

    返回违规列表。空列表 = 全部通过。
    这组断言应作为 CI 测试运行，失败 = 不允许合并。
    """
    violations = []

    # 缺失率只能 ≤ 0.05
    max_missing = config.get("universe", {}).get("max_missing_rate", 0.05)
    if max_missing > 0.05:
        violations.append(
            f"RED LINE VIOLATION: max_missing_rate={max_missing} > 0.05 "
            f"(红线要求 ≤ 0.05)"
        )

    # NAV 过期天数只能 ≤ 90
    stale_days = config.get("universe", {}).get("exclude_stale_nav_days", 90)
    if stale_days > 90:
        violations.append(
            f"RED LINE VIOLATION: exclude_stale_nav_days={stale_days} > 90 "
            f"(红线要求 ≤ 90)"
        )

    # 换手率上限只能 ≤ 0.30
    max_turnover = config.get("backtest", {}).get("max_turnover", 0.30)
    if max_turnover > 0.30:
        violations.append(
            f"RED LINE VIOLATION: max_turnover={max_turnover} > 0.30 "
            f"(红线要求 ≤ 0.30)"
        )

    # 交易成本不能为 0（防止免费交易幻觉）
    commission = config.get("backtest", {}).get("commission_rate", 0.0003)
    slippage = config.get("backtest", {}).get("slippage_rate", 0.0002)
    if commission <= 0 and slippage <= 0:
        violations.append(
            "RED LINE VIOLATION: commission_rate 和 slippage_rate 均为 0 "
            "(红线要求必须计入交易成本)"
        )

    # 分红再投资不能关闭（除非有明确 change proposal）
    # 注意：这条是软约束，仅告警
    reinvest = config.get("backtest", {}).get("dividend_reinvest", True)
    if not reinvest:
        violations.append(
            "WARNING: dividend_reinvest=false，需确认已有对应 change proposal"
        )

    return violations
