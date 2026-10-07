"""proposal.md 渲染器 / 解析器共用的锚点常量 —— **单一事实源**。

背景（EXP-2026-0013「契约断层」/ KG-093「声明了约束但从未生效」）：
`canon.py` 的 proposal 渲染器与 `extract_proposal.py` 的解析器此前**各自硬编码**锚点，
导致双向不通 —— 渲染器把 `### New/Modified Capabilities` 挂在 `## What Changes` 之下
且从不输出 `## Impact`；解析器却找 `## Capabilities` h2 ⇒
`capabilities` / `impact` 恒为空，capability 条目泄漏进 `what_changes`。

本模块把锚点收口为唯一来源：渲染器与解析器都从这里取，任一侧改锚点必然同时生效。
对照声明形态 = `.fstdd/templates/proposal.md`（14 段模板）。
"""

__all__ = [
    "H2_WHY",
    "H2_WHAT_CHANGES",
    "H2_CAPABILITIES",
    "H2_IMPACT",
    "H2_CONSTRAINTS",
    "H2_STAKEHOLDERS",
    "H2_RISK_AREAS",
    "H2_NON_GOALS",
    "H2_SUCCESS_CRITERIA",
    "H3_NEW_CAPABILITIES",
    "H3_MODIFIED_CAPABILITIES",
    "CAPABILITY_H3_ANCHORS",
    "IMPACT_SECTIONS",
]

# ---- 顶层 h2 锚点（与模板 `.fstdd/templates/proposal.md` 一致）----
H2_WHY = "Why"
H2_WHAT_CHANGES = "What Changes"
H2_CAPABILITIES = "Capabilities"
H2_IMPACT = "Impact"
H2_CONSTRAINTS = "Constraints"
H2_STAKEHOLDERS = "Stakeholders"
H2_RISK_AREAS = "Risk Areas"
H2_NON_GOALS = "NonGoals"
H2_SUCCESS_CRITERIA = "Success Criteria"

# ---- capabilities 子段（h3）----
H3_NEW_CAPABILITIES = "New Capabilities"
H3_MODIFIED_CAPABILITIES = "Modified Capabilities"

#: 解析 `what_changes` 时的截断锚点 —— 历史形态下这两个 h3 会落在
#: `## What Changes` 区间内（因为当时缺 `## Capabilities` 父标题），必须显式截断。
CAPABILITY_H3_ANCHORS = (H3_NEW_CAPABILITIES, H3_MODIFIED_CAPABILITIES)

#: impact 三段：渲染用显示标签 → 解析用 JSON 键
IMPACT_SECTIONS = (
    ("代码层面", "code"),
    ("配置层面", "config"),
    ("基础设施", "infrastructure"),
)
