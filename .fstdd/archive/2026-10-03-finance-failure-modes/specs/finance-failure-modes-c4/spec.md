# Spec: finance-failure-modes-c4

> Change: 2026-10-03-finance-failure-modes | Auto-generated Human View

## Requirements

### Requirement: build.md C4 section 追加 8 行金融失败模式（编号 15-22）

#### Scenario: SC-001

- **GIVEN** build.md C4 section 存在 14 类通用模式 Markdown table
- **WHEN** 在 #14 后面追加 8 行金融模式
- **THEN** build.md C4 section SHALL 包含 22 行 table（header + 14 通用 + 8 金融）
- **AND** 编号 15-22
- **AND** 4 列对齐: # | 失败模式 | 覆盖方式 | BUILD 检查动作

### Requirement: 8 类金融模式每类有具体 BUILD 检查动作

#### Scenario: SC-002

- **GIVEN** 每类金融模式
- **WHEN** 检查 BUILD 检查动作列
- **THEN** 每类 SHALL 有具体可执行步骤（如审查接口、检查字段、运行命令），不能只写审查代码

### Requirement: 原有 14 类条目一字不改

#### Scenario: SC-003

- **GIVEN** 追加前的 build.md L317-332
- **WHEN** 追加 8 行
- **THEN** L317-332（原 14 类 + header + 分隔线）SHALL 一字不变
