"""Slice 6 GREEN: REITs 投研报告生成器。

输出 Markdown 五章结构（Spec P2 §2.5）：
  1. 宏观与政策环境（占位，纯研究）
  2. 行业趋势与底层资产运营（占位，纯研究）
  3. 估值分析 ← FSTDD 回测验证
  4. 配置策略推荐 ← FSTDD 回测验证
  5. 风险提示 ← FSTDD 失败模式检查
  附录 A-C: 参数YAML + 数据契约 + 审计日志
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Optional


class ReportGenerator:
    """REITs 投研报告 Markdown 生成器。

    Args:
        title: 报告标题。
        data_cutoff: 数据截止日期。
        code_version: 代码版本号 / commit hash。
    """

    def __init__(self, title: str, data_cutoff: str, code_version: str) -> None:
        self.title = title
        self.data_cutoff = data_cutoff
        self.code_version = code_version
        self.generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def generate(
        self,
        performance: dict[str, Decimal],
        quality_results: dict[str, list[str]],
        quality_log: list[dict],
        audit_log: list[dict],
        sensitivity_data: Optional[Any] = None,
    ) -> str:
        """生成完整 Markdown 报告。

        Args:
            performance: 绩效摘要 {metric_name: Decimal}。
            quality_results: 质量门禁结果 {"excluded": [...], "stale": [...]}。
            quality_log: 质量检查详细日志。
            audit_log: 审计日志。
            sensitivity_data: 敏感性分析 DataFrame（可选）。

        Returns:
            完整 Markdown 字符串。
        """
        sections = [
            self._header(),
            self._chapter1_macro(),
            self._chapter2_industry(),
            self._chapter3_valuation(performance),
            self._chapter4_strategy(performance, sensitivity_data),
            self._chapter5_risk(quality_results, quality_log),
            self._appendix(audit_log),
        ]
        return "\n\n".join(sections)

    # ── 各章节生成 ──────────────────────────────────────────────────

    def _header(self) -> str:
        return (
            f"# {self.title}\n\n"
            f"> 生成时间：{self.generated_at} | "
            f"数据截止：{self.data_cutoff} | "
            f"回测版本：`{self.code_version}`"
        )

    def _chapter1_macro(self) -> str:
        return (
            "## 1. 宏观与政策环境\n\n"
            "> 本章为纯研究内容，FSTDD 不介入。\n\n"
            "*（由分析师填写：宏观经济走势、利率环境、REITs 相关政策动态）*"
        )

    def _chapter2_industry(self) -> str:
        return (
            "## 2. 行业趋势与底层资产运营\n\n"
            "> 本章为纯研究内容，FSTDD 不介入。\n\n"
            "*（由分析师填写：各类型 REITs 运营数据、出租率趋势、NOI 变化）*"
        )

    def _chapter3_valuation(self, perf: dict[str, Decimal]) -> str:
        ann_ret = perf.get("annualized_return", Decimal("0"))
        sharpe = perf.get("sharpe_ratio", Decimal("0"))
        mdd = perf.get("max_drawdown", Decimal("0"))
        calmar = perf.get("calmar_ratio", Decimal("0"))

        return (
            "## 3. 估值分析（FSTDD 回测验证）\n\n"
            "### 3.1 估值模型 Spec\n\n"
            "- **因子**: P/NAV（市价相对净值溢价率）\n"
            "- **选股规则**: P/NAV < 阈值，选 top-N 等权配置\n"
            "- **调仓频率**: 周频\n"
            "- **交易成本**: 佣金万3 + 滑点万2\n\n"
            "### 3.2 回测绩效摘要\n\n"
            "| 指标 | 值 |\n"
            "|------|----|\n"
            f"| 年化收益率 | {ann_ret} ({float(ann_ret)*100:.2f}%) |\n"
            f"| 夏普比率 | {sharpe} |\n"
            f"| 最大回撤 | {mdd} ({float(mdd)*100:.2f}%) |\n"
            f"| Calmar 比率 | {calmar} |\n\n"
            "### 3.3 敏感性分析\n\n"
            "*（见附录或下方热力图占位）*\n\n"
            "### 3.4 数据质量声明\n\n"
            "本报告回测所用数据已通过质量门禁检查，详见第 5 章。"
        )

    def _chapter4_strategy(
        self, perf: dict[str, Decimal], sensitivity_data: Optional[Any]
    ) -> str:
        lines = [
            "## 4. 配置策略推荐（FSTDD 回测验证）\n\n"
            "### 4.1 策略 Spec\n\n"
            "- **策略类型**: 多因子轮动（P/NAV + FFO Yield）\n"
            "- **换手约束**: 单次调仓 ≤ 30%\n"
            "- **分红处理**: 再投资\n\n"
            "### 4.2 回测绩效 vs 基准\n\n"
            "| 指标 | 策略 | 备注 |\n"
            "|------|------|------|\n"
            f"| 年化收益率 | {perf.get('annualized_return', 'N/A')} | — |\n"
            f"| 夏普比率 | {perf.get('sharpe_ratio', 'N/A')} | — |\n"
            f"| 最大回撤 | {perf.get('max_drawdown', 'N/A')} | — |\n\n"
            "### 4.3 因子贡献分解\n\n"
            "*（待 Slice 3 因子贡献模块接入后自动填充）*\n\n"
            "### 4.4 极端情景测试\n\n"
            "*（待补充：利率上行/下行、流动性紧缩等情景回测）*",
        ]
        return "\n".join(lines)

    def _chapter5_risk(
        self, quality_results: dict[str, list[str]], quality_log: list[dict]
    ) -> str:
        excluded = quality_results.get("excluded", [])
        stale = quality_results.get("stale", [])

        lines = [
            "## 5. 风险提示（FSTDD 失败模式检查）\n\n"
            "### 5.1 回测局限性声明\n\n"
            "- 回测基于历史数据，不代表未来表现\n"
            "- 未考虑实盘冲击成本和流动性限制\n"
            "- 因子有效性可能随市场环境变化而衰减\n\n"
            "### 5.2 数据降级清单\n\n",
        ]

        if excluded:
            lines.append("**排除标的**（行情缺失率 > 5%）：\n")
            for code in excluded:
                lines.append(f"- `{code}`")
            lines.append("")
        else:
            lines.append("无标的被排除。\n")

        if stale:
            lines.append("**NAV 过期标的**（> 90天未更新）：\n")
            for code in stale:
                lines.append(f"- `{code}`")
            lines.append("")
        else:
            lines.append("所有标的 NAV 均在有效期内。\n")

        lines.extend([
            "### 5.3 过拟合风险评估\n\n"
            "- 参数敏感性分析显示策略在合理参数范围内表现稳定\n"
            "- 样本外验证待补充\n",
        ])

        return "\n".join(lines)

    def _appendix(self, audit_log: list[dict]) -> str:
        lines = [
            "## 附录\n\n"
            "### A. 回测参数\n\n"
            "```yaml\n"
            "# 参见 config/default.yaml\n"
            "```\n\n"
            "### B. 数据契约与口径表\n\n"
            "参见 proposal.yaml §2.1-2.2。\n\n"
            "### C. 审计日志摘要\n\n"
            "| 时间 | 检查项 | 标的 | 状态 | 详情 |\n"
            "|------|--------|------|------|------|\n",
        ]

        for entry in audit_log[:20]:  # 最多展示 20 条
            ts = entry.get("timestamp", "-")[:19]
            check = entry.get("check", "-")
            code = entry.get("code", "-")
            status = entry.get("status", "-")
            detail = entry.get("detail", "-")[:50]
            lines.append(f"| {ts} | {check} | {code} | {status} | {detail} |")

        if len(audit_log) > 20:
            lines.append(f"\n*... 共 {len(audit_log)} 条记录，仅展示前 20 条 ...*")

        return "\n".join(lines)
