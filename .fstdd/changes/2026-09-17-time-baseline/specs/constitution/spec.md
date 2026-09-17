# Spec: constitution

> Change: 2026-09-17-time-baseline | Auto-generated Human View

## Requirements

### Requirement: 宪法必须含时间基线条款，且该条款被 Gate 检查引用

#### Scenario: SC-031

- **GIVEN** 宪法文件已更新
- **WHEN** 检索宪法中的时间基线条款
- **THEN** SHALL 存在编号连续的独立条款（`### 7. 时间基线`）
- **AND** 条款 SHALL 规定每个 change 必须建立基线
- **AND** 条款 SHALL 规定证据须带观测时刻
- **AND** 条款 SHALL 明确违规后果，而非仅描述性说明

#### Scenario: SC-032

- **GIVEN** 条款已写入宪法
- **WHEN** 检查 Gate 前自检清单与 `fstdd validate` 的检查项
- **THEN** 至少 1 处 SHALL 引用基线字段作为检查项
- **AND** 被引用的检查项 SHALL 实际执行（可被测试触发）
- **AND** SHALL NOT 只以文字提及而无对应实现

### Requirement: 宪法的两份副本必须保持一致

#### Scenario: SC-033

- **GIVEN** 宪法条款已更新
- **WHEN** 比较仓根 `FSTDD_CONSTITUTION.md` 与 `.fstdd/memory/FSTDD_CONSTITUTION.md`
- **THEN** 两份内容 SHALL 逐字节一致
- **AND** 一致性 SHALL 有测试断言覆盖
- **AND** SHALL NOT 只更新其中一份

### Requirement: 宪法条款必须与实现一致，不得教人做工具做不到的事

#### Scenario: SC-034

- **GIVEN** 宪法中的时间基线条款已定稿
- **WHEN** 逐条核对条款中的每一项「必须」
- **THEN** 每一项 SHALL 有对应的、可执行且已实现的检查
- **AND** 无法实现的条款 SHALL 从条款中移除或降级为建议
- **AND** 核对结果 SHALL 记入 test-report 并留证

#### Scenario: SC-035

- **GIVEN** 宪法条款与 skill 流程描述均已存在
- **WHEN** 检查 skill 中与时间基线相关的要求
- **THEN** skill 的 Gate 前自检清单 SHALL 与宪法条款一致
- **AND** SHALL NOT 出现「宪法要求、skill 未提」或「skill 要求、宪法禁止」的组合
