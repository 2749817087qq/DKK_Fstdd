# Spec: proposal-extraction-fidelity

> Change: 2026-10-07-tool-defect-fixes | Auto-generated Human View

## Requirements

### Requirement: `canon` 渲染出的 `proposal.md` SHALL 包含解析器所期望的顶层锚点：
`## Capabilities`（下含 `### New Capabilities` / `### Modified Capabilities`）与 `## Impact`
（含 `**代码层面**` / `**配置层面**` / `**基础设施**` 三段）。
渲染器与解析器 SHALL 由**同一组锚点常量**驱动，SHALL NOT 各自硬编码导致分叉。


#### Scenario: SC-008

- **GIVEN** `canon.py` 的 proposal 渲染器当前把 `### Modified Capabilities` 挂在 `## What Changes` 之下，且从不输出 `## Impact`
- **WHEN** 执行 `fstdd canon generate <change>` 渲染任一 change 的 proposal.md
- **THEN** SHALL 使渲染结果含顶层 `## Capabilities` 段
- **AND** SHALL 使渲染结果含顶层 `## Impact` 段
- **AND** `## What Changes` 段 SHALL NOT 再包含 capability 条目

### Requirement: `fstdd extract-proposal <change>` SHALL 正确解析出 `capabilities`（new / modified）与 `impact`；
对**历史** change（渲染器尚未输出 h2 的 h3 形态）SHALL 保持向后兼容。
`what_changes` SHALL NOT 混入 capability 段条目。


#### Scenario: SC-009

- **GIVEN** 某 change 的 proposal.md 含 `### Modified Capabilities`（h3 形态）或其 h2 等价形态
- **WHEN** 执行 `fstdd extract-proposal <change>`
- **THEN** SHALL 使 `capabilities.modified` 非空（该 change 确有 modified capability 时）
- **AND** `what_changes` 中 SHALL NOT 出现 `**<capability>**：` 形态的条目
- **AND** `impact` SHALL 非空（该 change 的 proposal.yaml 确有 impact 时）

#### Scenario: SC-010

- **GIVEN** 存在渲染器改造**之前**生成的历史 proposal.md（h3 形态）
- **WHEN** 对历史 change 执行 `fstdd extract-proposal <change>`
- **THEN** SHALL 仍能解析出 capabilities（向后兼容），SHALL NOT 报错
- **AND** 对同一 change，h2 形态与 h3 形态的解析结果 SHALL 一致
